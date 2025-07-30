import uuid
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..models.test_generation import (
    TestGenerationRequest, TestGenerationResponse, TestCase, TestPriority, 
    TestCategory, TestStep, GeneratedTests, ExistingTests, TraceabilityMatrix,
    Recommendations, AutomationFeasibility, WorkItemHierarchy, WorkItemInfo
)
from ..models.analysis import ChangeAnalysisResponseWithCode
from ..services.azure_openai_service import AzureOpenAIService
from ..services.ado_service import AzureDevOpsService

class TestGenerationService:
    def __init__(self):
        self.openai_service = AzureOpenAIService()
        self.ado_service = None
        self.test_templates = self._load_test_templates()
    
    def _get_ado_service(self):
        """Lazy initialization of ADO service"""
        if self.ado_service is None:
            self.ado_service = AzureDevOpsService()
        return self.ado_service
    
    async def generate_tests(self, request: TestGenerationRequest) -> TestGenerationResponse:
        """Main method to generate comprehensive test cases"""
        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Step 1: Retrieve work item hierarchy from ADO
            work_item_hierarchy = await self._get_work_item_hierarchy(request.ado_config.work_item_id)
            
            # Step 2: Get existing test cases linked to work items
            existing_tests = await self._get_existing_tests(request.ado_config.work_item_id)
            
            # Step 3: Generate AI-powered test cases
            generated_tests = await self._generate_ai_test_cases(request.code_analysis, request.test_generation_options)
            
            # Step 4: Create traceability matrix
            traceability_matrix = await self._create_traceability_matrix(
                work_item_hierarchy, generated_tests, request.code_analysis
            )
            
            # Step 5: Generate recommendations
            recommendations = await self._generate_recommendations(
                generated_tests, existing_tests, request.code_analysis
            )
            
            return TestGenerationResponse(
                test_generation_id=session_id,
                generated_tests=generated_tests,
                existing_tests=existing_tests,
                traceability_matrix=traceability_matrix,
                recommendations=recommendations
            )
            
        except Exception as e:
            raise Exception(f"Test generation failed: {str(e)}")
    
    async def _get_work_item_hierarchy(self, work_item_id: int) -> WorkItemHierarchy:
        """Retrieve work item hierarchy from ADO"""
        try:
            # Get the work item and its relations
            ado_service = self._get_ado_service()
            work_item = await ado_service.get_work_item(work_item_id)
            relations = await ado_service.get_work_item_relations(work_item_id)
            
            hierarchy = WorkItemHierarchy()
            
            # Navigate up the hierarchy
            current_item = work_item
            while current_item:
                item_info = WorkItemInfo(
                    id=current_item['id'],
                    title=current_item['fields']['System.Title'],
                    state=current_item['fields'].get('System.State')
                )
                
                work_item_type = current_item['fields']['System.WorkItemType']
                
                if work_item_type == 'Epic':
                    hierarchy.epic = item_info
                elif work_item_type == 'Feature':
                    hierarchy.feature = item_info
                elif work_item_type == 'User Story':
                    hierarchy.user_story = item_info
                elif work_item_type == 'Task':
                    hierarchy.tasks.append(item_info)
                
                # Get parent item
                parent_relations = [r for r in relations if r['rel'] == 'System.LinkTypes.Hierarchy-Reverse']
                if parent_relations:
                    parent_id = parent_relations[0]['url'].split('/')[-1]
                    current_item = await ado_service.get_work_item(int(parent_id))
                    relations = await ado_service.get_work_item_relations(int(parent_id))
                else:
                    current_item = None
            
            return hierarchy
            
        except Exception as e:
            # Return minimal hierarchy if ADO calls fail
            return WorkItemHierarchy(
                tasks=[WorkItemInfo(id=work_item_id, title="Unknown Work Item")]
            )
    
    async def _get_existing_tests(self, work_item_id: int) -> ExistingTests:
        """Retrieve existing test cases from ADO"""
        try:
            # Get linked test cases
            ado_service = self._get_ado_service()
            linked_tests = await ado_service.get_linked_test_cases(work_item_id)
            
            # Get test suites in the same area path
            work_item = await ado_service.get_work_item(work_item_id)
            area_path = work_item['fields'].get('System.AreaPath', '')
            test_suites = await ado_service.get_test_suites_by_area(area_path)
            
            return ExistingTests(
                linked_test_cases=linked_tests,
                test_suites=test_suites
            )
            
        except Exception as e:
            return ExistingTests()
    
    async def _generate_ai_test_cases(self, code_analysis: Dict[str, Any], options) -> GeneratedTests:
        """Generate test cases using AI based on code analysis"""
        
        # Prepare prompt for AI
        prompt = self._build_test_generation_prompt(code_analysis, options)
        
        # Get AI response
        ai_response = await self.openai_service.generate_test_cases(prompt)
        
        # Parse and categorize test cases
        generated_tests = GeneratedTests()
        
        for test_data in ai_response.get('test_cases', []):
            test_case = self._create_test_case_from_ai_response(test_data)
            
            # Categorize based on test category
            if test_case.category == TestCategory.API:
                generated_tests.api_tests.append(test_case)
            elif test_case.category == TestCategory.UI:
                generated_tests.ui_tests.append(test_case)
            elif test_case.category == TestCategory.INTEGRATION:
                generated_tests.integration_tests.append(test_case)
        
        return generated_tests
    
    def _build_test_generation_prompt(self, code_analysis: Dict[str, Any], options) -> str:
        """Build comprehensive prompt for AI test case generation"""
        
        prompt = f"""
        Generate comprehensive test cases based on the following code analysis:
        
        SUMMARY: {code_analysis.summary}
        
        CHANGED COMPONENTS:
        """
        
        for component in code_analysis.changed_components:
            prompt += f"""
            File: {component.file_path}
            Risk Level: {component.risk_level}
            Methods Changed: {[m.name for m in component.methods]}
            Impact: {component.impact_description}
            """
        
        prompt += f"""
        
        DEPENDENCY CHAINS:
        """
        
        if code_analysis.dependency_chains:
            for chain in code_analysis.dependency_chains:
                prompt += f"""
                Primary File: {chain.file_path}
                Impacted Files: {[f.file_path for f in chain.impacted_files]}
                """
        else:
            prompt += f"""
            No dependency chains identified.
            """
        
        prompt += f"""
        
        OVERALL RISK LEVEL: {code_analysis.risk_level or 'medium'}
        
        Generate test cases with the following requirements:
        1. Include both positive and negative test scenarios
        2. Focus on edge cases and boundary conditions
        3. Consider integration points and dependencies
        4. Prioritize based on risk level and business impact
        5. Include specific test steps and expected results
        6. Suggest automation feasibility
        
        Test Generation Options:
        - Include API Tests: {options.include_api_tests}
        - Include UI Tests: {options.include_ui_tests}
        - Maximum Test Cases: {options.max_test_cases}
        - Test Frameworks: {', '.join(options.test_frameworks)}
        
        Return test cases in JSON format with the following structure for each test:
        {{
            "title": "Test case title",
            "description": "Detailed description",
            "category": "API|UI|Integration",
            "priority": "Critical|High|Medium|Low",
            "test_steps": [
                {{
                    "step_number": 1,
                    "action": "Action to perform",
                    "expected_result": "Expected outcome",
                    "test_data": "Required test data"
                }}
            ],
            "preconditions": "Prerequisites",
            "automation_feasibility": "High|Medium|Low|Manual Only",
            "estimated_duration": 15,
            "tags": ["tag1", "tag2"],
            "related_code_files": ["file1.cs", "file2.cs"]
        }}
        """
        
        return prompt
    
    def _create_test_case_from_ai_response(self, test_data: Dict[str, Any]) -> TestCase:
        """Create TestCase object from AI response data"""
        
        # Parse test steps
        test_steps = []
        for step_data in test_data.get('test_steps', []):
            test_steps.append(TestStep(
                step_number=step_data.get('step_number', 1),
                action=step_data.get('action', ''),
                expected_result=step_data.get('expected_result', ''),
                test_data=step_data.get('test_data')
            ))
        
        return TestCase(
            id=str(uuid.uuid4()),
            title=test_data.get('title', ''),
            description=test_data.get('description', ''),
            priority=TestPriority(test_data.get('priority', 'Medium')),
            category=TestCategory(test_data.get('category', 'API')),
            test_steps=test_steps,
            preconditions=test_data.get('preconditions'),
            test_data_requirements=test_data.get('test_data_requirements', []),
            automation_feasibility=AutomationFeasibility(test_data.get('automation_feasibility', 'Medium')),
            estimated_duration=test_data.get('estimated_duration'),
            tags=test_data.get('tags', []),
            related_code_files=test_data.get('related_code_files', [])
        )
    
    async def _create_traceability_matrix(self, hierarchy: WorkItemHierarchy, 
                                        generated_tests: GeneratedTests, 
                                        code_analysis: ChangeAnalysisResponseWithCode) -> TraceabilityMatrix:
        """Create traceability matrix linking tests to code and work items"""
        
        test_coverage_map = {}
        
        # Map test cases to changed files
        for component in code_analysis.changed_components:
            file_path = component.file_path
            test_ids = []
            
            # Find tests related to this file
            all_tests = (generated_tests.api_tests + 
                        generated_tests.ui_tests + 
                        generated_tests.integration_tests)
            
            for test in all_tests:
                if file_path in test.related_code_files:
                    test_ids.append(test.id)
            
            test_coverage_map[file_path] = test_ids
        
        return TraceabilityMatrix(
            work_item_hierarchy=hierarchy,
            test_coverage_map=test_coverage_map
        )
    
    async def _generate_recommendations(self, generated_tests: GeneratedTests,
                                      existing_tests: ExistingTests,
                                      code_analysis: ChangeAnalysisResponseWithCode) -> Recommendations:
        """Generate recommendations for test execution and coverage"""
        
        all_generated_tests = (generated_tests.api_tests + 
                             generated_tests.ui_tests + 
                             generated_tests.integration_tests)
        
        # Priority tests (Critical and High priority)
        priority_tests = [
            test.id for test in all_generated_tests 
            if test.priority in [TestPriority.CRITICAL, TestPriority.HIGH]
        ]
        
        # Coverage gaps (files without tests)
        changed_files = {comp.file_path for comp in code_analysis.changed_components}
        tested_files = set()
        for test in all_generated_tests:
            tested_files.update(test.related_code_files)
        
        coverage_gaps = list(changed_files - tested_files)
        
        # Automation candidates (High automation feasibility)
        automation_candidates = [
            test.id for test in all_generated_tests 
            if test.automation_feasibility == AutomationFeasibility.HIGH
        ]
        
        return Recommendations(
            priority_tests=priority_tests,
            coverage_gaps=coverage_gaps,
            automation_candidates=automation_candidates
        )
    
    def _load_test_templates(self) -> Dict[str, Any]:
        """Load test case templates for different categories"""
        return {
            'api': {
                'positive': "Verify API endpoint returns expected response for valid input",
                'negative': "Verify API endpoint handles invalid input gracefully",
                'boundary': "Test API endpoint with boundary values"
            },
            'ui': {
                'interaction': "Verify user interaction produces expected result",
                'validation': "Verify form validation works correctly",
                'navigation': "Verify navigation between pages works correctly"
            },
            'integration': {
                'data_flow': "Verify data flows correctly between components",
                'service_integration': "Verify service integration works as expected"
            }
        }
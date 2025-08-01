import uuid
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..models.test_generation import (
    TestGenerationRequest, TestGenerationResponse, TestCase, TestPriority, 
    TestCategory, TestStep, GeneratedTests, ExistingTests, TraceabilityMatrix,
    Recommendations, AutomationFeasibility, WorkItemHierarchy, WorkItemInfo, TestGenerationOptions
)
from ..services.azure_openai_service import AzureOpenAIService

class TestGenerationService:
    def __init__(self):
        self.openai_service = AzureOpenAIService()
        self.test_templates = self._load_test_templates()
    
    async def generate_tests(
        self, 
        pull_request_id: str,
        modified_files: List[str],
        smart_impact_summary: str,
        dependency_visualization: Optional[str],
        test_options: Optional[TestGenerationOptions] = None
    ) -> TestGenerationResponse:
        """Generate comprehensive test cases with minimal required input"""
        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Set default options if not provided
            if test_options is None:
                test_options = TestGenerationOptions()
            
            # Generate AI-powered test cases using streamlined input
            generated_tests = await self._generate_ai_test_cases(
                modified_files=modified_files,
                smart_impact_summary=smart_impact_summary,
                dependency_visualization=dependency_visualization,
                test_options=test_options
            )
            
            # Create simplified traceability matrix without ADO dependencies
            traceability_matrix = self._create_traceability_matrix(
                modified_files, generated_tests
            )
            
            # Generate recommendations based on input
            recommendations = self._generate_recommendations(
                generated_tests, modified_files, smart_impact_summary
            )
            
            return TestGenerationResponse(
                test_generation_id=session_id,
                generated_tests=generated_tests,
                existing_tests=ExistingTests(),  # Empty since no ADO integration
                traceability_matrix=traceability_matrix,
                recommendations=recommendations
            )
            
        except Exception as e:
            raise Exception(f"Test generation failed: {str(e)}")
    
    async def _generate_ai_test_cases(
        self, 
        modified_files: List[str],
        smart_impact_summary: str,
        dependency_visualization: Optional[str],
        test_options: TestGenerationOptions
    ) -> GeneratedTests:
        """Generate test cases using AI for maximum efficiency"""
        
        # Prepare optimized prompt for AI
        prompt = self._build_test_generation_prompt(
            modified_files, smart_impact_summary, dependency_visualization, test_options
        )
        
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
    
    def _build_test_generation_prompt(
        self, 
        modified_files: List[str],
        smart_impact_summary: str,
        dependency_visualization: Optional[str],
        test_options: TestGenerationOptions
    ) -> str:
        """Build efficient prompt for AI test case generation"""
        
        prompt = f"""
        Generate comprehensive test cases based on this code change analysis:
        
        MODIFIED FILES:
        {chr(10).join(f'- {file}' for file in modified_files)}
        
        SMART IMPACT SUMMARY:
        {smart_impact_summary}
        """
        
        if dependency_visualization:
            prompt += f"""
        
        DEPENDENCY CONTEXT:
        {dependency_visualization}
        """
        
        prompt += f"""
        
        REQUIREMENTS:
        1. Focus on the identified test focus areas from the smart summary
        2. Prioritize tests based on the risk level assessment
        3. Cover all modified files with appropriate test scenarios
        4. Include both positive and negative test cases
        5. Consider edge cases and error handling
        6. Provide specific, actionable test steps
        
        TEST GENERATION OPTIONS:
        - Include API Tests: {test_options.include_api_tests}
        - Include UI Tests: {test_options.include_ui_tests}
        - Maximum Test Cases: {test_options.max_test_cases}
        - Test Frameworks: {', '.join(test_options.test_frameworks) if test_options.test_frameworks else 'Any'}
        
        Return test cases in JSON format with this structure:
        {{
            "test_cases": [
                {{
                    "title": "Descriptive test case title",
                    "description": "Detailed test description",
                    "category": "API|UI|Integration|Unit|Performance|Security",
                    "priority": "Critical|High|Medium|Low",
                    "test_steps": [
                        {{
                            "step_number": 1,
                            "action": "Specific action to perform",
                            "expected_result": "Expected outcome",
                            "test_data": "Required test data (optional)"
                        }}
                    ],
                    "preconditions": "Prerequisites for test execution",
                    "automation_feasibility": "High|Medium|Low|Manual Only",
                    "estimated_duration": 15,
                    "tags": ["relevant", "tags"],
                    "related_code_files": {modified_files}
                }}
            ]
        }}
        
        Focus on quality over quantity. Generate the most valuable test cases first.
        """
        
        return prompt
    
    def _create_test_case_from_ai_response(self, test_data: Dict[str, Any]) -> TestCase:
        """Create a TestCase object from AI response data"""
        
        # Parse test steps
        test_steps = []
        for step_data in test_data.get('test_steps', []):
            test_steps.append(TestStep(
                step_number=step_data.get('step_number', 1),
                action=step_data.get('action', ''),
                expected_result=step_data.get('expected_result', ''),
                test_data=step_data.get('test_data')
            ))
        
        # Generate unique test case ID
        test_id = f"test_{uuid.uuid4().hex[:8]}"
        
        return TestCase(
            id=test_id,
            title=test_data.get('title', 'Generated Test Case'),
            description=test_data.get('description', ''),
            priority=TestPriority(test_data.get('priority', 'Medium')),
            category=TestCategory(test_data.get('category', 'API')),
            test_steps=test_steps,
            preconditions=test_data.get('preconditions'),
            test_data_requirements=test_data.get('test_data_requirements', []),
            automation_feasibility=AutomationFeasibility(
                test_data.get('automation_feasibility', 'Medium')
            ),
            estimated_duration=test_data.get('estimated_duration', 10),
            tags=test_data.get('tags', []),
            related_code_files=test_data.get('related_code_files', [])
        )
    
    def _create_traceability_matrix(
        self, 
        modified_files: List[str],
        generated_tests: GeneratedTests
    ) -> TraceabilityMatrix:
        """Create traceability matrix without ADO dependencies"""
        
        # Create coverage map based on modified files
        test_coverage_map = {}
        
        # Map files to test cases
        all_tests = (generated_tests.api_tests + 
                    generated_tests.ui_tests + 
                    generated_tests.integration_tests)
        
        for file_path in modified_files:
            related_tests = [
                test.id for test in all_tests 
                if file_path in test.related_code_files
            ]
            test_coverage_map[file_path] = related_tests
        
        return TraceabilityMatrix(
            work_item_hierarchy=WorkItemHierarchy(),  # Empty since no ADO integration
            test_coverage_map=test_coverage_map
        )
    
    def _generate_recommendations(
        self, 
        generated_tests: GeneratedTests, 
        modified_files: List[str],
        smart_impact_summary: str
    ) -> Recommendations:
        """Generate recommendations based on input"""
        
        all_tests = (generated_tests.api_tests + 
                    generated_tests.ui_tests + 
                    generated_tests.integration_tests)
        
        # Identify priority tests (Critical and High priority)
        priority_tests = [
            test.id for test in all_tests 
            if test.priority in [TestPriority.CRITICAL, TestPriority.HIGH]
        ]
        
        # Identify coverage gaps (files without tests)
        coverage_gaps = []
        for file_path in modified_files:
            has_tests = any(
                file_path in test.related_code_files 
                for test in all_tests
            )
            if not has_tests:
                coverage_gaps.append(f"No tests found for {file_path}")
        
        # Identify automation candidates (tests with High automation feasibility)
        automation_candidates = [
            test.id for test in all_tests 
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

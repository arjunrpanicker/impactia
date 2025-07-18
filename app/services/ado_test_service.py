import os
import base64
import asyncio
from typing import List, Dict, Any, Optional
import aiohttp
from urllib.parse import quote
from ..models.test_generation import AdoTestCase, TestSuite, WorkItemInfo

class AdoTestService:
    """Service for Azure DevOps Test Management API integration"""
    
    def __init__(self):
        self.organization = os.getenv("AZURE_DEVOPS_ORG")
        self.project = os.getenv("AZURE_DEVOPS_PROJECT")
        self.pat_token = os.getenv("AZURE_DEVOPS_PAT")
        
        if not all([self.organization, self.project, self.pat_token]):
            raise ValueError("Missing required Azure DevOps configuration")
        
        # Properly encode organization and project names to handle special characters
        encoded_org = quote(self.organization, safe='')
        encoded_project = quote(self.project, safe='')
        self.base_url = f"https://dev.azure.com/{encoded_org}/{encoded_project}/_apis"
        
        # Create authorization header
        # Use empty username with PAT token for basic auth
        auth_string = f":{self.pat_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'ImpactAnalysisAPI/1.0'
        }
    
    async def get_work_item(self, work_item_id: int) -> Dict[str, Any]:
        """Get work item details from ADO"""
        url = f"{self.base_url}/wit/workitems/{work_item_id}"
        params = {
            'api-version': '7.0',
            '$expand': 'fields,relations'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 404:
                    raise ValueError(f"Work item {work_item_id} not found")
                elif response.status != 200:
                    raise Exception(f"ADO API error: {response.status}")
                
                return await response.json()
    
    async def get_work_item_relations(self, work_item_id: int) -> List[Dict[str, Any]]:
        """Get work item relations"""
        work_item = await self.get_work_item(work_item_id)
        return work_item.get('relations', [])
    
    async def get_linked_test_cases(self, work_item_id: int) -> List[AdoTestCase]:
        """Get test cases linked to a work item"""
        try:
            # Get work item relations
            relations = await self.get_work_item_relations(work_item_id)
            
            # Find test case links
            test_case_relations = [
                r for r in relations 
                if r.get('rel') == 'Microsoft.VSTS.Common.TestedBy'
            ]
            
            test_cases = []
            for relation in test_case_relations:
                # Extract test case ID from URL
                test_case_url = relation.get('url', '')
                test_case_id = test_case_url.split('/')[-1]
                
                try:
                    test_case_data = await self.get_test_case(int(test_case_id))
                    test_cases.append(self._convert_to_ado_test_case(test_case_data))
                except Exception as e:
                    print(f"Error fetching test case {test_case_id}: {e}")
                    continue
            
            return test_cases
            
        except Exception as e:
            print(f"Error getting linked test cases: {e}")
            return []
    
    async def get_test_case(self, test_case_id: int) -> Dict[str, Any]:
        """Get individual test case details"""
        url = f"{self.base_url}/wit/workitems/{test_case_id}"
        params = {
            'api-version': '7.0',
            '$expand': 'fields'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get test case {test_case_id}: {response.status}")
                
                return await response.json()
    
    async def get_test_suites_by_area(self, area_path: str) -> List[TestSuite]:
        """Get test suites in a specific area path"""
        try:
            # First, get all test plans
            test_plans = await self.get_test_plans()
            
            test_suites = []
            for plan in test_plans:
                plan_id = plan['id']
                suites = await self.get_test_suites_in_plan(plan_id)
                
                # Filter suites by area path
                for suite in suites:
                    if area_path in suite.get('areaPath', ''):
                        test_suites.append(TestSuite(
                            id=suite['id'],
                            name=suite['name'],
                            test_case_count=suite.get('testCaseCount', 0),
                            parent_suite_id=suite.get('parentSuite', {}).get('id')
                        ))
            
            return test_suites
            
        except Exception as e:
            print(f"Error getting test suites: {e}")
            return []
    
    async def get_test_plans(self) -> List[Dict[str, Any]]:
        """Get all test plans in the project"""
        url = f"{self.base_url}/test/plans"
        params = {
            'api-version': '7.0'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get test plans: {response.status}")
                
                data = await response.json()
                return data.get('value', [])
    
    async def get_test_suites_in_plan(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get test suites in a specific test plan"""
        url = f"{self.base_url}/test/plans/{plan_id}/suites"
        params = {
            'api-version': '7.0',
            '$expand': 'children'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                return data.get('value', [])
    
    async def search_test_cases_by_keywords(self, keywords: str) -> List[AdoTestCase]:
        """Search for test cases using keywords"""
        try:
            # Use work item search API
            url = f"{self.base_url}/search/workitemsearchresults"
            params = {
                'api-version': '7.0'
            }
            
            search_request = {
                'searchText': keywords,
                'filters': {
                    'System.WorkItemType': ['Test Case']
                },
                'top': 50
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, params=params, json=search_request) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    test_cases = []
                    
                    for result in data.get('results', []):
                        test_case_data = await self.get_test_case(result['workItem']['id'])
                        test_cases.append(self._convert_to_ado_test_case(test_case_data))
                    
                    return test_cases
                    
        except Exception as e:
            print(f"Error searching test cases: {e}")
            return []
    
    async def create_test_case(self, test_case_data: Dict[str, Any]) -> int:
        """Create a new test case in ADO"""
        url = f"{self.base_url}/wit/workitems/$Test Case"
        params = {
            'api-version': '7.0'
        }
        
        # Build patch document for test case creation
        patch_document = [
            {
                'op': 'add',
                'path': '/fields/System.Title',
                'value': test_case_data.get('title', '')
            },
            {
                'op': 'add',
                'path': '/fields/System.Description',
                'value': test_case_data.get('description', '')
            },
            {
                'op': 'add',
                'path': '/fields/Microsoft.VSTS.Common.Priority',
                'value': self._convert_priority_to_ado(test_case_data.get('priority', 'Medium'))
            }
        ]
        
        # Add test steps if provided
        if 'test_steps' in test_case_data:
            steps_xml = self._convert_test_steps_to_xml(test_case_data['test_steps'])
            patch_document.append({
                'op': 'add',
                'path': '/fields/Microsoft.VSTS.TCM.Steps',
                'value': steps_xml
            })
        
        headers = {**self.headers, 'Content-Type': 'application/json-patch+json'}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, params=params, json=patch_document) as response:
                if response.status not in [200, 201]:
                    raise Exception(f"Failed to create test case: {response.status}")
                
                data = await response.json()
                return data['id']
    
    def _convert_to_ado_test_case(self, work_item_data: Dict[str, Any]) -> AdoTestCase:
        """Convert ADO work item data to AdoTestCase model"""
        fields = work_item_data.get('fields', {})
        
        return AdoTestCase(
            id=work_item_data['id'],
            title=fields.get('System.Title', ''),
            state=fields.get('System.State', ''),
            assigned_to=fields.get('System.AssignedTo', {}).get('displayName'),
            area_path=fields.get('System.AreaPath', ''),
            iteration_path=fields.get('System.IterationPath', ''),
            test_suite_id=None,  # Would need additional API call to get this
            last_execution_outcome=fields.get('Microsoft.VSTS.TCM.AutomatedTestStorage')
        )
    
    def _convert_priority_to_ado(self, priority: str) -> int:
        """Convert priority string to ADO priority number"""
        priority_map = {
            'Critical': 1,
            'High': 2,
            'Medium': 3,
            'Low': 4
        }
        return priority_map.get(priority, 3)
    
    def _convert_test_steps_to_xml(self, test_steps: List[Dict[str, Any]]) -> str:
        """Convert test steps to ADO XML format"""
        steps_xml = '<steps id="0" last="1">'
        
        for i, step in enumerate(test_steps, 1):
            action = step.get('action', '').replace('<', '&lt;').replace('>', '&gt;')
            expected = step.get('expected_result', '').replace('<', '&lt;').replace('>', '&gt;')
            
            steps_xml += f'''
            <step id="{i}" type="ActionStep">
                <parameterizedString isformatted="true">
                    <DIV><P>{action}</P></DIV>
                </parameterizedString>
                <parameterizedString isformatted="true">
                    <DIV><P>{expected}</P></DIV>
                </parameterizedString>
                <description/>
            </step>
            '''
        
        steps_xml += '</steps>'
        return steps_xml
import os
from urllib.parse import quote
from typing import Dict, Any
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from ..models.analysis import ChangeAnalysisResponse
from ..services.ado_test_service import AdoTestService

class AzureDevOpsService:
    def __init__(self):
        # Initialize Azure DevOps client
        personal_access_token = os.getenv("AZURE_DEVOPS_PAT")
        organization = os.getenv('AZURE_DEVOPS_ORG')
        project = os.getenv("AZURE_DEVOPS_PROJECT")
        
        if not personal_access_token or not organization or not project:
            raise ValueError("Missing required Azure DevOps configuration: AZURE_DEVOPS_PAT, AZURE_DEVOPS_ORG, and AZURE_DEVOPS_PROJECT must be set")
        
        # Properly encode organization name and construct URL
        encoded_org = quote(organization, safe='')
        organization_url = f"https://dev.azure.com/{encoded_org}"
        
        # Create a connection to Azure DevOps
        credentials = BasicAuthentication('', personal_access_token)
        self.connection = Connection(base_url=organization_url, creds=credentials)
        
        # Get clients
        self.git_client = self.connection.clients.get_git_client()
        self.work_item_client = self.connection.clients.get_work_item_tracking_client()
        
        # Store project name
        self.project = project
        
        # Initialize test service
        self.test_service = AdoTestService()

    async def update_work_item(self, work_item_id: str, analysis: ChangeAnalysisResponse):
        """
        Update Azure DevOps work item with analysis results
        """
        try:
            # Format the analysis results as markdown
            markdown_content = self._format_analysis_as_markdown(analysis)
            
            # Create patch document
            patch_document = [
                {
                    "op": "add",
                    "path": "/fields/System.Description",
                    "value": markdown_content
                },
                {
                    "op": "add",
                    "path": "/fields/Custom.ImpactAnalysis",
                    "value": str(analysis.dict())
                }
            ]
            
            # Update work item
            result = self.work_item_client.update_work_item(
                document=patch_document,
                id=work_item_id,
                project=self.project
            )
            
            return result
            
        except Exception as e:
            raise Exception(f"Failed to update work item: {str(e)}")

    async def get_work_item(self, work_item_id: int):
        """Get work item details"""
        return await self.test_service.get_work_item(work_item_id)
    
    async def get_work_item_relations(self, work_item_id: int):
        """Get work item relations"""
        return await self.test_service.get_work_item_relations(work_item_id)
    
    async def get_linked_test_cases(self, work_item_id: int):
        """Get test cases linked to work item"""
        return await self.test_service.get_linked_test_cases(work_item_id)
    
    async def get_test_suites_by_area(self, area_path: str):
        """Get test suites by area path"""
        return await self.test_service.get_test_suites_by_area(area_path)

    def _format_analysis_as_markdown(self, analysis: ChangeAnalysisResponse) -> str:
        """
        Format the analysis results as markdown for Azure DevOps
        """
        markdown = f"""
# Code Change Impact Analysis

## Summary
{analysis.summary}
"""

        if analysis.risk_level:
            markdown += f"\n## Risk Level: {analysis.risk_level.value.upper()}\n"

        markdown += "\n## Changed Components\n"
        
        for component in analysis.changed_components:
            markdown += f"""
### {component.file_path}
- **Methods**: {', '.join(component.methods)}
- **Impact**: {component.impact_description}
- **Risk Level**: {component.risk_level.value}
- **Associated Unit Tests**: {', '.join(component.associated_unit_tests)}
"""

        if analysis.dependency_chains:
            markdown += "\n## Dependency Chains\n"
            
            for chain in analysis.dependency_chains:
                markdown += f"""
### {chain.file_path}
#### Changed Methods:
"""
                for method in chain.methods:
                    markdown += f"- **{method.name}**: {method.summary}\n"
                
                markdown += "\n#### Impacted Files:\n"
                for imp_file in chain.impacted_files:
                    markdown += f"\n##### {imp_file.file_path}\n"
                    for method in imp_file.methods:
                        markdown += f"- **{method.name}**: {method.summary}\n"
                
                if chain.associated_unit_tests:
                    markdown += f"\n#### Associated Unit Tests:\n"
                    for test in chain.associated_unit_tests:
                        markdown += f"- {test}\n"

        if analysis.dependency_chain_visualization:
            markdown += "\n## Dependency Chain Visualization\n"
            markdown += "```\n"
            for chain in analysis.dependency_chain_visualization:
                markdown += f"{chain}\n"
            markdown += "```\n"
            
        return markdown 
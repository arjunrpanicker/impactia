from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime

class TestPriority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class TestCategory(str, Enum):
    API = "API"
    UI = "UI"
    INTEGRATION = "Integration"
    UNIT = "Unit"
    PERFORMANCE = "Performance"
    SECURITY = "Security"

class AutomationFeasibility(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    MANUAL_ONLY = "Manual Only"

class TestStep(BaseModel):
    step: int
    action: str
    expected_result: str
    test_data: Optional[str] = None

class TestCase(BaseModel):
    id: str
    type: str
    title: str = Field(..., max_length=200)
    description: str = Field(..., max_length=1000)
    priority: str
    preconditions: Optional[str] = None
    test_steps: List[TestStep]
    tags: List[str] = []
    related_files: List[str] = []

class AdoTestCase(BaseModel):
    id: int
    title: str
    state: str
    assigned_to: Optional[str] = None
    area_path: str
    iteration_path: str
    test_suite_id: Optional[int] = None
    last_execution_outcome: Optional[str] = None

class TestSuite(BaseModel):
    id: int
    name: str
    test_case_count: int
    parent_suite_id: Optional[int] = None

class WorkItemInfo(BaseModel):
    id: int
    title: str
    state: Optional[str] = None

class WorkItemHierarchy(BaseModel):
    epic: Optional[WorkItemInfo] = None
    feature: Optional[WorkItemInfo] = None
    user_story: Optional[WorkItemInfo] = None
    tasks: List[WorkItemInfo] = []

class TestGenerationOptions(BaseModel):
    include_ui_tests: bool = True
    include_api_tests: bool = True
    max_test_cases: int = Field(default=20, ge=1, le=50)
    test_frameworks: List[str] = []

class AdoConfig(BaseModel):
    work_item_id: int = Field(..., ge=1)
    project_name: Optional[str] = Field(None, max_length=100)
    organization: Optional[str] = Field(None, max_length=100)

# Test generation request model
class TestGenerationRequest(BaseModel):
    """Test generation request with only essential information"""
    pull_request_id: str = Field(..., pattern=r"^[0-9]+$")
    modified_files: List[str] = Field(..., description="List of file paths that were modified")
    smart_impact_summary: str = Field(..., description="Smart impact summary from analysis")
    dependency_visualization: Optional[str] = Field(None, description="Dependency chain visualization for context")
    test_generation_options: Optional[TestGenerationOptions] = TestGenerationOptions()

# Test generation response models
class TestSummary(BaseModel):
    total_tests: int
    api_tests: int
    integration_tests: int
    ui_tests: int

class Traceability(BaseModel):
    file_to_tests: Dict[str, List[str]]

class TestGenerationResponse(BaseModel):
    test_generation_id: str
    summary: TestSummary
    tests: List[TestCase]
    traceability: Traceability

class TestGenerationError(BaseModel):
    error_code: str
    message: str
    details: Optional[str] = None
    timestamp: datetime
    request_id: str
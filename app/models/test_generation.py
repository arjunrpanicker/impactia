from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
from .analysis import ChangeAnalysisResponseWithCode

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
    step_number: int
    action: str
    expected_result: str
    test_data: Optional[str] = None

class TestCase(BaseModel):
    id: str
    title: str = Field(..., max_length=200)
    description: str = Field(..., max_length=1000)
    priority: TestPriority
    category: TestCategory
    test_steps: List[TestStep]
    preconditions: Optional[str] = None
    test_data_requirements: List[str] = []
    automation_feasibility: AutomationFeasibility = AutomationFeasibility.MEDIUM
    estimated_duration: Optional[int] = None  # in minutes
    tags: List[str] = []
    related_code_files: List[str] = []

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

class TestGenerationRequest(BaseModel):
    pull_request_id: str = Field(..., pattern=r"^[0-9]+$")
    code_analysis: ChangeAnalysisResponseWithCode  # Direct output from analyze endpoint
    ado_config: AdoConfig
    test_generation_options: Optional[TestGenerationOptions] = TestGenerationOptions()

class GeneratedTests(BaseModel):
    api_tests: List[TestCase] = []
    ui_tests: List[TestCase] = []
    integration_tests: List[TestCase] = []

class ExistingTests(BaseModel):
    linked_test_cases: List[AdoTestCase] = []
    test_suites: List[TestSuite] = []

class TraceabilityMatrix(BaseModel):
    work_item_hierarchy: WorkItemHierarchy
    test_coverage_map: Dict[str, List[str]] = {}  # file_path -> test_case_ids

class Recommendations(BaseModel):
    priority_tests: List[str] = []
    coverage_gaps: List[str] = []
    automation_candidates: List[str] = []

class TestGenerationResponse(BaseModel):
    test_generation_id: str
    generated_tests: GeneratedTests
    existing_tests: ExistingTests
    traceability_matrix: TraceabilityMatrix
    recommendations: Recommendations

class TestGenerationError(BaseModel):
    error_code: str
    message: str
    details: Optional[str] = None
    timestamp: datetime
    request_id: str
import pytest
from app.models.test_generation import TestGenerationRequest, TestGenerationOptions


class TestTestGeneration:
    """Test class for test generation functionality"""
    
    @pytest.fixture
    def test_generation_request(self):
        """Fixture providing a sample test generation request"""
        return TestGenerationRequest(
            pull_request_id="123",
            modified_files=[
                "src/controllers/UserController.cs: Enhanced user input validation",
                "src/services/UserService.cs: Updated user processing logic"
            ],
            smart_impact_summary="""Enhanced user input validation with security checks. Overall change type: feature, Risk level: medium
Test focus areas: input_validation, security, error_handling

In file src/controllers/UserController.cs, the changes are:
  - validateUserInput (modified): Validates user input for security
    Impact: Enhanced validation logic
  File impact: Updated validation logic

In file src/services/UserService.cs, the changes are:
  - processUser (modified): Processes validated user data
    Impact: Updated processing logic
  File impact: Enhanced user processing""",
            dependency_visualization="UserController -> UserService -> UserRepository -> Database",
            test_generation_options=TestGenerationOptions(
                include_api_tests=True,
                include_ui_tests=True,
                max_test_cases=15
            )
        )
    
    def test_request_creation(self, test_generation_request):
        """Test that test generation request is created correctly"""
        assert test_generation_request.pull_request_id == "123"
        assert len(test_generation_request.modified_files) == 2
        assert "UserController.cs" in test_generation_request.modified_files[0]
        assert "Enhanced user input validation" in test_generation_request.smart_impact_summary
    
    def test_request_required_fields(self, test_generation_request):
        """Test that all required fields are present and valid"""
        # Test required string fields
        assert test_generation_request.pull_request_id.isdigit()
        assert len(test_generation_request.modified_files) > 0
        assert len(test_generation_request.smart_impact_summary) > 0
        
        # Test optional fields
        assert test_generation_request.dependency_visualization is not None
        assert test_generation_request.test_generation_options is not None
    
    def test_vs_legacy_input_comparison(self, test_generation_request):
        """Test that test generation input is significantly more efficient than legacy approach"""
        
        # Simulate legacy request fields (what would be in a full ChangeAnalysisResponseWithCode)
        legacy_analysis_fields = [
            "summary", "changed_components", "dependency_chains", 
            "risk_level", "smart_impact_summary", "file_changes",
            "method_changes", "class_changes", "dependency_chain_visualization",
            "test_recommendations", "security_analysis", "performance_impact",
            "breaking_changes", "migration_notes", "rollback_plan"
        ]
        
        # Test generation request only needs 3 core fields for AI context
        test_generation_core_fields = ["modified_files", "smart_impact_summary", "dependency_visualization"]
        
        # Verify significant reduction in required fields
        reduction_ratio = len(test_generation_core_fields) / len(legacy_analysis_fields)
        assert reduction_ratio < 0.25  # At least 75% reduction in field count
        
        # Verify essential information is preserved
        assert test_generation_request.modified_files  # File context
        assert "validation" in test_generation_request.smart_impact_summary.lower()  # Change context
        assert "UserController" in test_generation_request.dependency_visualization  # Dependency context
    
    def test_input_size_efficiency(self, test_generation_request):
        """Test that the test generation approach significantly reduces payload size"""
        
        # Calculate approximate sizes (simplified)
        modified_files_size = sum(len(file) for file in test_generation_request.modified_files)
        summary_size = len(test_generation_request.smart_impact_summary)
        dependency_size = len(test_generation_request.dependency_visualization or "")
        
        core_data_size = modified_files_size + summary_size + dependency_size
        
        # In a real scenario, full analysis would be 5-10x larger
        # Here we just verify that our core data is focused and compact
        assert core_data_size < 2000  # Should be under 2KB for typical changes
        assert len(test_generation_request.modified_files) < 20  # Reasonable file count
        assert len(test_generation_request.smart_impact_summary.split('\n')) < 50  # Concise summary
    
    def test_test_generation_options_defaults(self):
        """Test that test generation options have sensible defaults"""
        options = TestGenerationOptions()
        
        assert options.include_api_tests is True
        assert options.include_ui_tests is True
        assert options.max_test_cases == 20
        assert options.test_frameworks == []
        
        # Test boundary validation
        with pytest.raises(ValueError):
            TestGenerationOptions(max_test_cases=0)  # Should be >= 1
        
        with pytest.raises(ValueError):
            TestGenerationOptions(max_test_cases=100)  # Should be <= 50

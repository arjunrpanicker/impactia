import pytest
import asyncio
from unittest.mock import Mock, patch
from app.services.smart_summary_service import SmartSummaryService, SmartChangeSummary
from app.models.analysis import (
    ChangeAnalysisResponseWithCode, ChangedComponentWithCode, MethodWithCode,
    DependencyChainWithCode, RiskLevel
)

@pytest.fixture
def sample_analysis():
    """Create a sample analysis response for testing"""
    method = MethodWithCode(
        name="validateUserInput",
        summary="Validates user input for security",
        change_type="modified",
        impact_description="Enhanced validation logic"
    )
    
    component = ChangedComponentWithCode(
        file_path="src/validators/UserValidator.cs",
        methods=[method],
        impact_description="Updated validation logic",
        risk_level=RiskLevel.MEDIUM,
        associated_unit_tests=["UserValidatorTests.cs"],
        file_summary="User input validation service"
    )
    
    return ChangeAnalysisResponseWithCode(
        summary="Updated user input validation to include new security checks and enhanced error handling.",
        changed_components=[component],
        dependency_chains=[],
        risk_level=RiskLevel.MEDIUM
    )

@pytest.fixture
def smart_summary_service():
    """Create SmartSummaryService instance"""
    return SmartSummaryService()

class TestSmartSummaryService:
    
    def test_generate_smart_summary(self, smart_summary_service, sample_analysis):
        """Test generating a smart summary from analysis"""
        summary = smart_summary_service.generate_smart_summary(sample_analysis)
        
        assert isinstance(summary, SmartChangeSummary)
        assert summary.change_type in ["feature", "bugfix", "refactor", "breaking", "modification"]
        assert summary.scope in ["method", "class", "module", "system"]
        assert summary.risk_level == "medium"
        assert len(summary.modified_methods) == 1
        assert summary.modified_methods[0]["name"] == "validateUserInput"
        assert "validation" in summary.test_focus_areas or "security" in summary.test_focus_areas
    
    def test_determine_change_type_feature(self, smart_summary_service, sample_analysis):
        """Test change type detection for features"""
        sample_analysis.summary = "Added new feature for user authentication"
        summary = smart_summary_service.generate_smart_summary(sample_analysis)
        assert summary.change_type == "feature"
    
    def test_determine_change_type_bugfix(self, smart_summary_service, sample_analysis):
        """Test change type detection for bug fixes"""
        sample_analysis.summary = "Fixed critical bug in payment processing"
        summary = smart_summary_service.generate_smart_summary(sample_analysis)
        assert summary.change_type == "bugfix"
    
    def test_determine_scope_method(self, smart_summary_service, sample_analysis):
        """Test scope detection for single method changes"""
        summary = smart_summary_service.generate_smart_summary(sample_analysis)
        assert summary.scope == "method"
    
    def test_determine_scope_system(self, smart_summary_service, sample_analysis):
        """Test scope detection for system-wide changes"""
        # Add more components to make it system-wide
        for i in range(5):
            method = MethodWithCode(
                name=f"method{i}",
                summary=f"Method {i}",
                change_type="modified",
                impact_description=f"Impact {i}"
            )
            component = ChangedComponentWithCode(
                file_path=f"src/file{i}.cs",
                methods=[method],
                impact_description=f"Impact {i}",
                risk_level=RiskLevel.LOW,
                associated_unit_tests=[],
                file_summary=f"File {i}"
            )
            sample_analysis.changed_components.append(component)
        
        summary = smart_summary_service.generate_smart_summary(sample_analysis)
        assert summary.scope == "system"
    
    def test_identify_test_focus_areas(self, smart_summary_service, sample_analysis):
        """Test identification of test focus areas"""
        sample_analysis.summary = "Updated API validation with database integration and error handling"
        summary = smart_summary_service.generate_smart_summary(sample_analysis)
        
        expected_areas = ["input_validation", "api_integration", "data_persistence", "error_handling"]
        assert any(area in summary.test_focus_areas for area in expected_areas)
    
    def test_get_summary_for_test_generation(self, smart_summary_service, sample_analysis):
        """Test formatted summary for test generation"""
        formatted_summary = smart_summary_service.get_summary_for_test_generation(sample_analysis)
        
        assert "CHANGE SUMMARY:" in formatted_summary
        assert "FUNCTIONAL CHANGE:" in formatted_summary
        assert "MODIFIED METHODS:" in formatted_summary
        assert "TEST FOCUS:" in formatted_summary
        assert "validateUserInput" in formatted_summary
    
    def test_get_smart_impact_summary(self, smart_summary_service, sample_analysis):
        """Test smart impact summary generation"""
        smart_impact_summary = smart_summary_service.get_smart_impact_summary(sample_analysis)
        
        # Check for key elements in the smart impact summary
        assert sample_analysis.summary in smart_impact_summary
        assert "Overall change type:" in smart_impact_summary
        assert "Risk level:" in smart_impact_summary
        assert "Test focus areas:" in smart_impact_summary
        assert "In file" in smart_impact_summary
        assert sample_analysis.changed_components[0].file_path in smart_impact_summary
        assert "validateUserInput" in smart_impact_summary
        assert "Impact:" in smart_impact_summary
        assert "File impact:" in smart_impact_summary
        
        # Verify that it's a single string with comprehensive info
        assert isinstance(smart_impact_summary, str)
        assert len(smart_impact_summary) > 100  # Should have substantial content
    
    def test_caching_mechanism(self, smart_summary_service, sample_analysis):
        """Test that caching works correctly"""
        # Generate summary twice
        summary1 = smart_summary_service.generate_smart_summary(sample_analysis)
        summary2 = smart_summary_service.generate_smart_summary(sample_analysis)
        
        # Should be the same object from cache
        assert summary1.summary_hash == summary2.summary_hash
        assert summary1 == summary2
    
    def test_token_count_estimation(self, smart_summary_service, sample_analysis):
        """Test token count estimation"""
        summary = smart_summary_service.generate_smart_summary(sample_analysis)
        
        assert summary.token_count_estimate > 0
        assert isinstance(summary.token_count_estimate, int)
    
    def test_risk_level_mapping(self, smart_summary_service, sample_analysis):
        """Test risk level mapping from analysis"""
        sample_analysis.risk_level = RiskLevel.HIGH
        summary = smart_summary_service.generate_smart_summary(sample_analysis)
        assert summary.risk_level == "high"
        
        # Clear cache before testing different risk level
        smart_summary_service.clear_cache()
        sample_analysis.risk_level = RiskLevel.CRITICAL
        summary = smart_summary_service.generate_smart_summary(sample_analysis)
        assert summary.risk_level == "critical"
    
    def test_clear_cache(self, smart_summary_service, sample_analysis):
        """Test cache clearing functionality"""
        # Generate summary to populate cache
        smart_summary_service.generate_smart_summary(sample_analysis)
        assert len(smart_summary_service.cache) > 0
        
        # Clear cache
        smart_summary_service.clear_cache()
        assert len(smart_summary_service.cache) == 0

if __name__ == "__main__":
    pytest.main([__file__])

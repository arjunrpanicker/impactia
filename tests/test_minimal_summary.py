"""
Test for the smart impact summary generation functionality
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.smart_summary_service import SmartSummaryService
from app.models.analysis import (
    ChangeAnalysisResponseWithCode, 
    ChangedComponentWithCode,
    MethodWithCode,
    RiskLevel
)

def test_smart_impact_summary_generation():
    # Setup mock analysis response
    mock_response = ChangeAnalysisResponseWithCode(
        summary="This change adds a new feature for user authentication",
        changed_components=[
            ChangedComponentWithCode(
                file_path="src/auth.py",
                risk_level=RiskLevel.MEDIUM,
                methods=[
                    MethodWithCode(
                        name="authenticate_user",
                        summary="Validates user credentials against database",
                        change_type="added",
                        impact_description="New authentication method for user login"
                    ),
                    MethodWithCode(
                        name="validate_token",
                        summary="Validates JWT token",
                        change_type="added",
                        impact_description="Token validation for protected endpoints"
                    )
                ],
                impact_description="Added new authentication module",
                file_summary="Added new authentication module for user management"
            )
        ],
        dependency_chains=[],
        risk_level=RiskLevel.MEDIUM
    )
    
    # Initialize service
    service = SmartSummaryService()
    
    # Generate smart impact summary
    smart_impact_summary = service.get_smart_impact_summary(mock_response)
    
    # Assertions
    assert smart_impact_summary is not None
    assert isinstance(smart_impact_summary, str)
    assert "user authentication" in smart_impact_summary.lower()
    assert "src/auth.py" in smart_impact_summary
    assert "authenticate_user" in smart_impact_summary
    assert "validate_token" in smart_impact_summary
    assert "risk level" in smart_impact_summary.lower()
    
    # Check format
    lines = smart_impact_summary.split('\n')
    # Should have overall summary line
    assert any("authentication" in line for line in lines[:3]), "Missing overall summary"
    # Should have risk level
    assert any("risk level" in line.lower() for line in lines), "Missing risk level"
    # Should have file section
    assert any("in file src/auth.py" in line.lower() for line in lines), "Missing file section"
    
    print("Smart impact summary length:", len(smart_impact_summary))
    print("Approximate token count:", len(smart_impact_summary) // 4)
    print("Smart impact summary:", smart_impact_summary[:100] + "...")
    
    # Check token efficiency (rough estimate)
    full_json_representation = str(mock_response.model_dump())
    token_reduction = (len(full_json_representation) - len(smart_impact_summary)) / len(full_json_representation) * 100
    print(f"Token reduction: ~{token_reduction:.1f}%")
    assert token_reduction > 30, "Not enough token reduction"  # Lower threshold for test data

if __name__ == "__main__":
    test_smart_impact_summary_generation()
    print("All tests passed!")

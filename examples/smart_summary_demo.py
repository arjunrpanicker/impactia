#!/usr/bin/env python3
"""
Example usage of the Smart Summary Service for token-efficient code analysis.

This script demonstrates how to:
1. Perform code analysis
2. Generate smart summaries
3. Use smart summaries for test generation
4. Compare token usage between approaches
"""

import asyncio
import json
from typing import Dict, Any

# Mock data for demonstration
SAMPLE_ANALYSIS_RESPONSE = {
    "summary": """
    This change introduces a new user authentication system with enhanced security features.
    The implementation includes JWT token validation, password hashing with bcrypt, and 
    comprehensive input validation. The authentication service integrates with the existing
    user management system and adds new endpoints for login, logout, and token refresh.
    Changes affect multiple components including the API layer, service layer, and data
    access layer. This is a significant enhancement that improves security posture and
    user experience.
    """,
    "changed_components": [
        {
            "file_path": "src/services/AuthenticationService.cs",
            "methods": [
                {
                    "name": "AuthenticateUser",
                    "summary": "Validates user credentials and generates JWT token",
                    "change_type": "added",
                    "impact_description": "New authentication method"
                },
                {
                    "name": "ValidateToken",
                    "summary": "Validates JWT token and extracts user claims",
                    "change_type": "added", 
                    "impact_description": "New token validation"
                }
            ],
            "impact_description": "New authentication service implementation",
            "risk_level": "high",
            "associated_unit_tests": ["AuthenticationServiceTests.cs"],
            "file_summary": "Core authentication service"
        },
        {
            "file_path": "src/controllers/AuthController.cs",
            "methods": [
                {
                    "name": "Login",
                    "summary": "Login endpoint with credential validation",
                    "change_type": "added",
                    "impact_description": "New login API endpoint"
                },
                {
                    "name": "Logout", 
                    "summary": "Logout endpoint with token invalidation",
                    "change_type": "added",
                    "impact_description": "New logout API endpoint"
                }
            ],
            "impact_description": "New authentication API endpoints",
            "risk_level": "medium",
            "associated_unit_tests": ["AuthControllerTests.cs"],
            "file_summary": "Authentication API controller"
        }
    ],
    "dependency_chains": [
        {
            "file_path": "src/services/AuthenticationService.cs",
            "methods": [
                {
                    "name": "AuthenticateUser",
                    "summary": "Main authentication method"
                }
            ],
            "impacted_files": [
                {
                    "file_path": "src/services/UserService.cs",
                    "methods": [
                        {
                            "name": "GetUserByEmail",
                            "summary": "Retrieves user by email"
                        }
                    ],
                    "file_summary": "User management service",
                    "change_impact": "Will be called by authentication service"
                }
            ],
            "associated_unit_tests": ["UserServiceTests.cs"]
        }
    ],
    "risk_level": "high"
}

def demonstrate_smart_summary():
    """Demonstrate smart summary generation and token savings"""
    print("🚀 Smart Summary Service Demonstration")
    print("=" * 50)
    
    # Simulate original analysis response size
    original_content = json.dumps(SAMPLE_ANALYSIS_RESPONSE, indent=2)
    original_tokens = len(original_content) // 4  # Rough token estimation
    
    print(f"📊 Original Analysis Size:")
    print(f"   Characters: {len(original_content):,}")
    print(f"   Estimated Tokens: {original_tokens:,}")
    print()
    
    # Simulate smart summary
    smart_summary = {
        "change_type": "feature",
        "scope": "system", 
        "risk_level": "high",
        "modified_methods": [],
        "new_methods": [
            {"name": "AuthenticateUser", "signature": "AuthenticateUser(email, password)", "change_type": "added"},
            {"name": "ValidateToken", "signature": "ValidateToken(token)", "change_type": "added"},
            {"name": "Login", "signature": "Login(credentials)", "change_type": "added"}
        ],
        "deleted_methods": [],
        "critical_dependencies": ["src/services/UserService.cs", "src/controllers/AuthController.cs"],
        "functional_summary": "This change introduces a new user authentication system with enhanced security features. The implementation includes JWT token validation, password hashing with bcrypt, and comprehensive input validation.",
        "test_focus_areas": ["security", "api_integration", "input_validation", "error_handling"],
        "summary_hash": "a1b2c3d4e5f6g7h8",
        "token_count_estimate": 85
    }
    
    formatted_summary = """
CHANGE SUMMARY:
Type: feature | Scope: system | Risk: high

FUNCTIONAL CHANGE: This change introduces a new user authentication system with enhanced security features. The implementation includes JWT token validation, password hashing with bcrypt, and comprehensive input validation.

MODIFIED METHODS: 0 methods

NEW METHODS: 3 methods
- AuthenticateUser: added
- ValidateToken: added  
- Login: added

DELETED METHODS: 0 methods

CRITICAL DEPENDENCIES: src/services/UserService.cs, src/controllers/AuthController.cs

TEST FOCUS: security, api_integration, input_validation, error_handling
    """.strip()
    
    smart_summary_tokens = len(formatted_summary) // 4
    token_savings = ((original_tokens - smart_summary_tokens) / original_tokens) * 100
    
    print(f"✨ Smart Summary:")
    print(formatted_summary)
    print()
    print(f"📈 Token Efficiency:")
    print(f"   Smart Summary Tokens: {smart_summary_tokens:,}")
    print(f"   Token Savings: {token_savings:.1f}%")
    print(f"   Efficiency Gain: {original_tokens // smart_summary_tokens}x more efficient")
    print()
    
    return smart_summary, formatted_summary

def demonstrate_test_generation_workflow():
    """Demonstrate how smart summaries optimize test generation"""
    print("🧪 Test Generation Workflow")
    print("=" * 50)
    
    _, formatted_summary = demonstrate_smart_summary()
    
    # Simulate test generation prompt with smart summary
    test_generation_prompt = f"""
Generate comprehensive test cases based on this code change summary:

{formatted_summary}

Generate test cases with the following requirements:
1. Focus on the identified test focus areas
2. Include both positive and negative test scenarios  
3. Consider the risk level for test prioritization
4. Cover the modified/new/deleted methods appropriately
5. Include specific test steps and expected results
6. Suggest automation feasibility

Return test cases focusing on security, API integration, input validation, and error handling.
    """.strip()
    
    prompt_tokens = len(test_generation_prompt) // 4
    
    print(f"🔧 Test Generation Prompt (Token Efficient):")
    print(f"   Tokens Used: {prompt_tokens:,}")
    print(f"   Focus Areas: security, api_integration, input_validation, error_handling")
    print(f"   Context: Sufficient for comprehensive test generation")
    print()
    
    # Example generated test case
    sample_test_case = {
        "title": "Authentication API - Valid Login Credentials",
        "description": "Verify successful authentication with valid user credentials",
        "category": "API",
        "priority": "High",
        "test_steps": [
            {
                "step_number": 1,
                "action": "Send POST request to /api/auth/login with valid email and password",
                "expected_result": "Returns 200 OK with JWT token",
                "test_data": "email: test@example.com, password: ValidPassword123!"
            },
            {
                "step_number": 2,
                "action": "Validate JWT token structure and claims",
                "expected_result": "Token contains valid user claims and expiration",
                "test_data": "JWT token from step 1"
            }
        ],
        "automation_feasibility": "High",
        "tags": ["authentication", "security", "api"]
    }
    
    print(f"✅ Example Generated Test Case:")
    print(f"   Title: {sample_test_case['title']}")
    print(f"   Category: {sample_test_case['category']}")
    print(f"   Priority: {sample_test_case['priority']}")
    print(f"   Steps: {len(sample_test_case['test_steps'])}")
    print(f"   Automation: {sample_test_case['automation_feasibility']}")
    print()

def demonstrate_api_usage():
    """Demonstrate API endpoint usage patterns"""
    print("🌐 API Usage Patterns") 
    print("=" * 50)
    
    print("1️⃣ Traditional Workflow (Legacy):")
    print("   POST /analyze -> Full Analysis (1000+ tokens)")
    print("   POST /generate-tests -> Full Analysis Input (1000+ tokens)")
    print("   Total: ~2000+ tokens")
    print()
    
    print("2️⃣ Smart Summary Workflow (Default - Automatic):")
    print("   POST /analyze -> Full Analysis + Smart Summary (1000 + 200 tokens)")
    print("   POST /generate-tests -> Smart Summary Auto-Used (200 tokens)")
    print("   Total: ~1200 tokens (40% savings)")
    print("   ✨ No workflow changes required!")
    print()
    
    print("3️⃣ Multiple Test Generation (Massive Savings):")
    print("   POST /analyze -> Full Analysis + Smart Summary (1000 + 200 tokens)")
    print("   POST /generate-tests -> Smart Summary (200 tokens) × N times")
    print("   Savings: (1000-200) × N additional tokens saved")
    print()
    
    print("💡 Best Practices:")
    print("   • Default behavior uses smart summaries automatically")
    print("   • Set use_smart_summary: false for legacy behavior")
    print("   • Leverage embedded smart summaries for repeated operations")
    print("   • Monitor token usage with built-in estimation")
    print("   • No API changes required for existing integrations")

if __name__ == "__main__":
    print("🎯 Impactia Smart Summary Service")
    print("Demonstrating Internal Token-Efficient Code Analysis")
    print()
    
    demonstrate_smart_summary()
    print()
    demonstrate_test_generation_workflow()
    print()
    demonstrate_api_usage()
    print()
    print("✨ Smart Summary Service provides automatic token savings")
    print("   while maintaining comprehensive analysis quality!")
    print("🔒 Internal implementation - no exposed endpoints!")
    print("🚀 Seamless integration - existing workflows unchanged!")

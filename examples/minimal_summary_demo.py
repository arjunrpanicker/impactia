"""
Smart Impact Summary Usage Example

This script demonstrates how to use the smart impact summary for efficient test generation.
"""

import requests
import json

# Example analysis response with smart impact summary
ANALYSIS_RESPONSE_EXAMPLE = {
    "summary": "This change introduces a new user authentication system with enhanced security features.",
    "changed_components": [
        # components would be here
    ],
    "risk_level": "HIGH",
    "smart_impact_summary": """Enhanced user authentication with JWT tokens and security features. Overall change type: feature, Risk level: high
Test focus areas: security, api_integration, error_handling

In file src/services/AuthenticationService.cs, the changes are:
  - AuthenticateUser (added): Validates user credentials and generates JWT token
    Impact: New authentication method
  - ValidateToken (added): Validates JWT token and extracts user claims 
    Impact: New token validation
  File impact: New authentication service implementation

In file src/controllers/AuthController.cs, the changes are:
  - Login (added): Login endpoint with credential validation
    Impact: New login API endpoint
  - Logout (added): Logout endpoint with token invalidation
    Impact: New logout API endpoint
  File impact: New authentication API endpoints

Dependencies affected:
  - Changes in src/services/AuthenticationService.cs impact:
    * src/services/UserService.cs
"""
}

def generate_tests_with_smart_impact_summary():
    """Example of using the smart impact summary for test generation"""
    url = "http://localhost:8000/generate-tests"
    
    # Real-world usage would get this from the /analyze endpoint response
    smart_impact_summary = ANALYSIS_RESPONSE_EXAMPLE["smart_impact_summary"]
    
    # Option 1: Passing the smart impact summary directly
    payload = {
        "smart_impact_summary": smart_impact_summary,
        "test_types": ["unit", "api"],
        "framework": "xUnit"
    }
    
    print("Example payload for test generation:")
    print(json.dumps(payload, indent=2))
    print("\n")
    print("=== Token Efficiency ===")
    print(f"Smart impact summary length: {len(smart_impact_summary)} characters")
    print(f"Estimated token count: ~{len(smart_impact_summary) // 4} tokens")
    print(f"Full analysis token count: ~2000 tokens")
    print(f"Token reduction: ~{(2000 - (len(smart_impact_summary) // 4)) / 2000 * 100:.1f}%")
    
    # In a real application, you would:
    # response = requests.post(url, json=payload)
    # return response.json()

def analyze_and_generate_workflow():
    """Example complete workflow from analysis to test generation"""
    print("\n=== Complete Workflow Example ===")
    
    # Step 1: Call analyze endpoint with file changes (pseudo-code)
    print("1. POST /analyze with code changes")
    # analysis_response = requests.post("/analyze", files={"file": open("changes.diff", "rb")})
    
    # Step 2: Extract smart impact summary from response
    print("2. Extract smart_impact_summary from response")
    smart_impact_summary = ANALYSIS_RESPONSE_EXAMPLE["smart_impact_summary"]
    print(f"   Got smart impact summary: {len(smart_impact_summary)} chars (~{len(smart_impact_summary)//4} tokens)")
    
    # Step 3: Use for test generation
    print("3. Call /generate-tests with smart impact summary")
    print("4. Get comprehensive tests with 85% token savings")

if __name__ == "__main__":
    print("=== Smart Impact Summary Demonstration ===")
    print("Showing the most token-efficient way to generate tests\n")
    
    print("Example smart impact summary:")
    print("-" * 50)
    print(ANALYSIS_RESPONSE_EXAMPLE["smart_impact_summary"])
    print("-" * 50 + "\n")
    
    generate_tests_with_smart_impact_summary()
    analyze_and_generate_workflow()
    
    print("\nThis approach provides maximum efficiency with comprehensive context!")

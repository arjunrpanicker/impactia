# Example Usage: Streamlined Test Generation

This document provides practical examples of using the new `/generate-tests-v2` endpoint for maximum efficiency.

## Complete Workflow Example

### Step 1: Analyze Code Changes
```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "file=@repository.zip" \
  -F "pull_request_changes=Modified user validation logic in UserController.cs and UserService.cs"
```

Response (relevant parts):
```json
{
  "summary": "Updated user input validation to include new security checks...",
  "changed_components": [
    {
      "file_path": "src/controllers/UserController.cs",
      "risk_level": "medium",
      "methods": [{"name": "validateUserInput", "change_type": "modified"}]
    },
    {
      "file_path": "src/services/UserService.cs", 
      "risk_level": "low",
      "methods": [{"name": "processUser", "change_type": "modified"}]
    }
  ],
  "smart_impact_summary": "Enhanced user input validation with security checks. Overall change type: feature, Risk level: medium\nTest focus areas: input_validation, security, error_handling\n\nIn file src/controllers/UserController.cs, the changes are:\n  - validateUserInput (modified): Validates user input for security\n    Impact: Enhanced validation logic\n  File impact: Updated validation logic\n\nIn file src/services/UserService.cs, the changes are:\n  - processUser (modified): Processes validated user data\n    Impact: Updated processing logic\n  File impact: Enhanced user processing",
  "dependency_chain_visualization": "UserController -> UserService -> UserRepository -> Database"
}
```

### Step 2: Extract Essential Information
```javascript
// Extract only what's needed for test generation
const testRequest = {
  pull_request_id: "12345",
  modified_files: analysis.changed_components.map(c => c.file_path),
  smart_impact_summary: analysis.smart_impact_summary,
  dependency_visualization: analysis.dependency_chain_visualization,
  ado_config: {
    work_item_id: 67890,
    project_name: "MyProject"
  }
};
```

### Step 3: Generate Tests (Streamlined)
```bash
curl -X POST "http://localhost:8000/generate-tests-v2" \
  -H "Content-Type: application/json" \
  -d '{
    "pull_request_id": "12345",
    "modified_files": [
      "src/controllers/UserController.cs",
      "src/services/UserService.cs"
    ],
    "smart_impact_summary": "Enhanced user input validation with security checks. Overall change type: feature, Risk level: medium\nTest focus areas: input_validation, security, error_handling\n\nIn file src/controllers/UserController.cs, the changes are:\n  - validateUserInput (modified): Validates user input for security\n    Impact: Enhanced validation logic\n  File impact: Updated validation logic\n\nIn file src/services/UserService.cs, the changes are:\n  - processUser (modified): Processes validated user data\n    Impact: Updated processing logic\n  File impact: Enhanced user processing",
    "dependency_visualization": "UserController -> UserService -> UserRepository -> Database",
    "ado_config": {
      "work_item_id": 67890,
      "project_name": "MyProject"
    },
    "test_generation_options": {
      "include_api_tests": true,
      "include_ui_tests": false,
      "max_test_cases": 15
    }
  }'
```

## Response Example

```json
{
  "test_generation_id": "550e8400-e29b-41d4-a716-446655440000",
  "generated_tests": {
    "api_tests": [
      {
        "id": "test_001",
        "title": "Validate User Input - Valid Data",
        "description": "Test user input validation with valid data to ensure proper processing",
        "priority": "High",
        "category": "API",
        "test_steps": [
          {
            "step_number": 1,
            "action": "Send POST request to /api/users with valid user data",
            "expected_result": "Returns 200 OK with user created successfully",
            "test_data": "{\"username\": \"validuser\", \"email\": \"user@example.com\"}"
          },
          {
            "step_number": 2,
            "action": "Verify user data is processed correctly",
            "expected_result": "User is saved in database with proper validation",
            "test_data": null
          }
        ],
        "preconditions": "API endpoint is available and database is accessible",
        "automation_feasibility": "High",
        "estimated_duration": 5,
        "tags": ["validation", "security", "api"],
        "related_code_files": ["src/controllers/UserController.cs", "src/services/UserService.cs"]
      },
      {
        "id": "test_002",
        "title": "Validate User Input - Invalid Data",
        "description": "Test user input validation with invalid data to ensure proper error handling",
        "priority": "Critical",
        "category": "API",
        "test_steps": [
          {
            "step_number": 1,
            "action": "Send POST request to /api/users with invalid user data",
            "expected_result": "Returns 400 Bad Request with validation errors",
            "test_data": "{\"username\": \"\", \"email\": \"invalid-email\"}"
          },
          {
            "step_number": 2,
            "action": "Verify error messages are descriptive",
            "expected_result": "Response includes specific validation error details",
            "test_data": null
          }
        ],
        "preconditions": "API endpoint is available",
        "automation_feasibility": "High",
        "estimated_duration": 3,
        "tags": ["validation", "error_handling", "security"],
        "related_code_files": ["src/controllers/UserController.cs"]
      }
    ],
    "ui_tests": [],
    "integration_tests": [
      {
        "id": "test_003",
        "title": "End-to-End User Validation Flow",
        "description": "Test complete user validation flow from controller to database",
        "priority": "Medium",
        "category": "Integration",
        "test_steps": [
          {
            "step_number": 1,
            "action": "Submit user data through the complete validation pipeline",
            "expected_result": "Data flows correctly through all components",
            "test_data": "{\"username\": \"testuser\", \"email\": \"test@example.com\"}"
          },
          {
            "step_number": 2,
            "action": "Verify database state after processing",
            "expected_result": "User record exists with validated data",
            "test_data": null
          }
        ],
        "preconditions": "All services are running and database is accessible",
        "automation_feasibility": "Medium",
        "estimated_duration": 10,
        "tags": ["integration", "database", "validation"],
        "related_code_files": ["src/controllers/UserController.cs", "src/services/UserService.cs"]
      }
    ]
  },
  "existing_tests": {
    "linked_test_cases": [
      {
        "id": 123,
        "title": "Existing User Controller Tests",
        "state": "Active"
      }
    ],
    "test_suites": [
      {
        "id": 456,
        "name": "User Management Test Suite",
        "test_case_count": 8
      }
    ]
  },
  "traceability_matrix": {
    "work_item_hierarchy": {
      "feature": {
        "id": 67890,
        "title": "Enhanced User Validation",
        "state": "Active"
      }
    },
    "test_coverage_map": {
      "src/controllers/UserController.cs": ["test_001", "test_002", "test_003"],
      "src/services/UserService.cs": ["test_001", "test_003"]
    }
  },
  "recommendations": {
    "priority_tests": ["test_001", "test_002"],
    "coverage_gaps": [],
    "automation_candidates": ["test_001", "test_002"]
  }
}
```

## Comparison: Legacy vs Streamlined

### Legacy Approach (`/generate-tests`)
```json
{
  "pull_request_id": "12345",
  "code_analysis": {
    "summary": "Full detailed summary...",
    "changed_components": [...], // Large array with detailed objects
    "dependency_chains": [...],  // Complex dependency information
    "risk_level": "medium",
    "smart_impact_summary": "...", // This gets used anyway
    "file_changes": [...],       // Redundant with changed_components
    "method_changes": [...],     // Also redundant
    // ... many more fields that aren't used for test generation
  },
  "ado_config": {...}
}
```
**Payload Size**: ~8-12KB  
**Token Usage**: ~3000-4000 tokens  
**Processing Time**: 3-5 seconds

### Streamlined Approach (`/generate-tests-v2`)
```json
{
  "pull_request_id": "12345",
  "modified_files": ["file1.cs", "file2.cs"],
  "smart_impact_summary": "Concise impact description...",
  "dependency_visualization": "A -> B -> C",
  "ado_config": {...}
}
```
**Payload Size**: ~1-2KB  
**Token Usage**: ~400-600 tokens  
**Processing Time**: 1-2 seconds

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: Generate Tests
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  generate-tests:
    runs-on: ubuntu-latest
    steps:
    - name: Analyze Changes
      id: analyze
      run: |
        response=$(curl -s -X POST "${{ env.API_URL }}/analyze" \
          -F "file=@repository.zip" \
          -F "pull_request_changes=${{ github.event.pull_request.title }}")
        echo "analysis=$response" >> $GITHUB_OUTPUT
    
    - name: Generate Tests
      run: |
        curl -X POST "${{ env.API_URL }}/generate-tests-v2" \
          -H "Content-Type: application/json" \
          -d '{
            "pull_request_id": "${{ github.event.pull_request.number }}",
            "modified_files": ${{ fromJson(steps.analyze.outputs.analysis).changed_components | map(.file_path) | toJSON }},
            "smart_impact_summary": "${{ fromJson(steps.analyze.outputs.analysis).smart_impact_summary }}",
            "dependency_visualization": "${{ fromJson(steps.analyze.outputs.analysis).dependency_chain_visualization }}",
            "ado_config": {
              "work_item_id": ${{ env.WORK_ITEM_ID }}
            }
          }'
```

### Azure DevOps Pipeline Example
```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  API_URL: 'https://your-api.azurewebsites.net'

steps:
- task: Bash@3
  displayName: 'Analyze and Generate Tests'
  inputs:
    targetType: 'inline'
    script: |
      # Analyze changes
      analysis=$(curl -s -X POST "$(API_URL)/analyze" \
        -F "file=@$(Build.SourcesDirectory)/repository.zip" \
        -F "pull_request_changes=$(Build.SourceVersionMessage)")
      
      # Extract essential information
      modified_files=$(echo "$analysis" | jq '.changed_components | map(.file_path)')
      smart_summary=$(echo "$analysis" | jq -r '.smart_impact_summary')
      dependencies=$(echo "$analysis" | jq -r '.dependency_chain_visualization')
      
      # Generate tests
      curl -X POST "$(API_URL)/generate-tests-v2" \
        -H "Content-Type: application/json" \
        -d "{
          \"pull_request_id\": \"$(System.PullRequest.PullRequestId)\",
          \"modified_files\": $modified_files,
          \"smart_impact_summary\": \"$smart_summary\",
          \"dependency_visualization\": \"$dependencies\",
          \"ado_config\": {
            \"work_item_id\": $(WORK_ITEM_ID),
            \"project_name\": \"$(System.TeamProject)\"
          }
        }"
```

## Error Handling

### Common Error Scenarios
```json
// Missing required field
{
  "detail": "modified_files is required and cannot be empty"
}

// Invalid work item
{
  "detail": "Work item 12345 not found in Azure DevOps"
}

// ADO integration disabled
{
  "detail": "Azure DevOps integration is required for test generation. Set ENABLE_ADO_INTEGRATION=true to enable it."
}
```

### Retry Logic Example
```javascript
async function generateTestsWithRetry(requestData, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch('/generate-tests-v2', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });
      
      if (response.ok) {
        return await response.json();
      }
      
      if (response.status === 400) {
        // Client error - don't retry
        throw new Error(`Bad request: ${await response.text()}`);
      }
      
      if (attempt === maxRetries) {
        throw new Error(`Failed after ${maxRetries} attempts`);
      }
      
      // Exponential backoff
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
      
    } catch (error) {
      if (attempt === maxRetries) {
        throw error;
      }
    }
  }
}
```

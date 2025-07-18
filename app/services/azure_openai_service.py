import os
import json
import asyncio
from functools import lru_cache
from typing import List, Dict, Any
from openai import AzureOpenAI
from ..models.analysis import RiskLevel, ChangeAnalysisResponse, ChangedComponent, CodeChange
from ..models.analysis import (
    RiskLevel, ChangeAnalysisResponseWithCode, ChangedComponentWithCode, MethodWithCode,
    DependencyChainWithCode, DependentFileWithCode, DependentMethodWithSummary
)
from .change_summary_service import ChangeSummaryService
from .method_extractor import MethodExtractor
from ..utils.diff_utils import is_diff_format

class AzureOpenAIService:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.embeddings_deployment = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME")
        self._embedding_cache = {}
        self._analysis_cache = {}
        self.change_summary_service = ChangeSummaryService()
        self.method_extractor = MethodExtractor()

    @lru_cache(maxsize=100)
    def _get_cached_prompt_template(self, analysis_type: str) -> str:
        """Get cached prompt templates for different analysis types"""
        templates = {
            "impact_analysis": """Analyze these code changes and their dependencies to provide a comprehensive impact analysis in the required JSON format:

CHANGES:
{changes}

{ui_context}

DEPENDENCY INFORMATION:
{dependencies}

SIMILAR CODE PATTERNS:
{similar_code}

{diff_summaries}

Analyze and include in your response:
1. A clear summary of the changes and their impact
2. Detailed analysis of each changed file, including:
   - Changed methods (use exact names as in code, case and underscores must match) and their new behavior
   - Dependent methods in other files that may be affected
   - For UI components:
     * Component rendering and behavior changes
     * User interaction modifications
     * Visual and layout changes
     * State management updates
     * Integration point changes
3. Complete dependency chains showing how changes propagate through the codebase
4. Visualization of dependencies between files

IMPORTANT: Respond with ONLY a valid JSON object matching the structure specified. No additional text or explanations.""",
            
            "method_analysis": """Analyze the following method changes and provide detailed impact analysis:

METHOD CHANGES:
{method_changes}

CONTEXT:
{context}

Provide analysis focusing on:
1. Functional changes in each method
2. Impact on calling methods
3. Data flow changes
4. Error handling modifications

Return as JSON with method-level details."""
        }
        return templates.get(analysis_type, templates["impact_analysis"])
    async def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings for text using Azure OpenAI"""
        # Check cache first
        text_hash = hash(text)
        if text_hash in self._embedding_cache:
            return self._embedding_cache[text_hash]
        
        try:
            response = self.client.embeddings.create(
                model=self.embeddings_deployment,
                input=text
            )
            embedding = response.data[0].embedding
            
            # Cache the result
            self._embedding_cache[text_hash] = embedding
            return embedding
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts in batch"""
        try:
            # Check cache for each text
            results = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                text_hash = hash(text)
                if text_hash in self._embedding_cache:
                    results.append(self._embedding_cache[text_hash])
                else:
                    results.append(None)
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            # Get embeddings for uncached texts
            if uncached_texts:
                response = self.client.embeddings.create(
                    model=self.embeddings_deployment,
                    input=uncached_texts
                )
                
                # Update results and cache
                for i, embedding_data in enumerate(response.data):
                    embedding = embedding_data.embedding
                    result_index = uncached_indices[i]
                    results[result_index] = embedding
                    
                    # Cache the result
                    text_hash = hash(uncached_texts[i])
                    self._embedding_cache[text_hash] = embedding
            
            return results
            
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            raise
    def _extract_methods(self, content: str, file_path: str = "") -> List[Dict[str, str]]:
        """Extract methods from code content"""
        try:
            # Use the enhanced method extractor
            method_infos = self.method_extractor.extract_methods_from_content(content, file_path)
            
            methods = []
            for method_info in method_infos:
                method_content = self.method_extractor.get_method_content(content, method_info)
                methods.append({
                    "name": method_info.name,
                    "content": method_content,
                    "start_line": method_info.start_line,
                    "signature": method_info.signature,
                    "is_async": method_info.is_async,
                    "is_static": method_info.is_static
                })
            
            return methods
        
        except Exception as e:
            print(f"Error extracting methods from {file_path}: {e}")
            return []
    
    def _identify_changed_methods_from_diff(self, changes: List[CodeChange]) -> Dict[str, List[str]]:
        """Identify actual method names that contain changes from diffs"""
        changed_methods_by_file = {}
        
        for change in changes:
            file_path = change.file_path
            changed_methods = []
            
            if change.diff:
                # Use change summary service to identify methods from diff
                changed_methods = self.change_summary_service.identify_methods_from_diff(
                    change.diff, file_path
                )
            elif change.content:
                # For full content, extract all methods (assuming all are changed)
                method_infos = self.method_extractor.extract_methods_from_content(
                    change.content, file_path
                )
                changed_methods = [method.name for method in method_infos]
            
            if changed_methods:
                changed_methods_by_file[file_path] = changed_methods
        
        return changed_methods_by_file

    def _optimize_prompt_content(self, content: str, max_tokens: int = 6000) -> str:
        """Optimize content for prompt to stay within token limits"""
        if len(content) <= max_tokens * 4:  # Rough estimate: 1 token ≈ 4 characters
            return content
        
        # Prioritize keeping method definitions and important sections
        lines = content.split('\n')
        important_lines = []
        regular_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['def ', 'function ', 'class ', 'import ', 'from ']):
                important_lines.append(line)
            else:
                regular_lines.append(line)
        
        # Start with important lines
        result = '\n'.join(important_lines)
        
        # Add regular lines until we reach the limit
        remaining_space = max_tokens * 4 - len(result)
        if remaining_space > 0:
            additional_content = '\n'.join(regular_lines)
            if len(additional_content) <= remaining_space:
                result += '\n' + additional_content
            else:
                result += '\n' + additional_content[:remaining_space] + '\n... (content truncated)'
        
        return result
    async def analyze_impact(self, changes: List[CodeChange], related_code: Dict[str, Any]) -> ChangeAnalysisResponseWithCode:
        """Analyze the impact of code changes using Azure OpenAI and include full method code and impacted file content."""
        import re
        def normalize(name):
            return re.sub(r'[^a-zA-Z0-9]', '', name).lower()
        
        # Detect UI components
        ui_files = [change for change in changes if any(change.file_path.endswith(ext) for ext in ['.jsx', '.tsx', '.vue', '.svelte', '.html', '.css'])]
        is_ui_change = len(ui_files) > 0
        
        # Format changes into a readable structure
        formatted_changes = []
        for change in changes:
            change_text = f"\nFile: {change.file_path}\n"
            change_text += f"Type: {change.change_type}\n"
            if change.diff:
                change_text += f"Diff:\n{change.diff}\n"
            elif change.content:
                # Optimize content for prompt
                optimized_content = self._optimize_prompt_content(change.content)
                change_text += f"Content:\n{optimized_content}\n"
            formatted_changes.append(change_text)

        # Add UI-specific context if needed
        ui_context = ""
        if is_ui_change:
            ui_context = """
            For UI components, analyze:
            1. Component Structure:
               - Component hierarchy
               - Props and state management
               - Event handlers
               - Conditional rendering
               - Styling changes
            
            2. User Interactions:
               - Click events
               - Form submissions
               - Input changes
               - Navigation
               - Modal/overlay interactions
            
            3. Visual Elements:
               - Layout changes
               - Styling modifications
               - Responsive design
               - Accessibility attributes
            
            4. State Management:
               - Local state changes
               - Global state updates
               - Context usage
               - Props drilling
            
            5. Integration Points:
               - API calls
               - Event propagation
               - Parent-child communication
               - Route changes
            """

        # Format dependencies information
        dependencies_text = "\nDependency Analysis:\n"
        if "direct_dependencies" in related_code:
            deps = related_code["direct_dependencies"]
            dependencies_text += "\nIncoming References (files that depend on the changed files):\n"
            for ref in deps.get("incoming", []):
                dependencies_text += f"- {ref}\n"
            
            dependencies_text += "\nOutgoing References (files that the changed files depend on):\n"
            for ref in deps.get("outgoing", []):
                dependencies_text += f"- {ref}\n"

        # Add enhanced dependency information
        if "enhanced_dependencies" in related_code:
            enhanced_deps = related_code["enhanced_dependencies"]
            dependencies_text += "\nEnhanced Dependency Analysis:\n"
            
            for method_call_info in enhanced_deps.get("method_calls", []):
                dependencies_text += f"\nFile: {method_call_info['file']}\n"
                dependencies_text += f"Method calls: {', '.join(method_call_info['calls'])}\n"
            
            for import_info in enhanced_deps.get("import_dependencies", []):
                dependencies_text += f"\nFile: {import_info['file']}\n"
                dependencies_text += f"Imports: {', '.join(import_info['imports'])}\n"
        # Add dependency chain information
        if "dependency_chains" in related_code:
            dependencies_text += "\nDetailed Dependency Chains:\n"
            for chain in related_code["dependency_chains"]:
                dependencies_text += f"\nFile: {chain['file_path']}\n"
                dependencies_text += "Dependent Files:\n"
                for dep in chain.get("dependent_files", []):
                    dependencies_text += f"- {dep['file_path']}\n"
                    for method in dep.get("methods", []):
                        dependencies_text += f"  - Method {method['name']}: {method['summary']}\n"

        if "dependency_visualization" in related_code:
            dependencies_text += "\nDependency Flow:\n"
            for viz in related_code["dependency_visualization"]:
                dependencies_text += f"- {viz}\n"

        # Format similar code information
        similar_code_text = "\nSimilar Code Analysis:\n"
        if "similar_code" in related_code:
            similar = related_code["similar_code"]
            
            similar_code_text += "\nSimilar Files:\n"
            for file in similar.get("files", []):
                similar_code_text += f"- {file['path']} (similarity: {file['similarity']:.2f})\n"
                for method in file.get("methods", []):
                    similar_code_text += f"  - Method: {method.get('name', 'unknown')}\n"
            
            similar_code_text += "\nSimilar Methods:\n"
            for method in similar.get("methods", []):
                similar_code_text += f"- {method['name']} in {method.get('file_path', 'unknown')} (similarity: {method['similarity']:.2f})\n"

        # --- Functional Diff Summaries ---
        # Build a map of file_path -> {method_name: summary}
        functional_summaries = {}
        for change in changes:
            file_path = change.file_path
            base_code = ''  # We don't have base code in this context
            updated_code = change.content or ''
            
            # Generate change analysis for the file
            if updated_code:
                change_analysis = self.change_summary_service.analyze_file_changes(
                    file_path, base_code, updated_code
                )
                
                # Create summaries for each method
                method_summaries = {}
                for method_change in change_analysis.get('method_changes', []):
                    method_name = method_change['method_name']
                    summary = method_change['summary']
                    method_summaries[method_name] = summary
                
                functional_summaries[file_path] = method_summaries
        # --- End Functional Diff Summaries ---

        # When building the LLM prompt, include the functional summaries for each changed/impacted method
        # Instead of sending full code or raw diff, send the summary
        # Example: Add to the prompt for each changed method:
        # "Functional change summary for {file_path}.{method_name}: {summary}"
        # You can concatenate these summaries and add to the prompt before the rest of the context
        diff_summaries_text = ""
        for file_path, methods in functional_summaries.items():
            for method_name, summary in methods.items():
                diff_summaries_text += f"\nFunctional change summary for {file_path}.{method_name}:\n{summary}\n"

        # Prepare the prompt
        prompt_template = self._get_cached_prompt_template("impact_analysis")
        prompt = prompt_template.format(
            changes=''.join(formatted_changes),
            ui_context=ui_context,
            dependencies=dependencies_text,
            similar_code=similar_code_text,
            diff_summaries=diff_summaries_text
        )
        
        # Update prompt to instruct LLM to use exact method names as in code, not to guess, and only include top-level functions
        prompt = prompt.replace(
            "- Changed methods (use exact names as in code, case and underscores must match) and their new behavior",
            "- Changed methods with detailed summaries of what changed and why it matters (use exact names as in code, case and underscores must match, and ONLY include top-level function or method names that actually exist in the provided code for each file; do NOT guess, hallucinate, or include variables/classes/inner blocks)"
        )
        
        # Check analysis cache
        prompt_hash = hash(prompt)
        if prompt_hash in self._analysis_cache:
            print("[DEBUG] Using cached analysis result")
            analysis_json = self._analysis_cache[prompt_hash]
        else:
        # Get completion from Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system", 
                        "content": """You are a code analysis expert. Analyze the impact of code changes and their dependencies to provide detailed insights.
IMPORTANT: Your response must be ONLY a valid JSON object with no additional text or explanation.

Required JSON structure:
{
    "summary": "Brief summary of changes and their impact",
    "changed_components": [
        {
            "file_path": "path/to/changed/file",
            "file_summary": "High-level summary of what changed in this file",
            "methods": [
                {
                    "name": "methodName1",
                    "summary": "Detailed summary of what changed in this method",
                    "change_type": "added|modified|removed",
                    "impact_description": "How this change affects the system"
                }
            ],
            "impact_description": "Description of how these methods are impacted",
            "risk_level": "low|medium|high|critical",
            "associated_unit_tests": ["tests/UnitTests/path/to/test1.cs", "tests/UnitTests/path/to/test2.cs"]
        }
    ],
    "dependency_chains": [
        {
            "file_path": "path/to/changed/file",
            "methods": [
                {
                    "name": "methodName",
                    "summary": "Description of how this method is impacted"
                }
            ],
            "impacted_files": [
                {
                    "file_path": "path/to/dependent/file",
                    "file_summary": "Summary of how this file is impacted by the changes",
                    "change_impact": "Specific impact description for this dependent file",
                    "methods": [
                        {
                            "name": "methodName",
                            "summary": "Description of how this dependent method is affected"
                        }
                    ]
                }
            ],
            "associated_unit_tests": ["tests/UnitTests/path/to/test1.cs", "tests/UnitTests/path/to/test2.cs"]
        }
    ],
    "dependency_chain_visualization": ["file1.cs->file2.cs"]
}

Rules:
1. Response must be ONLY the JSON object, no other text
2. All arrays must have at least one item
3. All fields are required except dependency_chains and dependency_chain_visualization
4. Use proper JSON formatting with double quotes for strings
5. Focus on change summaries and impact analysis, NOT code content
6. Include both direct changes and dependency impacts
7. For dependency chains:
   - Show how changes propagate through the codebase
   - Include all affected methods in each file
   - Provide clear summaries of impact at each level
   - Consider both direct and indirect dependencies
   - Include methods that call or are called by changed methods
   - Include methods that use or are used by changed methods
8. For risk levels:
   - low: Minor changes with no significant impact
   - medium: Changes that affect specific functionality
   - high: Changes that affect multiple components
   - critical: Changes that affect core functionality or security
9. For associated_unit_tests:
   - Include full paths to unit test files only
   - Focus on tests that directly verify the changed functionality
   - Include tests for dependent components that might be affected
   - All test paths should be under tests/UnitTests/ directory
10. For UI components:
    - Treat component methods as regular methods
    - Include component lifecycle methods
    - Consider event handlers as methods
    - Include state management methods
    - Consider UI-specific dependencies
11. For method summaries:
    - Explain WHAT changed (functionality, behavior, logic)
    - Explain WHY it matters (business impact, technical impact)
    - Be specific about the nature of the change
    - Focus on functional changes, not implementation details
12. For file summaries:
    - Provide high-level overview of changes in the file
    - Explain the overall purpose and impact
    - Connect individual method changes to file-level impact"""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=3000,
                response_format={ "type": "json_object" }
            )
            
            # Parse and cache the response
            response_text = response.choices[0].message.content.strip()
            if not response_text:
                raise Exception("Empty response from GPT")
                
            analysis_json = json.loads(response_text)
            self._analysis_cache[prompt_hash] = analysis_json
        
        try:
            # Validate required fields
            required_fields = ["summary", "changed_components"]
            missing_fields = [field for field in required_fields if field not in analysis_json]
            if missing_fields:
                raise KeyError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # After parsing the LLM response (analysis_json):
            # 1. For each changed file, extract all methods and their code from uploaded content
            file_method_map = {}
            uploaded_content_map = {change.file_path: change.content or '' for change in changes}
            for change in changes:
                file_path = change.file_path
                file_content = change.content or ''
                methods = self._extract_methods(file_content, file_path)
                # Normalize method names for robust matching
                file_method_map[file_path] = {normalize(m['name']): m['content'] for m in methods}
            # 2. Build changed_components with robust method code matching
            changed_components = []
            for comp in analysis_json["changed_components"]:
                file_path = comp["file_path"]
                
                # Handle both old format (list of strings) and new format (list of objects)
                method_objs = []
                methods_data = comp.get("methods", [])
                
                if methods_data and isinstance(methods_data[0], dict):
                    # New format with method objects
                    for method_data in methods_data:
                        method_objs.append(MethodWithCode(
                            name=method_data.get("name", ""),
                            summary=method_data.get("summary", ""),
                            change_type=method_data.get("change_type", "modified"),
                            impact_description=method_data.get("impact_description", "")
                        ))
                else:
                    # Old format with method names only - convert to new format
                    for method_name in methods_data:
                        method_objs.append(MethodWithCode(
                            name=method_name,
                            summary=f"Method '{method_name}' has been modified",
                            change_type="modified",
                            impact_description="Impact analysis not available in legacy format"
                        ))
                
        
        # Get the actual changed methods from diffs/content
        changed_methods_by_file = self._identify_changed_methods_from_diff(changes)
        
                changed_components.append(ChangedComponentWithCode(
                    file_path=file_path,
                    methods=method_objs,
                    impact_description=comp["impact_description"],
                    risk_level=comp["risk_level"],
                    associated_unit_tests=comp["associated_unit_tests"],
                    file_summary=comp.get("file_summary", "File has been modified")
                ))
            # 3. For dependency_chains, add full file content to each impacted file
            dependency_chains = []
            for chain in (analysis_json.get("dependency_chains") or []):
            # Use actual changed methods if available, otherwise fall back to LLM response
            actual_changed_methods = changed_methods_by_file.get(file_path, [])
            
                impacted_files = []
                for dep in chain.get("impacted_files", []):
                    dep_file_path = dep["file_path"]
                    
                    methods = [
                        DependentMethodWithSummary(name=m["name"], summary=m["summary"]) for m in dep.get("methods", [])
                    ]
                    method_name = method_data.get("name", "")
                    # Only include if it's actually a changed method or if we don't have diff info
                    if not actual_changed_methods or method_name in actual_changed_methods:
                        method_objs.append(MethodWithCode(
                            name=method_name,
                            summary=method_data.get("summary", ""),
                            change_type=method_data.get("change_type", "modified"),
                            impact_description=method_data.get("impact_description", "")
                        ))
                methods = [
                    DependentMethodWithSummary(name=m["name"], summary=m["summary"]) for m in chain.get("methods", [])
                ]
                dependency_chains.append(DependencyChainWithCode(
                    file_path=chain["file_path"],
                    methods=methods,
                    impacted_files=impacted_files,
                    associated_unit_tests=chain.get("associated_unit_tests", [])
                ))
            return ChangeAnalysisResponseWithCode(
                    # Only include if it's actually a changed method or if we don't have diff info
                    if not actual_changed_methods or method_name in actual_changed_methods:
                        method_objs.append(MethodWithCode(
                            name=method_name,
                            summary=f"Method '{method_name}' has been modified",
                            change_type="modified",
                            impact_description="Impact analysis not available in legacy format"
                        ))
            
        except json.JSONDecodeError as e:
            print(f"Raw GPT response: {response_text if 'response_text' in locals() else 'No response'}")
            raise Exception(f"Failed to parse GPT response as JSON: {str(e)}")
        except KeyError as e:
            raise Exception(f"Missing required field in GPT response: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid value in GPT response: {str(e)}")
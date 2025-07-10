import os
import re
from typing import List, Dict, Any, Tuple, Optional
from ..models.impact import ChangedMethod, ImpactedMethod, ImpactAnalysisResponse
from ..services.diff_service import generate_functional_diff, list_top_level_functions
from ..services.rag_service import RAGService
from ..services.azure_openai_service import AzureOpenAIService

class ImpactService:
    def __init__(self):
        self.rag_service = RAGService()
        self.openai_service = AzureOpenAIService()

    def _extract_methods_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract methods from code content with their positions"""
        import re
        
        methods = []
        lines = content.split('\n')
        
        # Match common method patterns
        patterns = [
            # Python
            (r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:', 1, 'python'),
            # JavaScript/TypeScript
            (r'(async\s+)?function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)', 2, 'javascript'),
            # C#/Java
            (r'(public|private|protected|internal)?\s+[a-zA-Z_<>[\]]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)', 2, 'csharp'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, group_idx, lang in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    method_name = match.group(group_idx)
                    
                    # Extract complete function using regex
                    if lang == 'python':
                        # Find the complete function definition
                        func_pattern = rf'def\s+{re.escape(method_name)}\s*\([^)]*\)\s*:.*?(?=\n\s*def|\n\s*class|\Z)'
                        func_match = re.search(func_pattern, content, re.DOTALL | re.MULTILINE)
                        if func_match:
                            method_content = func_match.group(0)
                        else:
                            # Fallback to context window
                            start_line = max(0, i - 5)
                            end_line = min(len(lines), i + 50)
                            method_content = '\n'.join(lines[start_line:end_line])
                    else:
                        # For non-Python, use larger context window
                        start_line = max(0, i - 5)
                        end_line = min(len(lines), i + 50)
                        method_content = '\n'.join(lines[start_line:end_line])
                    
                    methods.append({
                        "name": method_name,
                        "content": method_content,
                        "start_line": i,
                        "language": lang
                    })
        
        return methods

    def _identify_changed_methods(self, base_content: str, updated_content: str, file_path: str) -> List[ChangedMethod]:
        """Identify which methods have changed between base and updated versions"""
        changed_methods = []
        
        # Get methods from both versions
        base_methods = {m['name']: m for m in self._extract_methods_from_content(base_content)}
        updated_methods = {m['name']: m for m in self._extract_methods_from_content(updated_content)}
        
        # Find changed methods
        for method_name in updated_methods:
            if method_name in base_methods:
                # Method exists in both - check if content changed
                base_method_content = base_methods[method_name]['content']
                updated_method_content = updated_methods[method_name]['content']
                
                if base_method_content.strip() != updated_method_content.strip():
                    # Method was modified - generate functional diff summary
                    summary = generate_functional_diff(base_content, updated_content, method_name)
                    changed_methods.append(ChangedMethod(
                        file_path=file_path,
                        method=method_name,
                        summary=summary
                    ))
            else:
                # New method added
                changed_methods.append(ChangedMethod(
                    file_path=file_path,
                    method=method_name,
                    summary="New method added"
                ))
        
        # Check for deleted methods
        for method_name in base_methods:
            if method_name not in updated_methods:
                changed_methods.append(ChangedMethod(
                    file_path=file_path,
                    method=method_name,
                    summary="Method deleted"
                ))
        
        return changed_methods

    async def _find_impacted_methods(self, changed_methods: List[ChangedMethod]) -> List[ImpactedMethod]:
        """Find methods that are impacted by the changed methods using RAG"""
        impacted_methods = []
        
        try:
            # Get all code embeddings from the database
            result = self.rag_service.supabase.table("code_embeddings").select("*").execute()
            
            for changed_method in changed_methods:
                # Search for methods that reference this changed method
                for item in result.data:
                    content = item.get("content", "").lower()
                    current_path = item.get("file_path", "")
                    methods = item.get("metadata", {}).get("methods", [])
                    
                    # Skip the same file to avoid self-references
                    if current_path == changed_method.file_path:
                        continue
                    
                    # Look for references to the changed method
                    method_name_lower = changed_method.method.lower()
                    if method_name_lower in content:
                        # Find specific methods that reference the changed method
                        for method in methods:
                            method_content = method.get("content", "").lower()
                            method_name = method.get("name", "")
                            
                            if method_name_lower in method_content:
                                # Determine the type of impact
                                impact_reason = f"calls {changed_method.method}()"
                                if f"{method_name_lower}(" in method_content:
                                    impact_reason = f"calls {changed_method.method}()"
                                elif f"import" in method_content and method_name_lower in method_content:
                                    impact_reason = f"imports from {changed_method.file_path}"
                                elif f"from" in method_content and method_name_lower in method_content:
                                    impact_reason = f"imports {changed_method.method}"
                                
                                # Generate impact description based on the change summary
                                impact_description = self._generate_impact_description(
                                    changed_method.summary, 
                                    method_name,
                                    impact_reason
                                )
                                
                                impacted_methods.append(ImpactedMethod(
                                    file_path=current_path,
                                    method=method_name,
                                    impact_reason=impact_reason,
                                    impact_description=impact_description
                                ))
        
        except Exception as e:
            print(f"Error finding impacted methods: {str(e)}")
        
        return impacted_methods

    def _generate_impact_description(self, change_summary: str, impacted_method: str, impact_reason: str) -> str:
        """Generate a description of how the change might impact the dependent method"""
        # Simple rule-based impact description generation
        if "added validation" in change_summary.lower():
            return f"May now raise validation errors that {impacted_method} needs to handle"
        elif "removed" in change_summary.lower():
            return f"Functionality removed from dependency may cause {impacted_method} to fail"
        elif "added logging" in change_summary.lower():
            return f"New log entries may be generated when {impacted_method} executes"
        elif "changed return" in change_summary.lower():
            return f"Return value changes may affect how {impacted_method} processes results"
        elif "added parameter" in change_summary.lower():
            return f"New parameter requirements may break calls from {impacted_method}"
        elif "error handling" in change_summary.lower():
            return f"Error handling changes may affect exception flow in {impacted_method}"
        else:
            return f"Changes in dependency may affect behavior of {impacted_method}"

    def _build_dependency_chain(self, changed_methods: List[ChangedMethod], impacted_methods: List[ImpactedMethod]) -> List[str]:
        """Build dependency chain showing how changes propagate"""
        dependency_chain = []
        
        for changed_method in changed_methods:
            for impacted_method in impacted_methods:
                # Check if this impacted method is related to this changed method
                if (changed_method.method.lower() in impacted_method.impact_reason.lower() or
                    changed_method.file_path in impacted_method.impact_reason):
                    
                    chain_link = f"{changed_method.method} -> {impacted_method.method}"
                    if chain_link not in dependency_chain:
                        dependency_chain.append(chain_link)
        
        return dependency_chain

    async def analyze_impact(self, base_files: List[bytes], updated_files: List[bytes], file_paths: List[str]) -> ImpactAnalysisResponse:
        """Analyze the impact of code changes"""
        all_changed_methods = []
        
        # Process each file pair
        for i, (base_content_bytes, updated_content_bytes) in enumerate(zip(base_files, updated_files)):
            try:
                # Decode file contents
                base_content = base_content_bytes.decode('utf-8')
                updated_content = updated_content_bytes.decode('utf-8')
                
                # Use provided file path or generate a default one
                file_path = file_paths[i] if i < len(file_paths) else f"file_{i+1}"
                
                # Identify changed methods in this file
                changed_methods = self._identify_changed_methods(base_content, updated_content, file_path)
                all_changed_methods.extend(changed_methods)
                
            except UnicodeDecodeError:
                print(f"Warning: Could not decode file {i+1} as UTF-8")
                continue
            except Exception as e:
                print(f"Error processing file {i+1}: {str(e)}")
                continue
        
        # Find impacted methods using RAG
        impacted_methods = await self._find_impacted_methods(all_changed_methods)
        
        # Build dependency chain
        dependency_chain = self._build_dependency_chain(all_changed_methods, impacted_methods)
        
        return ImpactAnalysisResponse(
            changed_methods=all_changed_methods,
            impacted_methods=impacted_methods,
            dependency_chain=dependency_chain
        )
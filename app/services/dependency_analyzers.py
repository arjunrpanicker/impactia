import re
import ast
from typing import List, Dict, Any
from ..interfaces.embedding_provider import DependencyAnalyzer

class MethodCallAnalyzer(DependencyAnalyzer):
    """Analyzes method call dependencies"""
    
    async def analyze_dependencies(self, code_changes: List[Dict]) -> Dict[str, Any]:
        dependencies = []
        
        for change in code_changes:
            content = change.get('content', '')
            method_calls = self._extract_method_calls(content)
            
            dependencies.append({
                'file': change.get('file_path', ''),
                'type': 'method_calls',
                'dependencies': method_calls
            })
        
        return {'method_calls': dependencies}
    
    def _extract_method_calls(self, content: str) -> List[str]:
        """Extract method calls using AST when possible"""
        try:
            tree = ast.parse(content)
            calls = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if hasattr(node.func, 'id'):
                        calls.append(node.func.id)
                    elif hasattr(node.func, 'attr'):
                        calls.append(node.func.attr)
            
            return list(set(calls))
        except SyntaxError:
            # Fallback to regex for non-Python or invalid syntax
            pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            matches = re.findall(pattern, content)
            keywords = {'if', 'for', 'while', 'def', 'class', 'return', 'import', 'from', 'try', 'except', 'with'}
            return [match for match in set(matches) if match not in keywords]

class ImportAnalyzer(DependencyAnalyzer):
    """Analyzes import dependencies"""
    
    async def analyze_dependencies(self, code_changes: List[Dict]) -> Dict[str, Any]:
        dependencies = []
        
        for change in code_changes:
            content = change.get('content', '')
            imports = self._extract_imports(content)
            
            dependencies.append({
                'file': change.get('file_path', ''),
                'type': 'imports',
                'dependencies': imports
            })
        
        return {'imports': dependencies}
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract imports using AST when possible"""
        try:
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            return list(set(imports))
        except SyntaxError:
            # Fallback to regex
            import_patterns = [
                r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import',
                r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',
            ]
            
            imports = []
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                imports.extend(matches)
            
            return list(set(imports))

class DataFlowAnalyzer(DependencyAnalyzer):
    """Analyzes data flow dependencies"""
    
    async def analyze_dependencies(self, code_changes: List[Dict]) -> Dict[str, Any]:
        dependencies = []
        
        for change in code_changes:
            content = change.get('content', '')
            data_flow = self._extract_data_flow(content)
            
            dependencies.append({
                'file': change.get('file_path', ''),
                'type': 'data_flow',
                'dependencies': data_flow
            })
        
        return {'data_flow': dependencies}
    
    def _extract_data_flow(self, content: str) -> Dict[str, List[str]]:
        """Extract data flow patterns"""
        try:
            tree = ast.parse(content)
            assignments = []
            parameters = []
            returns = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if hasattr(target, 'id'):
                            assignments.append(target.id)
                elif isinstance(node, ast.FunctionDef):
                    for arg in node.args.args:
                        parameters.append(arg.arg)
                elif isinstance(node, ast.Return) and node.value:
                    if hasattr(node.value, 'id'):
                        returns.append(node.value.id)
            
            return {
                'assignments': list(set(assignments)),
                'parameters': list(set(parameters)),
                'returns': list(set(returns))
            }
        except SyntaxError:
            # Fallback to regex
            assignments = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=', content)
            return {'assignments': list(set(assignments))}

class CompositeDependencyAnalyzer(DependencyAnalyzer):
    """Combines multiple dependency analysis strategies"""
    
    def __init__(self, analyzers: List[DependencyAnalyzer]):
        self.analyzers = analyzers
    
    async def analyze_dependencies(self, code_changes: List[Dict]) -> Dict[str, Any]:
        results = {}
        
        for analyzer in self.analyzers:
            try:
                result = await analyzer.analyze_dependencies(code_changes)
                results.update(result)
            except Exception as e:
                print(f"Error in dependency analyzer {type(analyzer).__name__}: {e}")
        
        return results
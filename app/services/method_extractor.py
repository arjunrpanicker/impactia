import ast
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

@dataclass
class MethodInfo:
    name: str
    start_line: int
    end_line: int
    signature: str
    docstring: Optional[str] = None
    is_async: bool = False
    is_static: bool = False
    is_class_method: bool = False

class MethodExtractor:
    """Enhanced method extraction with proper AST parsing and fallback regex"""
    
    def __init__(self):
        self.python_keywords = {
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else',
            'except', 'exec', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'not', 'or', 'pass', 'print', 'raise', 'return', 'try', 'while', 'with',
            'yield', 'True', 'False', 'None'
        }
        
        self.builtin_functions = {
            'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes', 'callable', 'chr',
            'classmethod', 'compile', 'complex', 'delattr', 'dict', 'dir', 'divmod',
            'enumerate', 'eval', 'exec', 'filter', 'float', 'format', 'frozenset',
            'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex', 'id', 'input',
            'int', 'isinstance', 'issubclass', 'iter', 'len', 'list', 'locals',
            'map', 'max', 'memoryview', 'min', 'next', 'object', 'oct', 'open',
            'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed',
            'round', 'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str',
            'sum', 'super', 'tuple', 'type', 'vars', 'zip'
        }

    def extract_methods_from_content(self, content: str, file_path: str = "") -> List[MethodInfo]:
        """Extract methods using AST parsing with regex fallback"""
        file_extension = file_path.split('.')[-1].lower() if '.' in file_path else ''
        
        if file_extension == 'py':
            return self._extract_python_methods(content)
        elif file_extension in ['js', 'ts', 'jsx', 'tsx']:
            return self._extract_javascript_methods(content)
        elif file_extension in ['cs']:
            return self._extract_csharp_methods(content)
        elif file_extension in ['java']:
            return self._extract_java_methods(content)
        else:
            return self._extract_generic_methods(content)

    def _extract_python_methods(self, content: str) -> List[MethodInfo]:
        """Extract Python methods using AST"""
        try:
            tree = ast.parse(content)
            methods = []
            lines = content.split('\n')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip if it's a nested function (not top-level or class method)
                    if self._is_top_level_or_class_method(node, tree):
                        method_info = self._create_python_method_info(node, lines)
                        if method_info:
                            methods.append(method_info)
            
            return methods
            
        except SyntaxError:
            # Fallback to regex for invalid Python syntax
            return self._extract_python_methods_regex(content)

    def _is_top_level_or_class_method(self, func_node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if function is top-level or a class method (not nested)"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.Module)):
                if func_node in node.body:
                    return True
        return False

    def _create_python_method_info(self, node: ast.FunctionDef, lines: List[str]) -> Optional[MethodInfo]:
        """Create MethodInfo from AST FunctionDef node"""
        try:
            # Get method signature
            signature = f"def {node.name}("
            args = []
            
            # Add regular arguments
            for arg in node.args.args:
                args.append(arg.arg)
            
            # Add *args if present
            if node.args.vararg:
                args.append(f"*{node.args.vararg.arg}")
            
            # Add **kwargs if present
            if node.args.kwarg:
                args.append(f"**{node.args.kwarg.arg}")
            
            signature += ", ".join(args) + "):"
            
            # Get docstring
            docstring = None
            if (node.body and isinstance(node.body[0], ast.Expr) and 
                isinstance(node.body[0].value, ast.Constant) and 
                isinstance(node.body[0].value.value, str)):
                docstring = node.body[0].value.value
            
            # Determine method properties
            is_async = isinstance(node, ast.AsyncFunctionDef)
            is_static = any(isinstance(d, ast.Name) and d.id == 'staticmethod' 
                          for d in node.decorator_list)
            is_class_method = any(isinstance(d, ast.Name) and d.id == 'classmethod' 
                                for d in node.decorator_list)
            
            return MethodInfo(
                name=node.name,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                signature=signature,
                docstring=docstring,
                is_async=is_async,
                is_static=is_static,
                is_class_method=is_class_method
            )
            
        except Exception as e:
            print(f"Error creating method info for {node.name}: {e}")
            return None

    def _extract_python_methods_regex(self, content: str) -> List[MethodInfo]:
        """Fallback regex extraction for Python methods"""
        methods = []
        lines = content.split('\n')
        
        # Pattern for Python function definitions - must start with 'def' or 'async def'
        pattern = r'^(\s*)(async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:'
        
        for i, line in enumerate(lines):
            # Skip lines that are clearly variable assignments
            stripped_line = line.strip()
            
            # Skip if line contains '=' before 'def' (variable assignment)
            if '=' in stripped_line:
                equals_pos = stripped_line.find('=')
                def_pos = stripped_line.find('def')
                if def_pos == -1 or equals_pos < def_pos:
                    continue
            
            match = re.match(pattern, line)
            if match:
                indent, is_async, method_name = match.groups()
                
                # Skip if it's clearly a nested function (heavily indented)
                if len(indent) > 8:  # More than 2 levels of indentation
                    continue
                
                methods.append(MethodInfo(
                    name=method_name,
                    start_line=i + 1,
                    end_line=i + 1,  # We don't know the end line with regex
                    signature=line.strip(),
                    is_async=bool(is_async)
                ))
        
        return methods

    def _extract_javascript_methods(self, content: str) -> List[MethodInfo]:
        """Extract JavaScript/TypeScript methods"""
        methods = []
        lines = content.split('\n')
        
        patterns = [
            # Function declarations: function methodName()
            r'^\s*(?:async\s+)?function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(',
            # Method definitions: methodName() or async methodName()
            r'^\s*(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{',
            # Arrow functions: const methodName = () =>
            r'^\s*(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
            # Class methods: methodName() {
            r'^\s*(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{'
        ]
        
        for i, line in enumerate(lines):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    method_name = match.group(1)
                    if method_name not in self.builtin_functions:
                        methods.append(MethodInfo(
                            name=method_name,
                            start_line=i + 1,
                            end_line=i + 1,
                            signature=line.strip(),
                            is_async='async' in line
                        ))
                    break
        
        return methods

    def _extract_csharp_methods(self, content: str) -> List[MethodInfo]:
        """Extract C# methods"""
        methods = []
        lines = content.split('\n')
        
        # C# method pattern: [access modifier] [static] [async] returnType MethodName(params)
        pattern = r'^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?(?:async\s+)?(?:virtual\s+)?(?:override\s+)?[a-zA-Z_<>\[\]]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)'
        
        for i, line in enumerate(lines):
            match = re.search(pattern, line)
            if match:
                method_name = match.group(1)
                # Skip constructors and common keywords
                if (not method_name[0].isupper() or 
                    method_name in ['get', 'set', 'if', 'for', 'while', 'switch']):
                    continue
                    
                methods.append(MethodInfo(
                    name=method_name,
                    start_line=i + 1,
                    end_line=i + 1,
                    signature=line.strip(),
                    is_async='async' in line,
                    is_static='static' in line
                ))
        
        return methods

    def _extract_java_methods(self, content: str) -> List[MethodInfo]:
        """Extract Java methods"""
        methods = []
        lines = content.split('\n')
        
        # Java method pattern: [access modifier] [static] returnType methodName(params)
        pattern = r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?[a-zA-Z_<>\[\]]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)'
        
        for i, line in enumerate(lines):
            match = re.search(pattern, line)
            if match:
                method_name = match.group(1)
                # Skip constructors (start with uppercase) and keywords
                if (method_name[0].isupper() or 
                    method_name in ['if', 'for', 'while', 'switch', 'try', 'catch']):
                    continue
                    
                methods.append(MethodInfo(
                    name=method_name,
                    start_line=i + 1,
                    end_line=i + 1,
                    signature=line.strip(),
                    is_static='static' in line
                ))
        
        return methods

    def _extract_generic_methods(self, content: str) -> List[MethodInfo]:
        """Generic method extraction for unknown file types"""
        methods = []
        lines = content.split('\n')
        
        # Very basic pattern for function-like constructs
        pattern = r'^\s*(?:function\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*[{:]'
        
        for i, line in enumerate(lines):
            match = re.search(pattern, line)
            if match:
                method_name = match.group(1)
                if (method_name not in self.python_keywords and 
                    method_name not in self.builtin_functions):
                    methods.append(MethodInfo(
                        name=method_name,
                        start_line=i + 1,
                        end_line=i + 1,
                        signature=line.strip()
                    ))
        
        return methods

    def get_method_content(self, content: str, method_info: MethodInfo) -> str:
        """Extract the full content of a method"""
        lines = content.split('\n')
        
        if method_info.end_line > method_info.start_line:
            # We have accurate line numbers from AST
            method_lines = lines[method_info.start_line - 1:method_info.end_line]
            return '\n'.join(method_lines)
        else:
            # Fallback: try to extract method content heuristically
            start_idx = method_info.start_line - 1
            if start_idx >= len(lines):
                return lines[start_idx] if start_idx < len(lines) else ""
            
            # For Python, find the end by indentation
            if any(keyword in method_info.signature for keyword in ['def ', 'async def']):
                return self._extract_python_method_content(lines, start_idx)
            else:
                # For other languages, try to find closing brace
                return self._extract_braced_method_content(lines, start_idx)

    def _extract_python_method_content(self, lines: List[str], start_idx: int) -> str:
        """Extract Python method content by indentation"""
        if start_idx >= len(lines):
            return ""
        
        method_lines = [lines[start_idx]]
        base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.strip() == "":
                method_lines.append(line)
                continue
            
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent and line.strip():
                break
            
            method_lines.append(line)
            
            # Stop at reasonable length
            if len(method_lines) > 50:
                break
        
        return '\n'.join(method_lines)

    def _extract_braced_method_content(self, lines: List[str], start_idx: int) -> str:
        """Extract method content for brace-based languages"""
        if start_idx >= len(lines):
            return ""
        
        method_lines = [lines[start_idx]]
        brace_count = lines[start_idx].count('{') - lines[start_idx].count('}')
        
        if brace_count <= 0:
            return lines[start_idx]
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            method_lines.append(line)
            brace_count += line.count('{') - line.count('}')
            
            if brace_count <= 0:
                break
                
            # Stop at reasonable length
            if len(method_lines) > 50:
                break
        
        return '\n'.join(method_lines)
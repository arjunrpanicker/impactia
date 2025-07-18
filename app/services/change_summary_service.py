import ast
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .method_extractor import MethodExtractor, MethodInfo

@dataclass
class MethodChange:
    method_name: str
    change_type: str  # 'added', 'removed', 'modified'
    summary: str
    impact_level: str  # 'low', 'medium', 'high'
    details: List[str]

class ChangeSummaryService:
    """Service for generating detailed change summaries focused on functional changes"""
    
    def __init__(self):
        self.method_extractor = MethodExtractor()
        
    def analyze_file_changes(self, file_path: str, old_content: str = "", new_content: str = "") -> Dict[str, Any]:
        """Analyze changes in a file and generate comprehensive summary"""
        
        # Extract methods from both versions
        old_methods = self._get_methods_dict(old_content, file_path) if old_content else {}
        new_methods = self._get_methods_dict(new_content, file_path) if new_content else {}
        
        # Identify changes
        method_changes = self._identify_method_changes(old_methods, new_methods)
        
        # Generate file-level summary
        file_summary = self._generate_file_summary(file_path, method_changes, old_content, new_content)
        
        return {
            "file_path": file_path,
            "summary": file_summary,
            "method_changes": [self._method_change_to_dict(mc) for mc in method_changes],
            "total_methods_changed": len([mc for mc in method_changes if mc.change_type == 'modified']),
            "methods_added": len([mc for mc in method_changes if mc.change_type == 'added']),
            "methods_removed": len([mc for mc in method_changes if mc.change_type == 'removed']),
            "overall_impact": self._assess_overall_impact(method_changes)
        }
    
    def _get_methods_dict(self, content: str, file_path: str) -> Dict[str, MethodInfo]:
        """Extract methods and return as dictionary"""
        methods = self.method_extractor.extract_methods_from_content(content, file_path)
        return {method.name: method for method in methods}
    
    def _identify_method_changes(self, old_methods: Dict[str, MethodInfo], new_methods: Dict[str, MethodInfo]) -> List[MethodChange]:
        """Identify what changed between method versions"""
        changes = []
        
        # Find added methods
        for name, method_info in new_methods.items():
            if name not in old_methods:
                changes.append(MethodChange(
                    method_name=name,
                    change_type='added',
                    summary=f"New method '{name}' added",
                    impact_level='medium',
                    details=[f"Added {method_info.signature}"]
                ))
        
        # Find removed methods
        for name, method_info in old_methods.items():
            if name not in new_methods:
                changes.append(MethodChange(
                    method_name=name,
                    change_type='removed',
                    summary=f"Method '{name}' removed",
                    impact_level='high',
                    details=[f"Removed {method_info.signature}"]
                ))
        
        # Find modified methods
        for name in set(old_methods.keys()) & set(new_methods.keys()):
            old_method = old_methods[name]
            new_method = new_methods[name]
            
            if old_method.signature != new_method.signature:
                change_details = self._analyze_method_modification(old_method, new_method)
                if change_details:
                    changes.append(MethodChange(
                        method_name=name,
                        change_type='modified',
                        summary=change_details['summary'],
                        impact_level=change_details['impact_level'],
                        details=change_details['details']
                    ))
        
        return changes
    
    def _analyze_method_modification(self, old_method: MethodInfo, new_method: MethodInfo) -> Optional[Dict[str, Any]]:
        """Analyze what specifically changed in a method"""
        details = []
        impact_level = 'low'
        
        # Check signature changes
        if old_method.signature != new_method.signature:
            details.append(f"Signature changed from '{old_method.signature}' to '{new_method.signature}'")
            impact_level = 'high'  # Signature changes are usually breaking
        
        # Check async changes
        if old_method.is_async != new_method.is_async:
            if new_method.is_async:
                details.append("Method converted to async")
            else:
                details.append("Method converted from async to sync")
            impact_level = 'high'
        
        # Check static/class method changes
        if old_method.is_static != new_method.is_static:
            if new_method.is_static:
                details.append("Method converted to static")
            else:
                details.append("Method converted from static to instance")
            impact_level = 'medium'
        
        if old_method.is_class_method != new_method.is_class_method:
            if new_method.is_class_method:
                details.append("Method converted to class method")
            else:
                details.append("Method converted from class method")
            impact_level = 'medium'
        
        # Check docstring changes
        if old_method.docstring != new_method.docstring:
            if new_method.docstring and not old_method.docstring:
                details.append("Documentation added")
            elif old_method.docstring and not new_method.docstring:
                details.append("Documentation removed")
            else:
                details.append("Documentation updated")
            impact_level = max(impact_level, 'low')
        
        if not details:
            return None
        
        summary = f"Method '{new_method.name}' modified: {', '.join(details[:2])}"
        if len(details) > 2:
            summary += f" and {len(details) - 2} more changes"
        
        return {
            'summary': summary,
            'impact_level': impact_level,
            'details': details
        }
    
    def _generate_file_summary(self, file_path: str, method_changes: List[MethodChange], old_content: str, new_content: str) -> str:
        """Generate a high-level summary of file changes"""
        if not method_changes:
            return f"No method-level changes detected in {file_path}"
        
        added = len([mc for mc in method_changes if mc.change_type == 'added'])
        removed = len([mc for mc in method_changes if mc.change_type == 'removed'])
        modified = len([mc for mc in method_changes if mc.change_type == 'modified'])
        
        summary_parts = []
        
        if added:
            summary_parts.append(f"{added} method{'s' if added > 1 else ''} added")
        if removed:
            summary_parts.append(f"{removed} method{'s' if removed > 1 else ''} removed")
        if modified:
            summary_parts.append(f"{modified} method{'s' if modified > 1 else ''} modified")
        
        base_summary = f"File {file_path}: {', '.join(summary_parts)}"
        
        # Add context about the type of changes
        high_impact_changes = [mc for mc in method_changes if mc.impact_level == 'high']
        if high_impact_changes:
            base_summary += f". {len(high_impact_changes)} high-impact change{'s' if len(high_impact_changes) > 1 else ''} detected"
        
        return base_summary
    
    def _assess_overall_impact(self, method_changes: List[MethodChange]) -> str:
        """Assess the overall impact level of all changes"""
        if not method_changes:
            return 'none'
        
        impact_scores = {'low': 1, 'medium': 2, 'high': 3}
        max_impact = max(impact_scores.get(mc.impact_level, 1) for mc in method_changes)
        
        # Consider the number of changes
        if len(method_changes) > 5:
            max_impact = min(max_impact + 1, 3)
        
        impact_levels = {1: 'low', 2: 'medium', 3: 'high'}
        return impact_levels[max_impact]
    
    def _method_change_to_dict(self, method_change: MethodChange) -> Dict[str, Any]:
        """Convert MethodChange to dictionary"""
        return {
            "method_name": method_change.method_name,
            "change_type": method_change.change_type,
            "summary": method_change.summary,
            "impact_level": method_change.impact_level,
            "details": method_change.details
        }
    
    def generate_functional_diff_summary(self, file_path: str, old_content: str, new_content: str, method_name: str) -> str:
        """Generate a focused functional summary for a specific method"""
        try:
            # Extract the specific method from both versions
            old_methods = self._get_methods_dict(old_content, file_path)
            new_methods = self._get_methods_dict(new_content, file_path)
            
            old_method = old_methods.get(method_name)
            new_method = new_methods.get(method_name)
            
            if not old_method and not new_method:
                return f"Method '{method_name}' not found in either version"
            
            if not old_method:
                return f"Method '{method_name}' was added"
            
            if not new_method:
                return f"Method '{method_name}' was removed"
            
            # Get the actual method content
            old_method_content = self.method_extractor.get_method_content(old_content, old_method)
            new_method_content = self.method_extractor.get_method_content(new_content, new_method)
            
            # Analyze the functional changes
            return self._analyze_functional_changes(method_name, old_method_content, new_method_content)
            
        except Exception as e:
            return f"Error analyzing method '{method_name}': {str(e)}"
    
    def identify_method_containing_change(self, content: str, change_line_number: int, file_path: str = "") -> str:
        """Identify the method name that contains a specific line change"""
        try:
            methods = self.method_extractor.extract_methods_from_content(content, file_path)
            
            # Find the method that contains the change line
            for method in methods:
                method_content = self.method_extractor.get_method_content(content, method)
                method_lines = method_content.split('\n')
                method_start = method.start_line
                method_end = method_start + len(method_lines) - 1
                
                if method_start <= change_line_number <= method_end:
                    return method.name
            
            # If no method contains the change, it might be at module level
            return None
            
        except Exception as e:
            print(f"Error identifying method containing change: {e}")
            return None
    
    def identify_methods_from_diff(self, diff_content: str, file_path: str = "") -> List[str]:
        """Extract method names that contain changes from a diff"""
        try:
            # Parse the diff to find changed lines
            lines = diff_content.split('\n')
            changed_line_numbers = []
            current_line_number = 0
            
            for line in lines:
                if line.startswith('@@'):
                    # Parse hunk header to get line numbers
                    import re
                    match = re.search(r'@@\s*-\d+,?\d*\s*\+(\d+),?\d*\s*@@', line)
                    if match:
                        current_line_number = int(match.group(1))
                elif line.startswith('+') and not line.startswith('+++'):
                    # This is an added line
                    changed_line_numbers.append(current_line_number)
                    current_line_number += 1
                elif line.startswith('-') and not line.startswith('---'):
                    # This is a removed line, don't increment line number
                    continue
                elif not line.startswith('-'):
                    # Context line
                    current_line_number += 1
            
            # Extract the new content from diff
            from ..utils.diff_utils import extract_file_content_from_diff
            new_content = extract_file_content_from_diff(diff_content)
            
            # Find methods containing the changed lines
            method_names = set()
            for line_num in changed_line_numbers:
                method_name = self.identify_method_containing_change(new_content, line_num, file_path)
                if method_name:
                    method_names.add(method_name)
            
            return list(method_names)
            
        except Exception as e:
            print(f"Error identifying methods from diff: {e}")
            return []
    
    def _analyze_functional_changes(self, method_name: str, old_content: str, new_content: str) -> str:
        """Analyze functional changes between two versions of a method"""
        if old_content == new_content:
            return f"No changes detected in method '{method_name}'"
        
        changes = []
        
        # Analyze structural changes
        old_lines = [line.strip() for line in old_content.split('\n') if line.strip()]
        new_lines = [line.strip() for line in new_content.split('\n') if line.strip()]
        
        # Check for added/removed lines
        if len(new_lines) > len(old_lines):
            changes.append(f"Added {len(new_lines) - len(old_lines)} lines of code")
        elif len(new_lines) < len(old_lines):
            changes.append(f"Removed {len(old_lines) - len(new_lines)} lines of code")
        
        # Check for specific patterns
        old_patterns = self._extract_code_patterns(old_content)
        new_patterns = self._extract_code_patterns(new_content)
        
        # Check for new function calls
        new_calls = new_patterns['calls'] - old_patterns['calls']
        if new_calls:
            changes.append(f"Added calls to: {', '.join(list(new_calls)[:3])}")
        
        # Check for removed function calls
        removed_calls = old_patterns['calls'] - new_patterns['calls']
        if removed_calls:
            changes.append(f"Removed calls to: {', '.join(list(removed_calls)[:3])}")
        
        # Check for new imports/dependencies
        new_imports = new_patterns['imports'] - old_patterns['imports']
        if new_imports:
            changes.append(f"Added dependencies: {', '.join(list(new_imports)[:3])}")
        
        # Check for control flow changes
        if new_patterns['conditionals'] != old_patterns['conditionals']:
            changes.append("Modified conditional logic")
        
        if new_patterns['loops'] != old_patterns['loops']:
            changes.append("Modified loop structures")
        
        # Check for error handling changes
        if new_patterns['exceptions'] != old_patterns['exceptions']:
            changes.append("Modified error handling")
        
        if not changes:
            changes.append("Internal implementation modified")
        
        return f"Method '{method_name}': {'; '.join(changes[:4])}"
    
    def _extract_code_patterns(self, content: str) -> Dict[str, set]:
        """Extract various code patterns for comparison"""
        patterns = {
            'calls': set(),
            'imports': set(),
            'conditionals': set(),
            'loops': set(),
            'exceptions': set()
        }
        
        # Function calls
        call_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        patterns['calls'].update(re.findall(call_pattern, content))
        
        # Import statements
        import_patterns = [
            r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',
            r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import'
        ]
        for pattern in import_patterns:
            patterns['imports'].update(re.findall(pattern, content))
        
        # Control flow
        if re.search(r'\bif\b|\belif\b|\belse\b', content):
            patterns['conditionals'].add('conditional')
        
        if re.search(r'\bfor\b|\bwhile\b', content):
            patterns['loops'].add('loop')
        
        if re.search(r'\btry\b|\bexcept\b|\bfinally\b|\braise\b', content):
            patterns['exceptions'].add('exception_handling')
        
        # Remove common keywords that aren't actual function calls
        keywords_to_remove = {
            'if', 'for', 'while', 'def', 'class', 'return', 'import', 'from', 
            'try', 'except', 'with', 'as', 'and', 'or', 'not', 'in', 'is'
        }
        patterns['calls'] -= keywords_to_remove
        
        return patterns
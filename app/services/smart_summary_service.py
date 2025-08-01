from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
import json
import hashlib
from ..models.analysis import ChangeAnalysisResponseWithCode, RiskLevel

class SmartChangeSummary(BaseModel):
    """Condensed summary optimized for test generation"""
    change_type: str  # "feature", "bugfix", "refactor", "breaking"
    scope: str  # "method", "class", "module", "system"
    risk_level: str  # "low", "medium", "high", "critical"
    
    # Core changes - only essential info
    modified_methods: List[Dict[str, str]]  # {name, signature, change_type}
    new_methods: List[Dict[str, str]]
    deleted_methods: List[str]
    
    # Key dependencies - only critical ones
    critical_dependencies: List[str]  # method/class names that are heavily impacted
    
    # Business logic summary - very concise
    functional_summary: str  # 1-2 sentences max
    test_focus_areas: List[str]  # specific areas that need testing
    
    # Metadata for caching
    summary_hash: str
    token_count_estimate: int

class SmartSummaryService:
    def __init__(self):
        self.cache = {}  # In-memory cache, could be Redis in production
        
    def generate_smart_summary(self, analysis_response: ChangeAnalysisResponseWithCode) -> SmartChangeSummary:
        """Generate a token-efficient summary from full analysis"""
        
        # Create hash for caching
        content_hash = self._create_content_hash(analysis_response)
        
        if content_hash in self.cache:
            return self.cache[content_hash]
        
        # Extract and condense information
        summary = SmartChangeSummary(
            change_type=self._determine_change_type(analysis_response),
            scope=self._determine_scope(analysis_response),
            risk_level=self._determine_risk_level(analysis_response),
            modified_methods=self._extract_modified_methods(analysis_response),
            new_methods=self._extract_new_methods(analysis_response),
            deleted_methods=self._extract_deleted_methods(analysis_response),
            critical_dependencies=self._extract_critical_dependencies(analysis_response),
            functional_summary=self._create_functional_summary(analysis_response),
            test_focus_areas=self._identify_test_focus_areas(analysis_response),
            summary_hash=content_hash,
            token_count_estimate=self._estimate_token_count(analysis_response)
        )
        
        # Cache the result
        self.cache[content_hash] = summary
        return summary
    
    def _create_content_hash(self, analysis_response: ChangeAnalysisResponseWithCode) -> str:
        """Create hash for caching purposes"""
        content = f"{analysis_response.summary}{len(analysis_response.changed_components)}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _determine_change_type(self, analysis_response: ChangeAnalysisResponseWithCode) -> str:
        """Classify the type of change"""
        summary_lower = analysis_response.summary.lower()
        
        if any(word in summary_lower for word in ["new", "add", "implement", "feature"]):
            return "feature"
        elif any(word in summary_lower for word in ["fix", "bug", "error", "issue"]):
            return "bugfix"
        elif any(word in summary_lower for word in ["refactor", "restructure", "cleanup"]):
            return "refactor"
        elif any(word in summary_lower for word in ["breaking", "remove", "delete", "deprecate"]):
            return "breaking"
        else:
            return "modification"
    
    def _determine_scope(self, analysis_response: ChangeAnalysisResponseWithCode) -> str:
        """Determine the scope of changes"""
        component_count = len(analysis_response.changed_components)
        
        if component_count == 1:
            component = analysis_response.changed_components[0]
            if len(component.methods) == 1:
                return "method"
            else:
                return "class"
        elif component_count <= 3:
            return "module"
        else:
            return "system"
    
    def _determine_risk_level(self, analysis_response: ChangeAnalysisResponseWithCode) -> str:
        """Assess risk level based on dependencies and scope"""
        if analysis_response.risk_level:
            return analysis_response.risk_level.value
        
        # Fallback calculation
        total_dependencies = 0
        if analysis_response.dependency_chains:
            total_dependencies = len(analysis_response.dependency_chains)
        
        component_count = len(analysis_response.changed_components)
        
        if total_dependencies > 10 or component_count > 5:
            return "critical"
        elif total_dependencies > 5 or component_count > 2:
            return "high"
        elif total_dependencies > 2 or component_count > 1:
            return "medium"
        else:
            return "low"
    
    def _extract_modified_methods(self, analysis_response: ChangeAnalysisResponseWithCode) -> List[Dict[str, str]]:
        """Extract key info about modified methods"""
        methods = []
        for component in analysis_response.changed_components:
            for method in component.methods:
                if method.change_type in ["modified", "updated"]:
                    methods.append({
                        "name": method.name,
                        "signature": method.name,  # Using name as signature for now
                        "change_type": method.change_type
                    })
        return methods[:10]  # Limit to top 10 most important
    
    def _extract_new_methods(self, analysis_response: ChangeAnalysisResponseWithCode) -> List[Dict[str, str]]:
        """Extract new methods"""
        methods = []
        for component in analysis_response.changed_components:
            for method in component.methods:
                if method.change_type == "added":
                    methods.append({
                        "name": method.name,
                        "signature": method.name,
                        "change_type": "added"
                    })
        return methods[:5]  # Limit new methods
    
    def _extract_deleted_methods(self, analysis_response: ChangeAnalysisResponseWithCode) -> List[str]:
        """Extract deleted method names"""
        methods = []
        for component in analysis_response.changed_components:
            for method in component.methods:
                if method.change_type == "removed":
                    methods.append(method.name)
        return methods[:5]  # Limit deleted methods
    
    def _extract_critical_dependencies(self, analysis_response: ChangeAnalysisResponseWithCode) -> List[str]:
        """Extract only the most critical dependencies"""
        dependencies = set()
        
        if analysis_response.dependency_chains:
            for chain in analysis_response.dependency_chains:
                # Add the main file as a dependency
                dependencies.add(chain.file_path)
                
                # Add impacted files
                for impacted_file in chain.impacted_files:
                    dependencies.add(impacted_file.file_path)
        
        return list(dependencies)[:8]  # Limit to most critical
    
    def _create_functional_summary(self, analysis_response: ChangeAnalysisResponseWithCode) -> str:
        """Create a very concise functional summary"""
        summary = analysis_response.summary
        
        # Truncate to essential information
        sentences = summary.split('.')
        if len(sentences) > 2:
            return '. '.join(sentences[:2]) + '.'
        
        return summary[:200] + "..." if len(summary) > 200 else summary
    
    def _identify_test_focus_areas(self, analysis_response: ChangeAnalysisResponseWithCode) -> List[str]:
        """Identify specific areas that need testing focus"""
        focus_areas = []
        
        # Check for common patterns that need specific testing
        summary_lower = analysis_response.summary.lower()
        
        if "validation" in summary_lower or "input" in summary_lower:
            focus_areas.append("input_validation")
        if "error" in summary_lower or "exception" in summary_lower:
            focus_areas.append("error_handling")
        if "database" in summary_lower or "data" in summary_lower:
            focus_areas.append("data_persistence")
        if "api" in summary_lower or "endpoint" in summary_lower:
            focus_areas.append("api_integration")
        if "security" in summary_lower or "auth" in summary_lower:
            focus_areas.append("security")
        if "performance" in summary_lower:
            focus_areas.append("performance")
        
        # Add based on change scope
        if len(analysis_response.changed_components) > 3:
            focus_areas.append("integration_testing")
        
        # Add based on risk level
        if analysis_response.risk_level and analysis_response.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            focus_areas.append("regression_testing")
        
        return focus_areas[:5]  # Limit focus areas
    
    def _estimate_token_count(self, analysis_response: ChangeAnalysisResponseWithCode) -> int:
        """Rough estimate of token count for the summary"""
        # Rough calculation: ~4 characters per token
        total_chars = len(analysis_response.summary)
        for component in analysis_response.changed_components:
            total_chars += sum(len(method.name) + len(method.summary) for method in component.methods)
        
        return total_chars // 4
    
    def get_summary_for_test_generation(self, analysis_response: ChangeAnalysisResponseWithCode) -> str:
        """Get a formatted summary optimized for test generation prompts"""
        summary = self.generate_smart_summary(analysis_response)
        
        modified_methods_text = ""
        if summary.modified_methods:
            modified_methods_text = "\n".join([f"- {m['name']}: {m['change_type']}" for m in summary.modified_methods[:3]])
        
        new_methods_text = ""
        if summary.new_methods:
            new_methods_text = "\n".join([f"- {m['name']}" for m in summary.new_methods[:3]])
        
        deleted_methods_text = ""
        if summary.deleted_methods:
            deleted_methods_text = "\n".join([f"- {method}" for method in summary.deleted_methods[:3]])
        
        return f"""
CHANGE SUMMARY:
Type: {summary.change_type} | Scope: {summary.scope} | Risk: {summary.risk_level}

FUNCTIONAL CHANGE: {summary.functional_summary}

MODIFIED METHODS: {len(summary.modified_methods)} methods
{modified_methods_text}

NEW METHODS: {len(summary.new_methods)} methods
{new_methods_text}

DELETED METHODS: {len(summary.deleted_methods)} methods
{deleted_methods_text}

CRITICAL DEPENDENCIES: {', '.join(summary.critical_dependencies[:5])}

TEST FOCUS: {', '.join(summary.test_focus_areas)}
""".strip()
    
    def get_smart_impact_summary(self, analysis_response: ChangeAnalysisResponseWithCode) -> str:
        """Generate a smart impact summary with file-by-file changes"""
        # First get the overall change type and summary
        change_type = self._determine_change_type(analysis_response)
        functional_summary = self._create_functional_summary(analysis_response)
        risk_level = self._determine_risk_level(analysis_response)
        test_focus_areas = self._identify_test_focus_areas(analysis_response)
        
        # Start with the overall summary
        result = f"{functional_summary}\n\nOverall change type: {change_type}, Risk level: {risk_level}\n"
        result += f"Test focus areas: {', '.join(test_focus_areas)}\n\n"
        
        # Add file-by-file changes
        for component in analysis_response.changed_components:
            result += f"In file {component.file_path}, the changes are:\n"
            
            # Add methods changed in this file
            for method in component.methods:
                result += f"  - {method.name} ({method.change_type}): {method.summary}\n"
                result += f"    Impact: {method.impact_description}\n"
            
            # Add impact information for this file
            result += f"  File impact: {component.impact_description}\n"
            
            result += "\n"
        
        # Add dependency information if available
        if analysis_response.dependency_chains:
            result += "Dependencies affected:\n"
            
            for chain in analysis_response.dependency_chains[:3]:  # Limit to top 3 dependencies
                result += f"  - Changes in {chain.file_path} impact:\n"
                
                for impacted_file in chain.impacted_files[:3]:  # Limit to top 3 impacted files
                    result += f"    * {impacted_file.file_path}\n"
            
            result += "\n"
        
        return result.strip()
    
    def clear_cache(self):
        """Clear the summary cache"""
        self.cache.clear()

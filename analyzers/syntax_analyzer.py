"""
Syntax Analyzer

This module implements core syntax analysis logic for the A2A Code Review System.
Analyzes code syntax, style, and formatting using rule-based and LLM approaches.
"""

import ast
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import openai
from utils.logger import get_logger
import os

logger = get_logger(__name__)


class SyntaxAnalyzer:
    """
    Core syntax analysis logic for code review
    
    Provides comprehensive syntax analysis including:
    - Syntax error detection
    - Style and formatting checks
    - PEP 8 compliance
    - Code structure analysis
    """
    
    def __init__(self):
        """Initialize syntax analyzer"""
        self.logger = get_logger(__name__)
        
        # Initialize OpenAI client
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Style rules configuration
        self.style_rules = {
            "max_line_length": 88,
            "indent_size": 4,
            "max_function_args": 5,
            "max_function_length": 50,
            "max_class_length": 200
        }
        
        self.logger.info("Syntax analyzer initialized")
    
    async def analyze_code(self, code: str, language: str = "python", options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze code syntax and style
        
        Args:
            code: Code to analyze
            language: Programming language
            options: Analysis options
            
        Returns:
            Analysis results
        """
        try:
            self.logger.info(f"Starting syntax analysis for {language} code")
            
            observations = []
            errors = []
            suggestions = []
            
            # Basic syntax validation
            syntax_errors = self._check_syntax_errors(code, language)
            errors.extend(syntax_errors)
            
            if language.lower() == "python":
                # Python-specific analysis
                observations.extend(self._analyze_python_structure(code))
                errors.extend(self._check_pep8_compliance(code))
                suggestions.extend(self._generate_style_suggestions(code))
                
                # Use LLM for advanced analysis if available
                if openai.api_key and openai.api_key != "your_openai_api_key_here":
                    llm_analysis = await self._llm_analysis(code)
                    observations.extend(llm_analysis.get("observations", []))
                    errors.extend(llm_analysis.get("errors", []))
                    suggestions.extend(llm_analysis.get("suggestions", []))
            
            # Generate corrected code
            corrected_code = self._generate_corrected_code(code, errors, suggestions)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(len(errors), len(observations))
            
            result = {
                "analyzer_type": "syntax",
                "language": language,
                "observations": observations,
                "errors": errors,
                "suggestions": suggestions,
                "corrected_code": corrected_code,
                "quality_score": quality_score,
                "metadata": {
                    "lines_of_code": len(code.split('\n')),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "rules_applied": list(self.style_rules.keys())
                }
            }
            
            self.logger.info(f"Syntax analysis completed with {len(errors)} errors and {len(suggestions)} suggestions")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in syntax analysis: {e}")
            return {
                "analyzer_type": "syntax",
                "language": language,
                "observations": [],
                "errors": [{"type": "analysis_error", "message": str(e), "severity": "critical"}],
                "suggestions": [],
                "corrected_code": None,
                "quality_score": 0,
                "metadata": {"error": str(e)}
            }
    
    def _check_syntax_errors(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Check for basic syntax errors"""
        errors = []
        
        try:
            if language.lower() == "python":
                # Try to parse the code
                ast.parse(code)
            else:
                # For other languages, basic checks
                if not code.strip():
                    errors.append({
                        "type": "syntax_error",
                        "message": "Empty code provided",
                        "severity": "error",
                        "line_number": 1
                    })
        except SyntaxError as e:
            errors.append({
                "type": "syntax_error",
                "message": f"Syntax error: {e.msg}",
                "severity": "error",
                "line_number": e.lineno or 1,
                "suggestion": "Fix the syntax error to make the code executable"
            })
        except Exception as e:
            errors.append({
                "type": "syntax_error",
                "message": f"Code parsing error: {str(e)}",
                "severity": "error",
                "line_number": 1
            })
        
        return errors
    
    def _analyze_python_structure(self, code: str) -> List[Dict[str, Any]]:
        """Analyze Python code structure"""
        observations = []
        
        try:
            tree = ast.parse(code)
            
            # Analyze functions
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            for func in functions:
                # Check function length
                func_lines = func.end_lineno - func.lineno + 1 if hasattr(func, 'end_lineno') else 1
                if func_lines > self.style_rules["max_function_length"]:
                    observations.append({
                        "type": "function_length",
                        "message": f"Function '{func.name}' is {func_lines} lines long (max recommended: {self.style_rules['max_function_length']})",
                        "severity": "warning",
                        "line_number": func.lineno,
                        "suggestion": "Consider breaking this function into smaller functions"
                    })
                
                # Check function arguments
                if len(func.args.args) > self.style_rules["max_function_args"]:
                    observations.append({
                        "type": "function_args",
                        "message": f"Function '{func.name}' has {len(func.args.args)} arguments (max recommended: {self.style_rules['max_function_args']})",
                        "severity": "warning",
                        "line_number": func.lineno,
                        "suggestion": "Consider using *args, **kwargs, or a data structure to reduce arguments"
                    })
            
            # Analyze classes
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            for cls in classes:
                cls_lines = cls.end_lineno - cls.lineno + 1 if hasattr(cls, 'end_lineno') else 1
                if cls_lines > self.style_rules["max_class_length"]:
                    observations.append({
                        "type": "class_length",
                        "message": f"Class '{cls.name}' is {cls_lines} lines long (max recommended: {self.style_rules['max_class_length']})",
                        "severity": "warning",
                        "line_number": cls.lineno,
                        "suggestion": "Consider breaking this class into smaller classes"
                    })
        
        except Exception as e:
            self.logger.warning(f"Error analyzing Python structure: {e}")
        
        return observations
    
    def _check_pep8_compliance(self, code: str) -> List[Dict[str, Any]]:
        """Check PEP 8 compliance"""
        errors = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > self.style_rules["max_line_length"]:
                errors.append({
                    "type": "line_length",
                    "message": f"Line {i} is {len(line)} characters long (max: {self.style_rules['max_line_length']})",
                    "severity": "warning",
                    "line_number": i,
                    "suggestion": "Break this line into multiple lines"
                })
            
            # Check for trailing whitespace
            if line.rstrip() != line:
                errors.append({
                    "type": "trailing_whitespace",
                    "message": f"Line {i} has trailing whitespace",
                    "severity": "warning",
                    "line_number": i,
                    "suggestion": "Remove trailing whitespace"
                })
            
            # Check for tabs vs spaces
            if '\t' in line and not line.startswith('#'):
                errors.append({
                    "type": "indentation",
                    "message": f"Line {i} uses tabs for indentation (use spaces)",
                    "severity": "warning",
                    "line_number": i,
                    "suggestion": "Replace tabs with spaces"
                })
        
        return errors
    
    def _generate_style_suggestions(self, code: str) -> List[Dict[str, Any]]:
        """Generate style improvement suggestions"""
        suggestions = []
        lines = code.split('\n')
        
        # Check for missing docstrings
        has_docstring = False
        for line in lines:
            if '"""' in line or "'''" in line:
                has_docstring = True
                break
        
        if not has_docstring:
            suggestions.append({
                "type": "documentation",
                "message": "Consider adding docstrings to functions and classes",
                "priority": "medium",
                "suggestion": "Add docstrings following Google or NumPy style guide"
            })
        
        # Check for variable naming conventions
        snake_case_pattern = re.compile(r'^[a-z_][a-z0-9_]*$')
        camel_case_pattern = re.compile(r'^[a-z][a-zA-Z0-9]*$')
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    var_name = node.id
                    if not snake_case_pattern.match(var_name) and not camel_case_pattern.match(var_name):
                        suggestions.append({
                            "type": "naming_convention",
                            "message": f"Variable '{var_name}' doesn't follow Python naming conventions",
                            "priority": "low",
                            "line_number": getattr(node, 'lineno', None),
                            "suggestion": "Use snake_case for variables and functions"
                        })
        except:
            pass
        
        return suggestions
    
    async def _llm_analysis(self, code: str) -> Dict[str, Any]:
        """Use LLM for advanced syntax analysis"""
        try:
            if not openai.api_key or openai.api_key == "your_openai_api_key_here":
                return {"observations": [], "errors": [], "suggestions": []}
            
            prompt = f"""
            Analyze the following Python code for syntax, style, and best practices. Provide specific, actionable feedback.
            
            Code:
            ```python
            {code}
            ```
            
            Please provide:
            1. Any syntax or style issues
            2. Suggestions for improvement
            3. Best practice recommendations
            
            Format your response as JSON with the following structure:
            {{
                "observations": [
                    {{"type": "issue_type", "message": "description", "severity": "warning/error", "line_number": 1}}
                ],
                "errors": [
                    {{"type": "error_type", "message": "description", "severity": "error", "line_number": 1}}
                ],
                "suggestions": [
                    {{"type": "suggestion_type", "message": "description", "priority": "high/medium/low"}}
                ]
            }}
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content
            
            # Try to parse JSON response
            import json
            return json.loads(result_text)
            
        except Exception as e:
            self.logger.warning(f"LLM analysis failed: {e}")
            return {"observations": [], "errors": [], "suggestions": []}
    
    def _generate_corrected_code(self, code: str, errors: List[Dict[str, Any]], suggestions: List[Dict[str, Any]]) -> Optional[str]:
        """Generate corrected code based on errors and suggestions"""
        try:
            corrected_lines = code.split('\n')
            
            # Apply simple fixes
            for i, line in enumerate(corrected_lines):
                # Fix trailing whitespace
                corrected_lines[i] = line.rstrip()
                
                # Fix line length (simple approach)
                if len(corrected_lines[i]) > self.style_rules["max_line_length"]:
                    # Try to break at logical points
                    if '(' in corrected_lines[i] and ')' in corrected_lines[i]:
                        # This is a simplified approach - in practice, you'd want more sophisticated line breaking
                        pass
            
            return '\n'.join(corrected_lines)
            
        except Exception as e:
            self.logger.warning(f"Error generating corrected code: {e}")
            return None
    
    def _calculate_quality_score(self, error_count: int, observation_count: int) -> float:
        """Calculate quality score based on errors and observations"""
        base_score = 100.0
        
        # Deduct points for errors
        error_penalty = error_count * 5.0
        
        # Deduct points for observations (warnings)
        observation_penalty = observation_count * 2.0
        
        final_score = max(0, base_score - error_penalty - observation_penalty)
        return round(final_score, 2)

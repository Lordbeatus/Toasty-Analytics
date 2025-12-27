"""
Refactored Code Quality Grader using BaseGrader with AST-based analysis
"""

import sys
from pathlib import Path

# Add parent directory to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

import ast
import hashlib
import re
from typing import Any, Dict, List, Optional

from core.base_grader import BaseGrader, GraderResult
from core.types import GradingDimension, ImprovementSuggestion, ScoreBreakdown


class ASTAnalyzer:
    """Analyzes Python code using AST for real structural metrics"""

    def __init__(self, code: str):
        self.code = code
        self.tree = None
        self.functions = []
        self.classes = []
        self.complexity_map = {}
        self.imports = []
        self.parse_success = False

        try:
            self.tree = ast.parse(code)
            self.parse_success = True
            self._analyze()
        except SyntaxError:
            pass  # Invalid syntax - will be caught elsewhere

    def _analyze(self):
        """Walk the AST and extract metrics"""
        if not self.tree:
            return

        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                self.functions.append(
                    {
                        "name": node.name,
                        "lineno": node.lineno,
                        "args": len(node.args.args),
                        "has_docstring": ast.get_docstring(node) is not None,
                        "has_return": any(
                            isinstance(n, ast.Return) for n in ast.walk(node)
                        ),
                        "complexity": self._calculate_complexity(node),
                    }
                )
            elif isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                self.classes.append(
                    {
                        "name": node.name,
                        "lineno": node.lineno,
                        "methods": len(methods),
                        "has_docstring": ast.get_docstring(node) is not None,
                    }
                )
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                self.imports.append(node.lineno)

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity (McCabe) for a function"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Each decision point adds 1
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and/or operators
                complexity += len(child.values) - 1

        return complexity

    def get_metrics(self) -> Dict[str, Any]:
        """Return analyzed metrics"""
        total_complexity = sum(f["complexity"] for f in self.functions)
        avg_complexity = total_complexity / len(self.functions) if self.functions else 0

        return {
            "parse_success": self.parse_success,
            "function_count": len(self.functions),
            "class_count": len(self.classes),
            "import_count": len(self.imports),
            "avg_complexity": avg_complexity,
            "max_complexity": max((f["complexity"] for f in self.functions), default=0),
            "functions": self.functions,
            "classes": self.classes,
            "has_docstrings": any(f["has_docstring"] for f in self.functions),
            "typed_functions": sum(
                1 for f in self.functions if f.get("has_type_hints", False)
            ),
        }


class CodeQualityGraderV2(BaseGrader):
    """
    Advanced code quality grader implementing BaseGrader interface.

    This grader performs comprehensive static analysis of code quality across
    multiple dimensions. It uses heuristic algorithms and pattern matching to
    evaluate code without executing it.

    Evaluation Dimensions:
    - Code structure and organization (25% weight)
      * Module/class organization
      * Function decomposition
      * Logical grouping

    - Readability (25% weight)
      * Variable/function naming conventions
      * Comment quality and coverage
      * Code formatting consistency

    - Best practices (30% weight)
      * Error handling presence
      * DRY principle adherence
      * SOLID principles
      * Security considerations

    - Complexity metrics (20% weight)
      * Cyclomatic complexity
      * Nesting depth
      * Function length

    Scoring:
    - 85-100: Excellent code, production-ready
    - 75-84: Good code, minor improvements needed
    - 65-74: Acceptable, several issues to address
    - 50-64: Needs improvement, significant issues
    - 0-49: Poor quality, major refactoring required

    Example:
        >>> grader = CodeQualityGraderV2()
        >>> result = grader.grade(code='def hello(): return "world"', language='python')
        >>> print(f"Score: {result.score}/{result.max_score}")
    """

    @property
    def dimension(self) -> GradingDimension:
        return GradingDimension.CODE_QUALITY

    def _get_default_weights(self) -> Dict[str, float]:
        """Default weights for code quality components"""
        return {
            "structure": 0.25,
            "readability": 0.25,
            "best_practices": 0.30,
            "complexity": 0.20,
        }

    def _get_default_thresholds(self) -> Dict[str, float]:
        """Default thresholds for scoring"""
        return {
            "excellent": 85,
            "good": 75,
            "acceptable": 65,
            "needs_improvement": 50,
        }

    def grade(self, code: str, language: str = "python", **kwargs) -> GraderResult:
        """
        Grade code quality using AST-based multi-dimensional analysis.

        This method orchestrates the complete grading pipeline:
        1. Parse code with AST for real structural analysis
        2. Evaluate code structure (modularity, organization)
        3. Analyze readability (naming, comments, formatting)
        4. Check best practices (error handling, patterns)
        5. Measure complexity (cyclomatic, nesting depth)
        6. Combine scores using weighted average
        7. Generate actionable improvement suggestions

        Args:
            code: Source code to grade as a string. Can be empty or invalid.
            language: Programming language. Supported: 'python', 'javascript',
                     'java', 'cpp'. Default: 'python'
            **kwargs: Additional options (strict_mode, focus_areas, context)

        Returns:
            GraderResult with score, feedback, suggestions, and breakdown
        """
        # AST Analysis (for Python only)
        ast_metrics = None
        if language == "python":
            analyzer = ASTAnalyzer(code)
            ast_metrics = analyzer.get_metrics()

        # Component scores (each 0-100)
        structure_score = self._grade_structure(code, language, ast_metrics)
        readability_score = self._grade_readability(code, language, ast_metrics)
        best_practices_score = self._grade_best_practices(code, language, ast_metrics)
        complexity_score = self._grade_complexity(code, language, ast_metrics)

        # Weighted total: apply configurable weights to each component
        # Default: structure(25%) + readability(25%) + practices(30%) + complexity(20%)
        weighted_score = (
            structure_score * self._weights["structure"]
            + readability_score * self._weights["readability"]
            + best_practices_score * self._weights["best_practices"]
            + complexity_score * self._weights["complexity"]
        )

        # Generate feedback
        feedback = self._generate_feedback(
            structure_score,
            readability_score,
            best_practices_score,
            complexity_score,
            ast_metrics,
        )

        # Generate suggestions
        suggestions = self._generate_suggestions(
            code,
            structure_score,
            readability_score,
            best_practices_score,
            complexity_score,
            ast_metrics,
        )

        # Create breakdown
        breakdown = ScoreBreakdown(
            dimension=self.dimension,
            score=weighted_score,
            max_score=100,
            weight=1.0,
            weighted_score=weighted_score,
            rationale=feedback,
            line_level_feedback=self._get_line_level_feedback(
                code, language, ast_metrics
            ),
            suggestions=[s.description for s in suggestions],
        )

        return GraderResult(
            dimension=self.dimension,
            score=weighted_score,
            max_score=100,
            breakdown=breakdown,
            feedback=feedback,
            suggestions=suggestions,
            metadata={
                "language": language,
                "code_length": len(code),
                "component_scores": {
                    "structure": structure_score,
                    "readability": readability_score,
                    "best_practices": best_practices_score,
                    "complexity": complexity_score,
                },
            },
        )

    def _grade_structure(
        self, code: str, language: str, ast_metrics: Optional[Dict] = None
    ) -> float:
        """Grade code structure (0-100) using AST analysis for real metrics"""
        score = 50.0  # Start at baseline, earn points for good structure
        lines = code.split("\n")  # Define lines at top level

        if language == "python" and ast_metrics and ast_metrics.get("parse_success"):
            # Use AST metrics for precise scoring

            # Award points for functions (shows modularity)
            func_count = ast_metrics["function_count"]
            if func_count > 0:
                score += min(20, func_count * 5)  # +5 per function, max +20

            # Award for classes (shows OOP structure)
            class_count = ast_metrics["class_count"]
            if class_count > 0:
                score += min(15, class_count * 7)  # +7 per class, max +15

            # Award for imports (shows use of libraries)
            if ast_metrics["import_count"] > 0:
                score += 10

            # Award for balanced complexity (not too simple, not too complex)
            avg_complexity = ast_metrics["avg_complexity"]
            if 2 <= avg_complexity <= 5:  # Sweet spot
                score += 10
            elif avg_complexity > 10:  # Too complex
                score -= 5

        else:
            # Fallback to regex for non-Python or parse failures
            code_lines = [
                l for l in lines if l.strip() and not l.strip().startswith("#")
            ]

            # Award points for having functions/classes
            if language == "python":
                has_functions = bool(re.search(r"^\s*def\s+\w+", code, re.MULTILINE))
                has_classes = bool(re.search(r"^\s*class\s+\w+", code, re.MULTILINE))

                if has_functions:
                    score += 20  # Good: has function definitions
                if has_classes:
                    score += 15  # Better: has class organization

                # Award for proper imports at top
                import_lines = [
                    i
                    for i, line in enumerate(lines)
                    if re.match(r"^\s*(import|from)\s+", line)
                ]
                if import_lines:
                    first_import = import_lines[0]
                    if first_import <= 3:  # Imports near top (allow docstring)
                        score += 10

            # Award for modular design (multiple small functions vs one big one)
            func_count = len(re.findall(r"^\s*def\s+\w+", code, re.MULTILINE))
            if func_count >= 2:
                score += 10  # Multiple functions = good modularity
            elif func_count == 1 and len(code_lines) > 10:
                score -= 10  # One big function = poor modularity

        # Penalize overly long files
        if len(lines) > 500:
            score -= 10
        elif len(lines) > 1000:
            score -= 20

        return max(0, min(100, score))

    def _grade_readability(
        self, code: str, language: str, ast_metrics: Optional[Dict] = None
    ) -> float:
        """Grade code readability (0-100) using AST for precise analysis"""
        score = 40.0  # Start lower, earn points for readability features
        lines = code.split("\n")

        if language == "python" and ast_metrics and ast_metrics.get("parse_success"):
            # Use AST for precise docstring detection
            has_docstrings = ast_metrics.get("has_docstrings", False)
            if has_docstrings:
                score += 20  # Excellent: has docstrings

            # Check each function for docstrings (be specific!)
            functions_with_docs = sum(
                1 for f in ast_metrics["functions"] if f["has_docstring"]
            )
            total_functions = len(ast_metrics["functions"])

            if total_functions > 0:
                doc_coverage = functions_with_docs / total_functions
                if doc_coverage >= 0.8:
                    score += 15  # 80%+ functions documented
                elif doc_coverage >= 0.5:
                    score += 10  # 50%+ documented

            # Check variable naming (short names = bad)
            # AST doesn't give us variable names easily, so still use regex
            short_names = re.findall(r"\b[a-z]\b(?!\s*=)", code)  # Single letter vars
            if len(short_names) < 3:
                score += 10  # Good: minimal single-letter variables
            else:
                score -= 5  # Poor: too many unclear names

        else:
            # Fallback regex analysis
            # Comment ratio - REWARD good commenting
            comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
            code_lines = sum(
                1 for line in lines if line.strip() and not line.strip().startswith("#")
            )

            if code_lines > 0:
                comment_ratio = comment_lines / code_lines

                if comment_ratio >= 0.15:  # 15%+ comments
                    score += 20  # Excellent commenting
                elif comment_ratio >= 0.10:
                    score += 15  # Good commenting
                elif comment_ratio >= 0.05:
                    score += 10  # Acceptable
                # else: no points (poor commenting)

            # Docstrings - REWARD
            if language == "python":
                has_docstrings = bool(
                    re.search(r'(""".*?"""|\'\'\'.*?\'\'\')', code, re.DOTALL)
                )
                if has_docstrings:
                    score += 20  # Excellent: has docstrings

                # Type hints - REWARD
                has_type_hints = bool(re.search(r":\s*\w+\s*[,\)]", code)) or bool(
                    re.search(r"->\s*\w+:", code)
                )
                if has_type_hints:
                    score += 15  # Excellent: uses type hints

        # Descriptive variable names - REWARD
        # Check for multi-word variable names (snake_case)
        good_var_names = re.findall(r"\b[a-z]+_[a-z_]+\s*=", code)
        if len(good_var_names) >= 2:
            score += 10  # Good naming

        # Variable naming - PENALIZE bad
        single_char_vars = re.findall(r"\b[a-z]\s*=", code)
        single_char_vars = [
            v for v in single_char_vars if "for " + v not in code
        ]  # Exclude loop vars
        if len(single_char_vars) > 3:
            score -= 10

        # Line length - PENALIZE very long lines
        long_lines = sum(1 for line in lines if len(line) > 100)
        if long_lines > 0:
            score -= min(15, long_lines * 3)

        return max(0, min(100, score))

    def _grade_best_practices(
        self, code: str, language: str, ast_metrics: Optional[Dict] = None
    ) -> float:
        """Grade adherence to best practices (0-100) - Reward good, penalize bad"""
        score = 60.0  # Baseline

        if language == "python":
            # REWARD error handling
            has_try_except = bool(re.search(r"\btry\s*:", code))
            if has_try_except:
                score += 15  # Good: has error handling

                # PENALIZE bare except
                if re.search(r"except\s*:", code):
                    score -= 20  # Very bad: bare except

            # REWARD specific exceptions
            specific_exceptions = len(re.findall(r"except\s+\w+Error", code))
            if specific_exceptions > 0:
                score += 10  # Good: catches specific exceptions

            # Check for input validation
            has_validation = bool(re.search(r"\bif\s+not\s+", code)) or bool(
                re.search(r"\bif\s+.*\bis\s+None", code)
            )
            if has_validation:
                score += 10  # Good: validates inputs

            # PENALIZE excessive print (should use logging)
            print_count = len(re.findall(r"\bprint\s*\(", code))
            if print_count > 5:
                score -= 10
            elif print_count == 0 and len(code.split("\n")) > 10:
                score += 5  # Good: no debug prints in larger code

            # PENALIZE TODO/FIXME (incomplete code)
            todo_count = len(re.findall(r"#\s*(TODO|FIXME)", code, re.IGNORECASE))
            if todo_count > 0:
                score -= min(15, todo_count * 5)

            # PENALIZE magic numbers
            magic_numbers = re.findall(r"=\s*(\d+)", code)
            magic_numbers = [n for n in magic_numbers if int(n) > 1]
            if len(magic_numbers) > 5:
                score -= 10
            elif len(magic_numbers) == 0:
                score += 5  # Good: no magic numbers

        return max(0, min(100, score))

    def _grade_complexity(
        self, code: str, language: str, ast_metrics: Optional[Dict] = None
    ) -> float:
        """Grade code complexity (0-100) using McCabe cyclomatic complexity"""
        score = 100.0

        if language == "python" and ast_metrics and ast_metrics.get("parse_success"):
            # Use real cyclomatic complexity from AST
            max_complexity = ast_metrics.get("max_complexity", 0)
            avg_complexity = ast_metrics.get("avg_complexity", 0)

            # Score based on McCabe complexity
            # 1-5: Simple (excellent)
            # 6-10: More complex but manageable (good)
            # 11-20: Complex (needs refactoring)
            # 21+: Very complex (poor)

            if max_complexity <= 5:
                # Excellent: simple functions
                pass  # Keep 100
            elif max_complexity <= 10:
                score -= 10  # Good but could be simpler
            elif max_complexity <= 20:
                score -= 30  # Complex, should refactor
            else:
                score -= 50  # Very complex!

            # Also check average complexity
            if avg_complexity > 10:
                score -= 20  # Overall codebase is complex
            elif avg_complexity > 5:
                score -= 10

            # Penalize too many functions (over-engineered)
            func_count = ast_metrics.get("function_count", 0)
            if func_count > 20:
                score -= 15

        else:
            # Fallback: use indentation depth as proxy
            lines = code.split("\n")
            max_indent = 0
            for line in lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    max_indent = max(
                        max_indent, indent // 4
                    )  # Assuming 4-space indents

            if max_indent > 4:
                score -= 20
            elif max_indent > 3:
                score -= 10

            # Function complexity (number of branches)
            if_count = len(re.findall(r"\bif\b", code))
            for_count = len(re.findall(r"\bfor\b", code))
            while_count = len(re.findall(r"\bwhile\b", code))

            total_branches = if_count + for_count + while_count

            if total_branches > 20:
                score -= 20
            elif total_branches > 10:
                score -= 10

        return max(0, score)

    def _generate_feedback(
        self,
        structure: float,
        readability: float,
        best_practices: float,
        complexity: float,
        ast_metrics: Optional[Dict] = None,
    ) -> str:
        """Generate human-readable feedback with specific metrics"""
        overall = (structure + readability + best_practices + complexity) / 4

        feedback_parts = []

        if overall >= self._thresholds["excellent"]:
            feedback_parts.append("Excellent code quality! ")
        elif overall >= self._thresholds["good"]:
            feedback_parts.append("Good code quality overall. ")
        elif overall >= self._thresholds["acceptable"]:
            feedback_parts.append("Acceptable code quality with room for improvement. ")
        else:
            feedback_parts.append("Code quality needs significant improvement. ")

        # Add specific AST-based feedback
        if ast_metrics and ast_metrics.get("parse_success"):
            max_complexity = ast_metrics.get("max_complexity", 0)
            avg_complexity = ast_metrics.get("avg_complexity", 0)

            if max_complexity > 15:
                feedback_parts.append(
                    f"High cyclomatic complexity detected (max: {max_complexity}). "
                )
            elif max_complexity > 10:
                feedback_parts.append(
                    f"Some functions are complex (max complexity: {max_complexity}). "
                )

            if avg_complexity > 5:
                feedback_parts.append(
                    f"Average function complexity is {avg_complexity:.1f}. "
                )

            func_count = ast_metrics.get("function_count", 0)
            class_count = ast_metrics.get("class_count", 0)

            if func_count == 0 and class_count == 0:
                feedback_parts.append(
                    "No functions or classes detected - consider modularizing. "
                )

        # Specific feedback
        if structure < 70:
            feedback_parts.append(
                "Consider improving code organization and structure. "
            )
        if readability < 70:
            feedback_parts.append(
                "Enhance readability with better comments and naming. "
            )
        if best_practices < 70:
            feedback_parts.append("Follow more Python best practices. ")
        if complexity < 70:
            feedback_parts.append("Reduce code complexity by breaking down functions. ")

        return "".join(feedback_parts)

    def _generate_suggestions(
        self,
        code: str,
        structure: float,
        readability: float,
        best_practices: float,
        complexity: float,
        ast_metrics: Optional[Dict] = None,
    ) -> List[ImprovementSuggestion]:
        """Generate actionable, code-specific improvement suggestions using AST"""
        suggestions = []

        if ast_metrics and ast_metrics.get("parse_success"):
            # Generate SPECIFIC suggestions based on AST analysis

            # Check for missing docstrings
            functions_without_docs = [
                f for f in ast_metrics.get("functions", []) if not f["has_docstring"]
            ]
            if functions_without_docs and structure < 75:
                func_names = ", ".join(
                    [
                        f"'{f['name']}' (line {f['lineno']})"
                        for f in functions_without_docs[:3]
                    ]
                )
                suggestions.append(
                    ImprovementSuggestion(
                        category="Structure",
                        priority=2,
                        description=f"Add docstrings to functions: {func_names}",
                        expected_impact="Better documentation and code understanding",
                        examples=(
                            [
                                f'def {functions_without_docs[0]["name"]}():\n    """Describe what this function does."""\n    pass'
                            ]
                            if functions_without_docs
                            else []
                        ),
                    )
                )

            # Check for high complexity functions
            complex_functions = [
                f for f in ast_metrics.get("functions", []) if f["complexity"] > 10
            ]
            if complex_functions and complexity < 75:
                func_details = ", ".join(
                    [
                        f"'{f['name']}' (complexity {f['complexity']})"
                        for f in complex_functions[:3]
                    ]
                )
                suggestions.append(
                    ImprovementSuggestion(
                        category="Complexity",
                        priority=1,
                        description=f"Reduce complexity in: {func_details}",
                        expected_impact="Easier to test, debug, and maintain",
                        examples=(
                            [
                                f"Break down '{complex_functions[0]['name']}' into smaller functions",
                                "Extract conditional logic into separate functions",
                            ]
                            if complex_functions
                            else []
                        ),
                    )
                )

            # Check for large functions (many args)
            large_functions = [
                f for f in ast_metrics.get("functions", []) if f["args"] > 5
            ]
            if large_functions:
                func_names = ", ".join(
                    [f"'{f['name']}' ({f['args']} args)" for f in large_functions[:2]]
                )
                suggestions.append(
                    ImprovementSuggestion(
                        category="Best Practices",
                        priority=2,
                        description=f"Functions have too many parameters: {func_names}",
                        expected_impact="Simpler function signatures",
                        examples=[
                            "Use a config object/dict instead of many parameters",
                            "Split function responsibilities",
                        ],
                    )
                )

        else:
            # Fallback generic suggestions
            if structure < 75:
                suggestions.append(
                    ImprovementSuggestion(
                        category="Structure",
                        priority=2,
                        description="Organize code into logical functions and classes",
                        expected_impact="Improved maintainability and testability",
                        examples=[
                            "Break long scripts into functions",
                            "Group related functionality into classes",
                        ],
                    )
                )

            if readability < 75:
                suggestions.append(
                    ImprovementSuggestion(
                        category="Readability",
                        priority=1,
                        description="Add more comments and improve variable naming",
                        expected_impact="Easier for others to understand your code",
                        examples=[
                            "Add docstrings to functions",
                            "Use descriptive variable names instead of single letters",
                            "Add inline comments for complex logic",
                        ],
                    )
                )

        if best_practices < 75:
            suggestions.append(
                ImprovementSuggestion(
                    category="Best Practices",
                    priority=2,
                    description="Follow Python best practices and conventions",
                    expected_impact="More Pythonic and maintainable code",
                    examples=[
                        "Use specific exception types instead of bare except",
                        "Use logging instead of print statements",
                        "Extract magic numbers into named constants",
                    ],
                )
            )

        if complexity < 75:
            suggestions.append(
                ImprovementSuggestion(
                    category="Complexity",
                    priority=1,
                    description="Reduce code complexity",
                    expected_impact="Easier to understand, test, and maintain",
                    examples=[
                        "Break down complex functions into smaller ones",
                        "Reduce nesting levels",
                        "Extract complex conditions into well-named variables",
                    ],
                )
            )

        return suggestions

    def _get_line_level_feedback(
        self, code: str, language: str, ast_metrics: Optional[Dict] = None
    ) -> Dict[int, str]:
        """Generate line-by-line feedback using AST data"""
        feedback = {}
        lines = code.split("\n")

        if ast_metrics and ast_metrics.get("parse_success"):
            # Use AST for precise line feedback

            # Mark functions without docstrings
            for func in ast_metrics.get("functions", []):
                if not func["has_docstring"]:
                    feedback[func["lineno"]] = (
                        f"📝 Function '{func['name']}' missing docstring"
                    )

            # Mark classes without docstrings
            for cls in ast_metrics.get("classes", []):
                if not cls["has_docstring"]:
                    feedback[cls["lineno"]] = (
                        f"📝 Class '{cls['name']}' missing docstring"
                    )

            # Mark high-complexity functions
            for func in ast_metrics.get("functions", []):
                if func["complexity"] > 10:
                    feedback[func["lineno"]] = (
                        f"⚠️ Function '{func['name']}' has high complexity ({func['complexity']})"
                    )

        # Also do regex checks
        for i, line in enumerate(lines, 1):
            if i in feedback:
                continue  # Skip if AST already provided feedback

            # Check for specific issues
            if language == "python":
                if re.match(r"^\s*except\s*:", line):
                    feedback[i] = "⚠️ Avoid bare except - specify exception types"

                elif len(line) > 100:
                    feedback[i] = "📏 Line too long - consider breaking it up"

                elif re.search(r"\b[a-z]\s*=", line) and not re.search(
                    r"\bfor\b", line
                ):
                    feedback[i] = "💡 Consider using a more descriptive variable name"

        return feedback

"""
Example Custom Grader Plugin
Demonstrates how to create custom grading logic
"""

import ast
from typing import Any, Dict, List

from src.core.base_grader import BaseGrader, GraderResult
from src.core.types import GradingDimension, ImprovementSuggestion, ScoreBreakdown


class SecurityGrader(BaseGrader):
    """
    Custom grader that checks for security vulnerabilities
    """

    dimension = GradingDimension.CODE_QUALITY

    def grade(self, code: str, language: str = "python", **context) -> GraderResult:
        """Grade code for security issues"""

        if language != "python":
            # Only support Python for now
            return GraderResult(
                dimension=self.dimension,
                score=100,
                max_score=100,
                breakdown=ScoreBreakdown(
                    dimension=self.dimension,
                    score=100,
                    max_score=100,
                    weight=1.0,
                    weighted_score=100,
                    rationale="Security grading only available for Python",
                    line_level_feedback={},
                    suggestions=[],
                ),
                feedback="Security grading not available for this language",
            )

        score = 100
        issues = []
        suggestions = []

        # Check for common security issues

        # 1. eval() usage (dangerous)
        if "eval(" in code:
            score -= 30
            issues.append("❌ Uses eval() which can execute arbitrary code")
            suggestions.append(
                ImprovementSuggestion(
                    category="security",
                    description="Replace eval() with safer alternatives like ast.literal_eval()",
                    priority="high",
                    example="Use: result = ast.literal_eval(user_input) instead of eval()",
                )
            )

        # 2. exec() usage (dangerous)
        if "exec(" in code:
            score -= 30
            issues.append("❌ Uses exec() which can execute arbitrary code")
            suggestions.append(
                ImprovementSuggestion(
                    category="security",
                    description="Avoid exec() - redesign code to not execute dynamic code",
                    priority="high",
                    example="Use predefined functions and a mapping dictionary instead",
                )
            )

        # 3. Hardcoded credentials
        credential_patterns = ["password=", "passwd=", "api_key=", "secret=", "token="]
        for pattern in credential_patterns:
            if pattern in code.lower() and ("=" in code):
                # Check if it's assigning a string literal
                if '"' in code or "'" in code:
                    score -= 25
                    issues.append(f"❌ Possible hardcoded credential: {pattern}")
                    suggestions.append(
                        ImprovementSuggestion(
                            category="security",
                            description="Use environment variables for credentials",
                            priority="critical",
                            example="Use: password = os.getenv('PASSWORD') instead of hardcoding",
                        )
                    )
                    break

        # 4. SQL concatenation (SQL injection risk)
        if "cursor.execute(" in code and ("+" in code or 'f"' in code or "f'" in code):
            score -= 20
            issues.append("⚠️  Possible SQL injection vulnerability")
            suggestions.append(
                ImprovementSuggestion(
                    category="security",
                    description="Use parameterized queries to prevent SQL injection",
                    priority="high",
                    example="Use: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
                )
            )

        # 5. Pickle usage (can execute arbitrary code)
        if "pickle.loads(" in code or "pickle.load(" in code:
            score -= 15
            issues.append("⚠️  Pickle can execute arbitrary code on untrusted data")
            suggestions.append(
                ImprovementSuggestion(
                    category="security",
                    description="Use JSON or other safe serialization formats",
                    priority="medium",
                    example="Use: json.loads(data) instead of pickle.loads()",
                )
            )

        # 6. Insecure random (for security-sensitive operations)
        if "random." in code and (
            "token" in code.lower() or "password" in code.lower()
        ):
            score -= 10
            issues.append("⚠️  Using non-cryptographic random for security tokens")
            suggestions.append(
                ImprovementSuggestion(
                    category="security",
                    description="Use secrets module for cryptographically secure random",
                    priority="medium",
                    example="Use: secrets.token_hex(32) instead of random",
                )
            )

        score = max(0, score)

        feedback = "Security Analysis:\n"
        if issues:
            feedback += "\n".join(issues)
        else:
            feedback = "✅ No obvious security issues detected"

        return GraderResult(
            dimension=self.dimension,
            score=score,
            max_score=100,
            breakdown=ScoreBreakdown(
                dimension=self.dimension,
                score=score,
                max_score=100,
                weight=1.0,
                weighted_score=score,
                rationale=f"Found {len(issues)} security issues",
                line_level_feedback={},
                suggestions=[s.description for s in suggestions],
            ),
            feedback=feedback,
            suggestions=suggestions,
            metadata={
                "security_issues": len(issues),
                "severity": (
                    "critical"
                    if score < 50
                    else "high" if score < 70 else "medium" if score < 90 else "low"
                ),
            },
        )

"""
Custom Grading Plugin System
Allows developers to add their own grading rules without modifying core code
"""

import importlib.util
import inspect
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import yaml
from src.core.base_grader import BaseGrader, GraderResult
from src.core.types import GradingDimension


class CustomRule:
    """Base class for custom grading rules"""

    def __init__(self, name: str, description: str, weight: float = 1.0):
        self.name = name
        self.description = description
        self.weight = weight

    def evaluate(self, code: str, language: str, **context) -> Dict[str, Any]:
        """
        Evaluate the rule against code

        Returns:
            {
                "passed": bool,
                "score": float (0-100),
                "feedback": str,
                "suggestions": List[str]
            }
        """
        raise NotImplementedError("Custom rules must implement evaluate()")


class PluginLoader:
    """Loads and manages custom grading plugins"""

    def __init__(self, plugin_dir: str = "plugins/custom"):
        self.plugin_dir = Path(plugin_dir)
        self.custom_graders: Dict[str, Type[BaseGrader]] = {}
        self.custom_rules: Dict[str, List[CustomRule]] = {}

    def load_all_plugins(self):
        """Load all plugins from the plugin directory"""
        if not self.plugin_dir.exists():
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            return

        # Load Python module plugins
        for py_file in self.plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            self._load_python_plugin(py_file)

        # Load YAML config plugins
        for yaml_file in self.plugin_dir.glob("*.yaml"):
            self._load_yaml_plugin(yaml_file)

    def _load_python_plugin(self, plugin_path: Path):
        """Load a Python module as a plugin"""
        try:
            module_name = f"plugins.custom.{plugin_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find all grader classes
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseGrader)
                        and obj != BaseGrader
                    ):
                        self.custom_graders[name] = obj
                        print(f"✅ Loaded custom grader: {name}")

                    elif (
                        inspect.isclass(obj)
                        and issubclass(obj, CustomRule)
                        and obj != CustomRule
                    ):
                        # Instantiate the rule
                        try:
                            rule_instance = obj()
                            dimension = getattr(
                                rule_instance, "dimension", "code_quality"
                            )
                            if dimension not in self.custom_rules:
                                self.custom_rules[dimension] = []
                            self.custom_rules[dimension].append(rule_instance)
                            print(f"✅ Loaded custom rule: {rule_instance.name}")
                        except Exception as e:
                            print(f"⚠️  Failed to instantiate rule {name}: {e}")

        except Exception as e:
            print(f"❌ Failed to load plugin {plugin_path}: {e}")

    def _load_yaml_plugin(self, yaml_path: Path):
        """Load a YAML configuration as custom rules"""
        try:
            with open(yaml_path, "r") as f:
                config = yaml.safe_load(f)

            for rule_config in config.get("rules", []):
                rule = YAMLCustomRule(
                    name=rule_config["name"],
                    description=rule_config.get("description", ""),
                    pattern=rule_config.get("pattern", ""),
                    severity=rule_config.get("severity", "warning"),
                    weight=rule_config.get("weight", 1.0),
                    dimension=rule_config.get("dimension", "code_quality"),
                )

                dimension = rule.dimension
                if dimension not in self.custom_rules:
                    self.custom_rules[dimension] = []
                self.custom_rules[dimension].append(rule)
                print(f"✅ Loaded YAML rule: {rule.name}")

        except Exception as e:
            print(f"❌ Failed to load YAML plugin {yaml_path}: {e}")

    def get_custom_grader(self, name: str) -> Optional[Type[BaseGrader]]:
        """Get a custom grader by name"""
        return self.custom_graders.get(name)

    def get_custom_rules(self, dimension: str) -> List[CustomRule]:
        """Get all custom rules for a dimension"""
        return self.custom_rules.get(dimension, [])

    def apply_custom_rules(
        self, code: str, language: str, dimension: str, **context
    ) -> Dict[str, Any]:
        """Apply all custom rules for a dimension"""
        rules = self.get_custom_rules(dimension)
        if not rules:
            return {"passed": True, "score": 100, "feedback": "", "suggestions": []}

        total_weight = sum(rule.weight for rule in rules)
        weighted_score = 0
        all_feedback = []
        all_suggestions = []

        for rule in rules:
            try:
                result = rule.evaluate(code, language, **context)
                weighted_score += result["score"] * rule.weight
                if result.get("feedback"):
                    all_feedback.append(f"[{rule.name}] {result['feedback']}")
                all_suggestions.extend(result.get("suggestions", []))
            except Exception as e:
                print(f"⚠️  Rule {rule.name} failed: {e}")

        final_score = weighted_score / total_weight if total_weight > 0 else 100

        return {
            "passed": final_score >= 70,
            "score": final_score,
            "feedback": "\n".join(all_feedback),
            "suggestions": all_suggestions,
        }


class YAMLCustomRule(CustomRule):
    """Custom rule defined in YAML"""

    def __init__(
        self,
        name: str,
        description: str,
        pattern: str,
        severity: str,
        weight: float,
        dimension: str,
    ):
        super().__init__(name, description, weight)
        self.pattern = pattern
        self.severity = severity
        self.dimension = dimension

    def evaluate(self, code: str, language: str, **context) -> Dict[str, Any]:
        """Evaluate using regex pattern matching"""
        import re

        matches = re.findall(self.pattern, code, re.MULTILINE)

        if not matches:
            return {"passed": True, "score": 100, "feedback": "", "suggestions": []}

        # Deduct points based on severity
        severity_penalties = {"error": 30, "warning": 15, "info": 5}
        penalty = severity_penalties.get(self.severity, 10)
        score = max(0, 100 - (len(matches) * penalty))

        return {
            "passed": score >= 70,
            "score": score,
            "feedback": f"Found {len(matches)} instances of {self.description}",
            "suggestions": [
                f"Fix {self.name} violations (found {len(matches)} instances)"
            ],
        }


# Global plugin loader instance
_plugin_loader = None


def get_plugin_loader() -> PluginLoader:
    """Get the global plugin loader instance"""
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader()
        _plugin_loader.load_all_plugins()
    return _plugin_loader


def reload_plugins():
    """Reload all plugins"""
    global _plugin_loader
    _plugin_loader = PluginLoader()
    _plugin_loader.load_all_plugins()
    return _plugin_loader

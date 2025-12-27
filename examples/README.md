# ToastyAnalytics Examples

This directory contains practical examples demonstrating how to use ToastyAnalytics.

## Quick Start

1. Install ToastyAnalytics:
```bash
pip install -e ..
```

2. Run basic examples:
```bash
python basic_usage.py
```

3. Start MCP server for API examples:
```bash
toastyanalytics serve --port 8000
```

4. Run API examples (in new terminal):
```bash
python api_usage.py
```

## Examples

### basic_usage.py
- Example 1: Basic code grading
- Example 2: Meta-learning integration
- Example 3: Multiple grading dimensions
- Example 4: Custom weights configuration
- Example 5: Line-level feedback

### api_usage.py
- Example 1: Grade code via REST API
- Example 2: Submit feedback
- Example 3: Get user analytics
- Example 4: Multi-agent coordination
- Example 5: Health checks

## Sample Code Files

Example Python files you can use for testing:

**good_code.py** - Well-written Python code
**bad_code.py** - Code with quality issues
**medium_code.py** - Average quality code

Grade them with:
```bash
toastyanalytics grade good_code.py --user-id test_user -d code_quality
```

## Integration Patterns

See the examples for common integration patterns:
- CLI usage
- Python SDK usage
- REST API usage
- Meta-learning workflows
- Multi-agent coordination

## More Information

- [QUICKSTART.md](../QUICKSTART.md) - Getting started guide
- [docs/USAGE.md](../docs/USAGE.md) - Comprehensive usage guide
- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System architecture

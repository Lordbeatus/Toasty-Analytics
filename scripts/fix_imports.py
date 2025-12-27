"""
Fix all relative imports in the toastyanalytics codebase
Run this once to update all files
"""

import re
from pathlib import Path


def fix_imports_in_file(file_path: Path):
    """Fix relative imports to absolute imports in a Python file"""

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Add path setup if needed
    needs_path_setup = "from .." in content or "import .." in content
    has_path_setup = "sys.path.insert" in content

    if needs_path_setup and not has_path_setup:
        # Find where to insert (after docstring and before first import)
        lines = content.split("\n")
        insert_pos = 0
        in_docstring = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if not in_docstring:
                    in_docstring = True
                elif stripped.endswith('"""') or stripped.endswith("'''"):
                    in_docstring = False
                    insert_pos = i + 1
            elif not in_docstring and (
                stripped.startswith("from") or stripped.startswith("import")
            ):
                insert_pos = i
                break

        # Add import sys and Path
        if "import sys" not in content:
            lines.insert(insert_pos, "import sys")
            insert_pos += 1
        if "from pathlib import Path" not in content:
            lines.insert(insert_pos, "from pathlib import Path")
            insert_pos += 1

        # Add path setup
        path_setup = """
# Add parent directory to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))
"""
        lines.insert(insert_pos, path_setup)
        content = "\n".join(lines)

    # Fix relative imports
    # from ..module import X -> from module import X
    content = re.sub(r"from \.\.([a-zA-Z_][a-zA-Z0-9_.]*)", r"from \1", content)

    # from .module import X -> from module import X (single dot)
    # But be careful with relative imports within same package
    # For now, keep single-dot imports as they're usually correct

    # Only write if changed
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Fixed: {file_path}")
        return True
    return False


def main():
    # Find all Python files
    root = Path(__file__).parent
    python_files = list(root.rglob("*.py"))

    # Exclude certain directories
    exclude_dirs = {"__pycache__", ".venv", "venv", "build", "dist", ".git", "docs"}

    fixed_count = 0
    for py_file in python_files:
        # Skip if in excluded directory
        if any(ex in py_file.parts for ex in exclude_dirs):
            continue

        # Skip this script itself
        if py_file.name == "fix_imports.py":
            continue

        try:
            if fix_imports_in_file(py_file):
                fixed_count += 1
        except Exception as e:
            print(f"❌ Error in {py_file}: {e}")

    print(f"\n🎉 Fixed {fixed_count} files!")


if __name__ == "__main__":
    main()

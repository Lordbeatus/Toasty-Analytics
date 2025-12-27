"""
Setup configuration for toastyanalytics
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path, encoding="utf-8") as f:
        requirements = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]

setup(
    name="toastyanalytics",
    version="2.0.0",
    author="ToastyAnalytics Team",
    author_email="contact@toastyanalytics.dev",
    description="AI Agent Self-Improvement & Grading System with Meta-Learning",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Lordbeatus/Toastimer",
    packages=find_packages(
        exclude=["tests", "tests.*", "vscode-extension", "vscode-extension.*"]
    ),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "toastyanalytics=toastyanalytics.cli.main:cli",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-cov>=4.1.0",
            "black>=23.12.1",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
            "isort>=5.13.2",
        ],
        "postgres": [
            "psycopg2-binary>=2.9.9",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)

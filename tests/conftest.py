"""
Test suite for toastyanalytics
"""

import sys
from pathlib import Path

# Add parent directory to path
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.database.models import DatabaseManager
from src.meta_learning.engine import MetaLearner


@pytest.fixture
def db_manager():
    """Create in-memory database for testing"""
    db = DatabaseManager("sqlite:///:memory:")
    yield db
    db.close()


@pytest.fixture
def meta_learner(db_manager):
    """Create meta-learner for testing"""
    return MetaLearner(db_manager)


@pytest.fixture
def sample_code():
    """Sample Python code for testing"""
    return """
def calculate_sum(a, b):
    '''Calculate sum of two numbers'''
    return a + b

def main():
    result = calculate_sum(5, 10)
    print(f'Result: {result}')

if __name__ == '__main__':
    main()
"""


@pytest.fixture
def bad_code():
    """Poorly written code for testing"""
    return """
def f(x):
    try:
        return x+1
    except:
        pass
a=1
b=2
c=3
print(a)
print(b)
print(c)
"""

"""
Test suite for toastyanalytics
"""

import os

import pytest

# Configuration is read at import time, so set test values before importing it.
os.environ.setdefault("AUTH_ENABLED", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-use")
os.environ.setdefault("TOASTY_API_KEYS", "test-api-key:test-user:admin:*")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("RATE_LIMIT_ENABLED", "true")
os.environ.setdefault("RATE_LIMIT", "1000")
os.environ.setdefault("RATE_LIMIT_ADMIN", "0")

from toastyanalytics.database.models import DatabaseManager  # noqa: E402
from toastyanalytics.meta_learning.engine import MetaLearner  # noqa: E402


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

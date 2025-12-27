import requests

# Test 1: Minimal code (should score LOW)
minimal = """
x = 5
"""

# Test 2: Bad code (should score LOW)
bad = """
def f(a,b,c,d,e,f,g):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        print(a+b+c+d+e+f+g)
"""

# Test 3: Good code (should score HIGH)
good = """
def calculate_statistics(data: list) -> dict:
    '''Calculate mean, median, and standard deviation.
    
    Args:
        data: List of numeric values
        
    Returns:
        Dictionary with statistics
    '''
    if not data:
        return {'mean': 0, 'median': 0, 'std': 0}
    
    mean = sum(data) / len(data)
    sorted_data = sorted(data)
    median = sorted_data[len(data) // 2]
    
    return {'mean': mean, 'median': median}
"""

# Test 4: Excellent code (should score VERY HIGH)
excellent = """
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    '''Process and validate data with comprehensive error handling.'''
    
    def __init__(self, config: Dict[str, any]):
        '''Initialize processor with configuration.
        
        Args:
            config: Configuration dictionary
        '''
        self.config = config
        logger.info('DataProcessor initialized')
    
    def process(self, items: List[int]) -> Optional[Dict[str, float]]:
        '''Process items and return statistics.
        
        Args:
            items: List of integers to process
            
        Returns:
            Dictionary of statistics or None if invalid
        '''
        try:
            if not items:
                logger.warning('Empty items list provided')
                return None
            
            total = sum(items)
            average = total / len(items)
            
            return {'total': total, 'average': average}
        except (TypeError, ValueError) as e:
            logger.error(f'Processing failed: {e}')
            return None
"""

tests = [("Minimal", minimal), ("Bad", bad), ("Good", good), ("Excellent", excellent)]

print("Testing score differentiation:\n")
for name, code in tests:
    r = requests.post(
        "http://localhost:8000/grade",
        json={
            "code": code,
            "language": "python",
            "user_id": "differentiation_test",
            "dimensions": ["code_quality"],
        },
    )

    if r.status_code == 200:
        result = r.json()
        score = result.get("overall_score", 0)
        print(f"{name:12s}: {score:5.1f}/100")

        # Show breakdown
        if "feedback" in result and "code_quality" in result["feedback"]:
            breakdown = result["feedback"]["code_quality"].get("breakdown", {})
            print(f"             Structure: {breakdown.get('structure', 'N/A')}")
            print(f"             Readability: {breakdown.get('readability', 'N/A')}")
            print(
                f"             Best Practices: {breakdown.get('best_practices', 'N/A')}"
            )
            print(f"             Complexity: {breakdown.get('complexity', 'N/A')}")
        print()
    else:
        print(f"{name}: ERROR - {r.status_code}")
        print(f"  {r.text}\n")

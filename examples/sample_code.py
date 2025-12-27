"""
Sample code files for testing ToastyAnalytics grading
"""

# good_code.py - Well-written Python code
good_code = """
from typing import List, Optional


def calculate_statistics(numbers: List[float]) -> dict:
    \"\"\"
    Calculate basic statistics for a list of numbers.
    
    Args:
        numbers: List of numerical values
        
    Returns:
        Dictionary containing mean, median, min, and max
        
    Raises:
        ValueError: If the list is empty
    \"\"\"
    if not numbers:
        raise ValueError("Cannot calculate statistics for empty list")
    
    sorted_numbers = sorted(numbers)
    n = len(sorted_numbers)
    
    # Calculate mean
    mean = sum(sorted_numbers) / n
    
    # Calculate median
    if n % 2 == 0:
        median = (sorted_numbers[n//2 - 1] + sorted_numbers[n//2]) / 2
    else:
        median = sorted_numbers[n//2]
    
    return {
        'mean': mean,
        'median': median,
        'min': sorted_numbers[0],
        'max': sorted_numbers[-1],
        'count': n
    }


def main():
    \"\"\"Example usage.\"\"\"
    test_data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    stats = calculate_statistics(test_data)
    
    print(f"Statistics for {test_data}:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
"""

# bad_code.py - Code with quality issues
bad_code = """
def calc(l):
    # TODO: finish this
    x=0
    for i in l:
        x=x+i
    return x/len(l)

def process(data):
    result=[]
    for d in data:
        if d>0:
            result.append(d*2)
        else:
            result.append(d)
    return result

l=[1,2,3,4,5]
r=calc(l)
print(r)
p=process(l)
print(p)
"""

# medium_code.py - Average quality code
medium_code = """
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

def is_prime(num):
    if num < 2:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True

# Test
print("Fibonacci(10):", fibonacci(10))
print("Is 17 prime?", is_prime(17))
"""

# Save to files
if __name__ == "__main__":
    with open("good_code.py", "w") as f:
        f.write(good_code)
    print("✓ Created good_code.py")

    with open("bad_code.py", "w") as f:
        f.write(bad_code)
    print("✓ Created bad_code.py")

    with open("medium_code.py", "w") as f:
        f.write(medium_code)
    print("✓ Created medium_code.py")

    print("\nUse these files to test grading:")
    print("  toastyanalytics grade good_code.py --user-id test -d code_quality")

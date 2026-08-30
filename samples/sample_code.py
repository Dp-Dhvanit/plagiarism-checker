def calculate_fibonacci(n):
    """
    Calculate the nth Fibonacci number.
    Returns 0 for negative inputs.
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
        
    return b

if __name__ == "__main__":
    for i in range(10):
        print(f"Fibonacci({i}) = {calculate_fibonacci(i)}")

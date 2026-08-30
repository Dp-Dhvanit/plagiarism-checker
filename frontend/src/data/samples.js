export const SAMPLE_AI =
  "Photosynthesis is a fundamental biological process through which plants, algae, and certain bacteria convert light energy into chemical energy. During this process, organisms absorb sunlight and utilize it to transform carbon dioxide and water into glucose and oxygen. Chlorophyll, the green pigment found in chloroplasts, plays a critical role by capturing light energy. Overall, photosynthesis not only sustains plant growth but also supports life on Earth by producing oxygen and forming the base of most food chains. Understanding this process is essential for students studying biology and environmental science.";

export const SAMPLE_HUMAN =
  "Okay so honestly I still don't really get why the midterm felt that hard? Like, I studied the slides twice, maybe three times if you count skim-reading at 1am with leftover pizza. My roommate kept blasting music and I kept rewriting the same paragraph about photosynthesis because every time I tried to sound 'academic' it just came out weird. Anyway — plants make sugar from light, I think? Wait, carbon dioxide too. Whatever. Point is I panicked on question 4 and wrote something about chlorophyll that probably made zero sense. Hope partial credit is a thing.";

export const SAMPLE_CODE_AI = `def calculate_factorial(n):
    """
    This function calculates the factorial of a given non-negative integer.

    Args:
        n (int): The non-negative integer whose factorial is to be calculated.

    Returns:
        int: The factorial of the given integer.

    Raises:
        ValueError: If the input is a negative integer.
    """
    # Validate the input to ensure it is a non-negative integer
    if not isinstance(n, int) or n < 0:
        raise ValueError("Input must be a non-negative integer.")

    # Initialize the result variable to store the factorial value
    result = 1

    # Iterate through each integer from 1 to n and multiply
    for i in range(1, n + 1):
        result *= i

    return result


def is_prime(number):
    """
    This function determines whether a given number is prime.

    Args:
        number (int): The integer to check for primality.

    Returns:
        bool: True if the number is prime, False otherwise.
    """
    # Handle edge cases for numbers less than or equal to 1
    if number <= 1:
        return False

    # Check divisibility for all numbers up to the square root
    for divisor in range(2, int(number ** 0.5) + 1):
        if number % divisor == 0:
            return False

    return True


if __name__ == "__main__":
    # Example usage of the calculate_factorial function
    print(calculate_factorial(5))
    print(is_prime(17))`;

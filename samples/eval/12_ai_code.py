"""Utilities for computing statistical measures on numeric datasets."""

from typing import List, Optional


def calculate_mean(values: List[float]) -> float:
    """
    Calculate the arithmetic mean of a list of numeric values.

    Args:
        values (List[float]): A list of numeric values to average.

    Returns:
        float: The arithmetic mean of the provided values.

    Raises:
        ValueError: If the input list is empty.
        TypeError: If the input is not a list.
    """
    # Validate that the input is of the expected type
    if not isinstance(values, list):
        raise TypeError("Input must be a list of numeric values.")

    # Ensure the list is not empty before performing division
    if len(values) == 0:
        raise ValueError("Cannot calculate the mean of an empty list.")

    # Compute the total sum of all values in the list
    total = sum(values)

    # Divide the total by the number of elements to obtain the mean
    return total / len(values)


def calculate_median(values: List[float]) -> float:
    """
    Calculate the median value of a list of numeric values.

    Args:
        values (List[float]): A list of numeric values.

    Returns:
        float: The median of the provided values.

    Raises:
        ValueError: If the input list is empty.
    """
    # Validate that the list contains at least one element
    if not values:
        raise ValueError("Cannot calculate the median of an empty list.")

    # Sort the values in ascending order for median calculation
    sorted_values = sorted(values)
    length = len(sorted_values)
    midpoint = length // 2

    # Handle the even-length case by averaging the two central values
    if length % 2 == 0:
        return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2

    # Handle the odd-length case by returning the central value
    return sorted_values[midpoint]

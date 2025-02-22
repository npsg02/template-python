"""Mathematical utility functions."""

from typing import List, Union

Number = Union[int, float]


def calculate_mean(numbers: List[Number]) -> float:
    """Calculate the arithmetic mean of a list of numbers.

    Args:
        numbers: A list of integers or floating point numbers

    Returns:
        float: The arithmetic mean of the input numbers

    Raises:
        ValueError: If the input list is empty
        TypeError: If any element is not a number
    """
    if not numbers:
        raise ValueError("Cannot calculate mean of empty list")

    if not all(isinstance(x, (int, float)) for x in numbers):
        raise TypeError("All elements must be numbers")

    return sum(numbers) / len(numbers)


def calculate_median(numbers: List[Number]) -> float:
    """Calculate the median value from a list of numbers.

    Args:
        numbers: A list of integers or floating point numbers

    Returns:
        float: The median value of the input numbers

    Raises:
        ValueError: If the input list is empty
        TypeError: If any element is not a number
    """
    if not numbers:
        raise ValueError("Cannot calculate median of empty list")

    if not all(isinstance(x, (int, float)) for x in numbers):
        raise TypeError("All elements must be numbers")

    sorted_numbers = sorted(numbers)
    length = len(sorted_numbers)

    if length % 2 == 0:
        mid = length // 2
        return (sorted_numbers[mid - 1] + sorted_numbers[mid]) / 2
    else:
        return sorted_numbers[length // 2]

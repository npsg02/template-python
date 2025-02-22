"""Tests for mathematical utility functions."""

import pytest
from src.utils.math import calculate_mean, calculate_median

def test_calculate_mean():
    """Test the calculate_mean function with various inputs."""
    # Test with integers
    assert calculate_mean([1, 2, 3, 4, 5]) == 3.0
    
    # Test with floats
    assert calculate_mean([1.5, 2.5, 3.5]) == 2.5
    
    # Test with mixed numbers
    assert calculate_mean([1, 2.5, 3]) == 2.1666666666666665

def test_calculate_mean_errors():
    """Test error handling in calculate_mean function."""
    # Test empty list
    with pytest.raises(ValueError) as exc:
        calculate_mean([])
    assert str(exc.value) == "Cannot calculate mean of empty list"
    
    # Test invalid input types
    with pytest.raises(TypeError) as exc:
        calculate_mean([1, "2", 3])
    assert str(exc.value) == "All elements must be numbers"

def test_calculate_median():
    """Test the calculate_median function with various inputs."""
    # Test odd number of integers
    assert calculate_median([1, 2, 3, 4, 5]) == 3.0
    
    # Test even number of integers
    assert calculate_median([1, 2, 3, 4]) == 2.5
    
    # Test unsorted list
    assert calculate_median([5, 2, 1, 4, 3]) == 3.0
    
    # Test with floats
    assert calculate_median([1.5, 2.5, 3.5]) == 2.5
    
    # Test with mixed numbers
    assert calculate_median([1, 2.5, 3]) == 2.5

def test_calculate_median_errors():
    """Test error handling in calculate_median function."""
    # Test empty list
    with pytest.raises(ValueError) as exc:
        calculate_median([])
    assert str(exc.value) == "Cannot calculate median of empty list"
    
    # Test invalid input types
    with pytest.raises(TypeError) as exc:
        calculate_median([1, "2", 3])
    assert str(exc.value) == "All elements must be numbers"
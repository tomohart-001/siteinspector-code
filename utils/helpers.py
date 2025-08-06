
"""
Helper Utilities
Basic utility functions for common operations
"""
import math
from typing import Union, List, Dict, Any


def round_to_precision(value: Union[float, int], precision: int = 2) -> float:
    """
    Round a number to specified decimal places
    
    Args:
        value: Number to round
        precision: Number of decimal places (default: 2)
        
    Returns:
        Rounded number
    """
    return round(float(value), precision)


def calculate_percentage(part: Union[float, int], whole: Union[float, int]) -> float:
    """
    Calculate percentage of part relative to whole
    
    Args:
        part: The part value
        whole: The whole value
        
    Returns:
        Percentage as float
    """
    if whole == 0:
        return 0.0
    return round_to_precision((part / whole) * 100)


def safe_divide(numerator: Union[float, int], denominator: Union[float, int], 
                default: Union[float, int] = 0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero
    
    Args:
        numerator: Number to divide
        denominator: Number to divide by
        default: Value to return if denominator is zero
        
    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return float(default)
    return float(numerator) / float(denominator)


def clamp(value: Union[float, int], min_val: Union[float, int], 
          max_val: Union[float, int]) -> Union[float, int]:
    """
    Clamp a value between minimum and maximum bounds
    
    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def format_area(area_sqm: Union[float, int]) -> str:
    """
    Format area in square meters with appropriate units
    
    Args:
        area_sqm: Area in square meters
        
    Returns:
        Formatted area string
    """
    if area_sqm >= 10000:  # 1 hectare
        hectares = area_sqm / 10000
        return f"{round_to_precision(hectares)} ha"
    else:
        return f"{round_to_precision(area_sqm)} m²"


def is_valid_coordinates(lat: Union[float, int], lng: Union[float, int]) -> bool:
    """
    Check if latitude and longitude coordinates are valid
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        True if coordinates are valid
    """
    return (-90 <= lat <= 90) and (-180 <= lng <= 180)

"""Validation and calculation utility functions for Time Tracker."""
from datetime import time


def validate_empty_string(value: str) -> bool:
    """Validate that a string is non-empty after stripping whitespace.
    
    Returns True if the string is valid (non-empty), False otherwise.
    """
    if value is None:
        return False
    return len(value.strip()) > 0


def validate_group_name(name: str) -> bool:
    """Validate research group name is non-empty.
    
    Returns True if name is valid, False otherwise.
    """
    return validate_empty_string(name)


def validate_task_description(description: str) -> bool:
    """Validate task description is non-empty.
    
    Returns True if description is valid, False otherwise.
    """
    return validate_empty_string(description)


def validate_time_block(start: time, end: time) -> bool:
    """Validate that end time is after start time.
    
    Returns True if the time block is valid (end > start), False otherwise.
    """
    if start is None or end is None:
        return True  # Empty blocks are valid
    
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    return end_minutes > start_minutes


def calculate_block_hours(start: time, end: time) -> float:
    """Calculate hours between two times.
    
    Returns 0.0 if either time is None.
    """
    if start is None or end is None:
        return 0.0
    
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    return (end_minutes - start_minutes) / 60.0


def calculate_total_hours(morning_start: time, morning_end: time,
                          afternoon_start: time, afternoon_end: time) -> float:
    """Calculate total hours from both time blocks.
    
    Returns the sum of morning and afternoon block durations, rounded to 2 decimal places.
    """
    morning = calculate_block_hours(morning_start, morning_end)
    afternoon = calculate_block_hours(afternoon_start, afternoon_end)
    return round(morning + afternoon, 2)


def calculate_pay(total_hours: float, rate: float = 107.93) -> float:
    """Calculate pay based on total hours and hourly rate.
    
    Default rate is 107.93 per hour.
    Returns pay rounded to 2 decimal places.
    """
    return round(total_hours * rate, 2)


def parse_time_blocks_from_form(form_data: dict) -> list:
    """Parse multiple time blocks from form submission.
    
    Expects form data with indexed time block fields:
    - block_start_0, block_end_0
    - block_start_1, block_end_1
    - etc.
    
    Returns a list of tuples: [(start_time, end_time), ...]
    Only returns complete blocks where both start and end are provided.
    """
    blocks = []
    index = 0
    
    while True:
        start_key = f'block_start_{index}'
        end_key = f'block_end_{index}'
        
        # Check if this index exists in form data
        if start_key not in form_data and end_key not in form_data:
            break
        
        start_str = form_data.get(start_key, '').strip()
        end_str = form_data.get(end_key, '').strip()
        
        # Only add complete blocks
        if start_str and end_str:
            try:
                start_parts = start_str.split(':')
                end_parts = end_str.split(':')
                
                start_time = time(int(start_parts[0]), int(start_parts[1]))
                end_time = time(int(end_parts[0]), int(end_parts[1]))
                
                blocks.append((start_time, end_time))
            except (ValueError, IndexError):
                # Skip invalid time formats
                pass
        
        index += 1
    
    return blocks


def calculate_total_hours_from_blocks(blocks: list) -> float:
    """Calculate total hours from a list of time block tuples.
    
    Args:
        blocks: List of tuples [(start_time, end_time), ...]
    
    Returns:
        Sum of all block durations in hours, rounded to 2 decimal places.
    """
    total = 0.0
    for start, end in blocks:
        total += calculate_block_hours(start, end)
    return round(total, 2)

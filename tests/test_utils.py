"""Tests for validation and calculation utility functions."""
import pytest
from datetime import time
from hypothesis import given, strategies as st, settings

from app.utils import (
    validate_empty_string,
    validate_group_name,
    validate_task_description,
    validate_time_block,
    calculate_block_hours,
    calculate_total_hours,
    calculate_pay,
    parse_time_blocks_from_form,
    calculate_total_hours_from_blocks,
)


# Unit Tests

class TestValidateEmptyString:
    def test_empty_string_returns_false(self):
        assert validate_empty_string("") is False

    def test_whitespace_only_returns_false(self):
        assert validate_empty_string("   ") is False
        assert validate_empty_string("\t\n") is False

    def test_none_returns_false(self):
        assert validate_empty_string(None) is False

    def test_valid_string_returns_true(self):
        assert validate_empty_string("test") is True
        assert validate_empty_string("  test  ") is True


class TestValidateTimeBlock:
    def test_valid_block_returns_true(self):
        assert validate_time_block(time(9, 0), time(12, 0)) is True

    def test_end_before_start_returns_false(self):
        assert validate_time_block(time(12, 0), time(9, 0)) is False

    def test_equal_times_returns_false(self):
        assert validate_time_block(time(9, 0), time(9, 0)) is False

    def test_none_values_returns_true(self):
        assert validate_time_block(None, time(12, 0)) is True
        assert validate_time_block(time(9, 0), None) is True
        assert validate_time_block(None, None) is True


class TestCalculateBlockHours:
    def test_three_hour_block(self):
        assert calculate_block_hours(time(9, 0), time(12, 0)) == 3.0

    def test_half_hour_block(self):
        assert calculate_block_hours(time(9, 0), time(9, 30)) == 0.5

    def test_none_start_returns_zero(self):
        assert calculate_block_hours(None, time(12, 0)) == 0.0

    def test_none_end_returns_zero(self):
        assert calculate_block_hours(time(9, 0), None) == 0.0


class TestCalculateTotalHours:
    def test_both_blocks(self):
        result = calculate_total_hours(
            time(9, 0), time(12, 0),
            time(13, 0), time(17, 0)
        )
        assert result == 7.0

    def test_morning_only(self):
        result = calculate_total_hours(
            time(9, 0), time(12, 0),
            None, None
        )
        assert result == 3.0

    def test_afternoon_only(self):
        result = calculate_total_hours(
            None, None,
            time(13, 0), time(17, 0)
        )
        assert result == 4.0


class TestCalculatePay:
    def test_default_rate(self):
        assert calculate_pay(10.0) == 1079.30

    def test_custom_rate(self):
        assert calculate_pay(10.0, rate=50.0) == 500.0

    def test_zero_hours(self):
        assert calculate_pay(0.0) == 0.0


class TestParseTimeBlocksFromForm:
    def test_single_block(self):
        form_data = {
            'block_start_0': '09:00',
            'block_end_0': '12:00'
        }
        result = parse_time_blocks_from_form(form_data)
        assert len(result) == 1
        assert result[0] == (time(9, 0), time(12, 0))

    def test_multiple_blocks(self):
        form_data = {
            'block_start_0': '09:00',
            'block_end_0': '12:00',
            'block_start_1': '13:00',
            'block_end_1': '17:00'
        }
        result = parse_time_blocks_from_form(form_data)
        assert len(result) == 2
        assert result[0] == (time(9, 0), time(12, 0))
        assert result[1] == (time(13, 0), time(17, 0))

    def test_empty_form(self):
        form_data = {}
        result = parse_time_blocks_from_form(form_data)
        assert result == []

    def test_incomplete_block_skipped(self):
        form_data = {
            'block_start_0': '09:00',
            'block_end_0': '',  # Missing end time
            'block_start_1': '13:00',
            'block_end_1': '17:00'
        }
        result = parse_time_blocks_from_form(form_data)
        assert len(result) == 1
        assert result[0] == (time(13, 0), time(17, 0))

    def test_invalid_time_format_skipped(self):
        form_data = {
            'block_start_0': 'invalid',
            'block_end_0': '12:00',
            'block_start_1': '13:00',
            'block_end_1': '17:00'
        }
        result = parse_time_blocks_from_form(form_data)
        assert len(result) == 1
        assert result[0] == (time(13, 0), time(17, 0))

    def test_whitespace_handling(self):
        form_data = {
            'block_start_0': '  09:00  ',
            'block_end_0': '  12:00  '
        }
        result = parse_time_blocks_from_form(form_data)
        assert len(result) == 1
        assert result[0] == (time(9, 0), time(12, 0))


class TestCalculateTotalHoursFromBlocks:
    def test_single_block(self):
        blocks = [(time(9, 0), time(12, 0))]
        result = calculate_total_hours_from_blocks(blocks)
        assert result == 3.0

    def test_multiple_blocks(self):
        blocks = [
            (time(9, 0), time(12, 0)),
            (time(13, 0), time(17, 0))
        ]
        result = calculate_total_hours_from_blocks(blocks)
        assert result == 7.0

    def test_empty_list(self):
        result = calculate_total_hours_from_blocks([])
        assert result == 0.0

    def test_fractional_hours(self):
        blocks = [(time(9, 0), time(9, 30))]
        result = calculate_total_hours_from_blocks(blocks)
        assert result == 0.5

    def test_rounding(self):
        # 20 minutes = 0.333... hours, should round to 0.33
        blocks = [(time(9, 0), time(9, 20))]
        result = calculate_total_hours_from_blocks(blocks)
        assert result == 0.33


# Property-Based Tests

# Time strategy: generates valid time objects (0-23 hours, 0-59 minutes)
time_strategy = st.builds(
    time,
    st.integers(min_value=0, max_value=23),
    st.integers(min_value=0, max_value=59)
)


@given(
    start_hour=st.integers(min_value=0, max_value=22),
    start_minute=st.integers(min_value=0, max_value=59),
    duration_minutes=st.integers(min_value=1, max_value=720)
)
@settings(max_examples=100)
def test_property_1_time_block_duration_calculation(start_hour, start_minute, duration_minutes):
    """Property 1: Time Block Duration Calculation
    
    For any valid time block (where end > start), the calculated duration
    SHALL equal (end_time - start_time) converted to hours.
    
    **Validates: Requirements 3.3**
    """
    start_minutes_total = start_hour * 60 + start_minute
    end_minutes_total = start_minutes_total + duration_minutes
    
    # Skip if end time would exceed 23:59
    if end_minutes_total > 23 * 60 + 59:
        return
    
    end_hour = end_minutes_total // 60
    end_minute = end_minutes_total % 60
    
    start = time(start_hour, start_minute)
    end = time(end_hour, end_minute)
    
    expected_hours = duration_minutes / 60.0
    actual_hours = calculate_block_hours(start, end)
    
    assert abs(actual_hours - expected_hours) < 0.0001


@given(
    morning_start_hour=st.integers(min_value=6, max_value=10),
    morning_duration=st.integers(min_value=0, max_value=240),
    afternoon_start_hour=st.integers(min_value=12, max_value=16),
    afternoon_duration=st.integers(min_value=0, max_value=240)
)
@settings(max_examples=100)
def test_property_2_total_hours_summation(morning_start_hour, morning_duration, 
                                          afternoon_start_hour, afternoon_duration):
    """Property 2: Total Hours Summation
    
    For any time entry with two time blocks, the total hours SHALL equal
    the sum of the morning block duration plus the afternoon block duration.
    
    **Validates: Requirements 2.2, 3.1**
    """
    # Create morning block
    if morning_duration > 0:
        morning_start = time(morning_start_hour, 0)
        morning_end_minutes = morning_start_hour * 60 + morning_duration
        morning_end = time(morning_end_minutes // 60, morning_end_minutes % 60)
    else:
        morning_start = None
        morning_end = None
    
    # Create afternoon block
    if afternoon_duration > 0:
        afternoon_start = time(afternoon_start_hour, 0)
        afternoon_end_minutes = afternoon_start_hour * 60 + afternoon_duration
        afternoon_end = time(afternoon_end_minutes // 60, afternoon_end_minutes % 60)
    else:
        afternoon_start = None
        afternoon_end = None
    
    expected_hours = round((morning_duration + afternoon_duration) / 60.0, 2)
    actual_hours = calculate_total_hours(morning_start, morning_end, 
                                         afternoon_start, afternoon_end)
    
    assert actual_hours == expected_hours


@given(
    hour1=st.integers(min_value=0, max_value=23),
    minute1=st.integers(min_value=0, max_value=59),
    hour2=st.integers(min_value=0, max_value=23),
    minute2=st.integers(min_value=0, max_value=59)
)
@settings(max_examples=100)
def test_property_3_time_block_validation(hour1, minute1, hour2, minute2):
    """Property 3: Time Block Validation
    
    For any time block where end_time <= start_time, the validation function
    SHALL return false and reject the entry.
    
    **Validates: Requirements 2.4**
    """
    start = time(hour1, minute1)
    end = time(hour2, minute2)
    
    start_total = hour1 * 60 + minute1
    end_total = hour2 * 60 + minute2
    
    if end_total <= start_total:
        assert validate_time_block(start, end) is False
    else:
        assert validate_time_block(start, end) is True


@given(text=st.text(alphabet=st.characters(whitelist_categories=['Zs']), max_size=100))
@settings(max_examples=100)
def test_property_4_empty_string_validation_whitespace(text):
    """Property 4: Empty String Validation (whitespace only)
    
    For any string composed entirely of whitespace (including empty string),
    the validation functions for group name and task description SHALL reject the input.
    
    **Validates: Requirements 1.3, 2.5**
    """
    assert validate_group_name(text) is False
    assert validate_task_description(text) is False


@given(text=st.text(min_size=1).filter(lambda x: len(x.strip()) > 0))
@settings(max_examples=100)
def test_property_4_empty_string_validation_valid(text):
    """Property 4: Empty String Validation (valid strings)
    
    For any string with non-whitespace content, validation SHALL accept the input.
    
    **Validates: Requirements 1.3, 2.5**
    """
    assert validate_group_name(text) is True
    assert validate_task_description(text) is True

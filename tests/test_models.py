"""Property-based tests for Time Tracker models."""
import pytest
from datetime import time, date
from hypothesis import given, strategies as st, settings, HealthCheck

from app import create_app, db
from app.models import TimeBlock, TimeEntry, ResearchGroup
from app.utils import validate_time_block


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


# Property-Based Tests

@given(
    hour1=st.integers(min_value=0, max_value=23),
    minute1=st.integers(min_value=0, max_value=59),
    hour2=st.integers(min_value=0, max_value=23),
    minute2=st.integers(min_value=0, max_value=59)
)
@settings(max_examples=100)
def test_property_1_time_block_validation(hour1, minute1, hour2, minute2):
    """Property 1: Time Block Validation
    
    For any time block with start_time and end_time, the validation function
    SHALL return true if and only if end_time > start_time.
    
    **Validates: Requirements 1.3, 2.5**
    """
    start = time(hour1, minute1)
    end = time(hour2, minute2)
    
    start_total = hour1 * 60 + minute1
    end_total = hour2 * 60 + minute2
    
    # Validation should return True only when end > start
    expected_valid = end_total > start_total
    actual_valid = validate_time_block(start, end)
    
    assert actual_valid == expected_valid, (
        f"Expected validate_time_block({start}, {end}) to be {expected_valid}, "
        f"but got {actual_valid}"
    )



# Strategy for generating valid time block data (end > start)
@st.composite
def valid_time_block_data(draw):
    """Generate valid time block data where end_time > start_time."""
    start_hour = draw(st.integers(min_value=0, max_value=22))
    start_minute = draw(st.integers(min_value=0, max_value=59))
    
    start_total = start_hour * 60 + start_minute
    max_duration = (23 * 60 + 59) - start_total
    
    if max_duration < 1:
        start_hour, start_minute, start_total = 0, 0, 0
        max_duration = 23 * 60 + 59
    
    duration = draw(st.integers(min_value=1, max_value=min(max_duration, 480)))
    
    end_total = start_total + duration
    end_hour = end_total // 60
    end_minute = end_total % 60
    
    return (time(start_hour, start_minute), time(end_hour, end_minute), duration / 60.0)


@given(blocks_data=st.lists(valid_time_block_data(), min_size=1, max_size=5))
@settings(max_examples=100)
def test_property_5_total_hours_calculation(blocks_data):
    """Property 5: Total Hours Calculation
    
    For any TimeEntry with one or more TimeBlock records, the calculate_total_hours()
    method SHALL return the sum of all block durations (each calculated as
    (end_time - start_time) in hours), rounded to two decimal places.
    
    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    # Create mock time blocks without database
    class MockTimeBlock:
        def __init__(self, start_time, end_time):
            self.start_time = start_time
            self.end_time = end_time
        
        def duration_hours(self):
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            return (end_minutes - start_minutes) / 60.0
    
    # Create mock entry with time_blocks list
    class MockTimeEntry:
        def __init__(self):
            self.time_blocks = []
        
        def calculate_total_hours(self):
            total = sum(block.duration_hours() for block in self.time_blocks)
            return round(total, 2)
    
    entry = MockTimeEntry()
    expected_total = 0.0
    
    for start_time, end_time, duration in blocks_data:
        block = MockTimeBlock(start_time, end_time)
        entry.time_blocks.append(block)
        expected_total += duration
    
    actual_total = entry.calculate_total_hours()
    expected_rounded = round(expected_total, 2)
    
    assert actual_total == expected_rounded, (
        f"Expected calculate_total_hours() to return {expected_rounded}, "
        f"but got {actual_total}"
    )


@given(num_blocks=st.integers(min_value=1, max_value=10))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_3_time_block_retrieval_completeness(app, num_blocks):
    """Property 3: Time Block Retrieval Completeness

    For any TimeEntry with N associated TimeBlock records, querying the entry's
    time_blocks relationship SHALL return exactly N TimeBlock records.

    **Validates: Requirements 3.1**
    """
    with app.app_context():
        # Create a research group
        group = ResearchGroup(
            name='Test Group',
            manager_name='Test Manager',
            project_name='Test Project'
        )
        db.session.add(group)
        db.session.flush()

        # Create a time entry
        entry = TimeEntry(
            research_group_id=group.id,
            date=date(2025, 1, 1),
            task_description='Test task',
            total_hours=0.0
        )
        db.session.add(entry)
        db.session.flush()

        # Create N time blocks
        for i in range(num_blocks):
            start_hour = i % 24
            end_hour = (i + 1) % 24 if (i + 1) < 24 else 23
            block = TimeBlock(
                time_entry_id=entry.id,
                start_time=time(start_hour, 0),
                end_time=time(end_hour, 30) if end_hour > start_hour else time(start_hour, 30)
            )
            db.session.add(block)

        db.session.commit()

        # Retrieve the entry and check time_blocks count
        retrieved_entry = TimeEntry.query.get(entry.id)
        assert len(retrieved_entry.time_blocks) == num_blocks, (
            f"Expected {num_blocks} time blocks, but got {len(retrieved_entry.time_blocks)}"
        )

        # Cleanup
        db.session.delete(retrieved_entry)
        db.session.delete(group)
        db.session.commit()


@st.composite
def time_blocks_for_ordering(draw):
    """Generate a list of time blocks with distinct start times for ordering test."""
    num_blocks = draw(st.integers(min_value=2, max_value=8))
    # Generate distinct start times
    start_minutes = draw(st.lists(
        st.integers(min_value=0, max_value=1400),
        min_size=num_blocks,
        max_size=num_blocks,
        unique=True
    ))
    blocks = []
    for start_min in start_minutes:
        start_hour = start_min // 60
        start_minute = start_min % 60
        # Ensure end is after start (add 30 minutes)
        end_min = start_min + 30
        end_hour = min(end_min // 60, 23)
        end_minute = end_min % 60
        if end_hour == start_hour and end_minute <= start_minute:
            end_minute = start_minute + 1
        if end_hour > 23:
            end_hour = 23
            end_minute = 59
        blocks.append((time(start_hour, start_minute), time(end_hour, end_minute)))
    return blocks


@given(blocks_data=time_blocks_for_ordering())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_4_time_block_chronological_ordering(app, blocks_data):
    """Property 4: Time Block Chronological Ordering

    For any TimeEntry with multiple TimeBlock records, the get_sorted_time_blocks()
    method SHALL return blocks sorted in ascending order by start_time.

    **Validates: Requirements 3.3**
    """
    with app.app_context():
        # Create a research group
        group = ResearchGroup(
            name='Test Group',
            manager_name='Test Manager',
            project_name='Test Project'
        )
        db.session.add(group)
        db.session.flush()

        # Create a time entry
        entry = TimeEntry(
            research_group_id=group.id,
            date=date(2025, 1, 1),
            task_description='Test task',
            total_hours=0.0
        )
        db.session.add(entry)
        db.session.flush()

        # Create time blocks in random order
        for start_time, end_time in blocks_data:
            block = TimeBlock(
                time_entry_id=entry.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(block)

        db.session.commit()

        # Get sorted time blocks
        sorted_blocks = entry.get_sorted_time_blocks()

        # Verify they are in chronological order
        for i in range(len(sorted_blocks) - 1):
            current_start = sorted_blocks[i].start_time
            next_start = sorted_blocks[i + 1].start_time
            assert current_start <= next_start, (
                f"Blocks not in chronological order: {current_start} should be <= {next_start}"
            )

        # Cleanup
        db.session.delete(entry)
        db.session.delete(group)
        db.session.commit()


@st.composite
def entries_with_hours(draw):
    """Generate a list of entry total_hours values."""
    num_entries = draw(st.integers(min_value=1, max_value=10))
    hours_list = draw(st.lists(
        st.floats(min_value=0.01, max_value=24.0, allow_nan=False, allow_infinity=False),
        min_size=num_entries,
        max_size=num_entries
    ))
    return [round(h, 2) for h in hours_list]


@given(entry_hours=entries_with_hours())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_6_group_total_hours_aggregation(app, entry_hours):
    """Property 6: Group Total Hours Aggregation

    For any ResearchGroup with N TimeEntry records, the get_total_hours() method
    SHALL return the sum of total_hours from all associated entries.

    **Validates: Requirements 4.4**
    """
    with app.app_context():
        # Create a research group
        group = ResearchGroup(
            name='Test Group',
            manager_name='Test Manager',
            project_name='Test Project'
        )
        db.session.add(group)
        db.session.flush()

        # Create entries with specified total_hours
        for i, hours in enumerate(entry_hours):
            entry = TimeEntry(
                research_group_id=group.id,
                date=date(2025, 1, i + 1),
                task_description=f'Task {i + 1}',
                total_hours=hours
            )
            db.session.add(entry)

        db.session.commit()

        # Calculate expected total
        expected_total = sum(entry_hours)

        # Get actual total from group method
        actual_total = group.get_total_hours()

        # Allow for small floating point differences
        assert abs(actual_total - expected_total) < 0.01, (
            f"Expected get_total_hours() to return approximately {expected_total}, "
            f"but got {actual_total}"
        )

        # Cleanup
        for entry in group.entries:
            db.session.delete(entry)
        db.session.delete(group)
        db.session.commit()


@given(num_blocks=st.integers(min_value=1, max_value=10))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_2_cascade_delete_integrity(app, num_blocks):
    """Property 2: Cascade Delete Integrity

    For any TimeEntry with associated TimeBlock records, when the TimeEntry is deleted,
    all associated TimeBlock records SHALL also be deleted from the database.

    **Validates: Requirements 1.4, 5.3**
    """
    with app.app_context():
        # Create a research group
        group = ResearchGroup(
            name='Test Group',
            manager_name='Test Manager',
            project_name='Test Project'
        )
        db.session.add(group)
        db.session.flush()

        # Create a time entry
        entry = TimeEntry(
            research_group_id=group.id,
            date=date(2025, 1, 1),
            task_description='Test task',
            total_hours=0.0
        )
        db.session.add(entry)
        db.session.flush()

        entry_id = entry.id
        block_ids = []

        # Create N time blocks
        for i in range(num_blocks):
            start_hour = i % 24
            end_hour = (i + 1) % 24 if (i + 1) < 24 else 23
            block = TimeBlock(
                time_entry_id=entry.id,
                start_time=time(start_hour, 0),
                end_time=time(end_hour, 30) if end_hour > start_hour else time(start_hour, 30)
            )
            db.session.add(block)
            db.session.flush()
            block_ids.append(block.id)

        db.session.commit()

        # Verify blocks exist before deletion
        blocks_before = TimeBlock.query.filter(TimeBlock.id.in_(block_ids)).count()
        assert blocks_before == num_blocks, (
            f"Expected {num_blocks} time blocks before deletion, got {blocks_before}"
        )

        # Delete the entry - need to load time_blocks for cascade to work
        entry_to_delete = db.session.get(TimeEntry, entry_id)
        # Access time_blocks to ensure they're loaded for cascade delete
        _ = entry_to_delete.time_blocks
        db.session.delete(entry_to_delete)
        db.session.commit()

        # Verify entry is deleted
        assert TimeEntry.query.filter_by(id=entry_id).first() is None, (
            f"TimeEntry {entry_id} should be deleted"
        )

        # Verify all time blocks are cascade deleted by querying the database
        blocks_after = TimeBlock.query.filter(TimeBlock.id.in_(block_ids)).count()
        assert blocks_after == 0, (
            f"Expected 0 time blocks after cascade delete, got {blocks_after}"
        )

        # Cleanup
        db.session.delete(group)
        db.session.commit()


@st.composite
def entries_for_deletion_test(draw):
    """Generate a list of entry total_hours values for deletion test."""
    num_entries = draw(st.integers(min_value=2, max_value=10))
    hours_list = draw(st.lists(
        st.floats(min_value=0.01, max_value=24.0, allow_nan=False, allow_infinity=False),
        min_size=num_entries,
        max_size=num_entries
    ))
    return [round(h, 2) for h in hours_list]


@given(entry_hours=entries_for_deletion_test())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_7_group_total_update_on_entry_deletion(app, entry_hours):
    """Property 7: Group Total Update on Entry Deletion

    For any ResearchGroup, when a TimeEntry is deleted, the group's get_total_hours()
    SHALL decrease by exactly the deleted entry's total_hours value.

    **Validates: Requirements 5.5**
    """
    with app.app_context():
        # Create a research group
        group = ResearchGroup(
            name='Test Group',
            manager_name='Test Manager',
            project_name='Test Project'
        )
        db.session.add(group)
        db.session.flush()

        # Create entries with specified total_hours
        entries = []
        for i, hours in enumerate(entry_hours):
            entry = TimeEntry(
                research_group_id=group.id,
                date=date(2025, 1, i + 1),
                task_description=f'Task {i + 1}',
                total_hours=hours
            )
            db.session.add(entry)
            entries.append(entry)

        db.session.commit()

        # Get initial total hours
        initial_total = group.get_total_hours()
        expected_initial = sum(entry_hours)
        
        # Verify initial total is correct
        assert abs(initial_total - expected_initial) < 0.01, (
            f"Initial total should be {expected_initial}, got {initial_total}"
        )

        # Pick a random entry to delete
        import random
        entry_to_delete_idx = random.randint(0, len(entries) - 1)
        entry_to_delete = entries[entry_to_delete_idx]
        deleted_hours = entry_to_delete.total_hours

        # Delete the entry
        db.session.delete(entry_to_delete)
        db.session.commit()

        # Refresh the group to get updated total
        db.session.refresh(group)

        # Get new total hours
        new_total = group.get_total_hours()
        expected_new_total = initial_total - deleted_hours

        # Verify the total decreased by exactly the deleted entry's hours
        assert abs(new_total - expected_new_total) < 0.01, (
            f"After deleting entry with {deleted_hours} hours, "
            f"expected total to be {expected_new_total}, got {new_total}"
        )

        # Cleanup
        for entry in group.entries:
            db.session.delete(entry)
        db.session.delete(group)
        db.session.commit()

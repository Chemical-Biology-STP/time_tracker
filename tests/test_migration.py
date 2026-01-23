"""Tests for migration from legacy schema to TimeBlock model."""
import pytest
from datetime import time, date
from hypothesis import given, strategies as st, settings, HealthCheck

from app import create_app, db
from app.models import TimeBlock, TimeEntry, ResearchGroup
from app.migration import migrate_entry_to_time_blocks, run_migration


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


# Strategy for generating optional time values
@st.composite
def optional_time_block(draw, required=False):
    """Generate an optional time block (start, end) tuple.
    
    If required=True, always generates a valid block.
    Otherwise, may return (None, None) for no block.
    """
    if not required and draw(st.booleans()):
        return (None, None)
    
    # Generate valid time block where end > start
    start_hour = draw(st.integers(min_value=0, max_value=22))
    start_minute = draw(st.integers(min_value=0, max_value=59))
    
    start_total = start_hour * 60 + start_minute
    max_end = 23 * 60 + 59
    
    if start_total >= max_end:
        start_hour, start_minute, start_total = 0, 0, 0
    
    duration = draw(st.integers(min_value=1, max_value=min(480, max_end - start_total)))
    end_total = start_total + duration
    end_hour = end_total // 60
    end_minute = end_total % 60
    
    return (time(start_hour, start_minute), time(end_hour, end_minute))


@st.composite
def legacy_entry_data(draw):
    """Generate legacy entry data with morning and/or afternoon blocks.
    
    Ensures morning and afternoon blocks don't have identical times to avoid
    ambiguity in verification.
    """
    morning_block = draw(optional_time_block())
    afternoon_block = draw(optional_time_block())
    
    # If both blocks exist and have identical times, regenerate afternoon
    # to ensure we can distinguish them in verification
    if (morning_block[0] is not None and afternoon_block[0] is not None and
        morning_block[0] == afternoon_block[0] and morning_block[1] == afternoon_block[1]):
        # Make afternoon block different by using a later time range
        afternoon_block = (time(13, 0), time(17, 0))
    
    # Calculate expected total hours
    total_hours = 0.0
    if morning_block[0] is not None:
        m_start = morning_block[0].hour * 60 + morning_block[0].minute
        m_end = morning_block[1].hour * 60 + morning_block[1].minute
        total_hours += (m_end - m_start) / 60.0
    
    if afternoon_block[0] is not None:
        a_start = afternoon_block[0].hour * 60 + afternoon_block[0].minute
        a_end = afternoon_block[1].hour * 60 + afternoon_block[1].minute
        total_hours += (a_end - a_start) / 60.0
    
    return {
        'morning_start': morning_block[0],
        'morning_end': morning_block[1],
        'afternoon_start': afternoon_block[0],
        'afternoon_end': afternoon_block[1],
        'total_hours': round(total_hours, 2)
    }


# Property-Based Tests

@given(entry_data=legacy_entry_data())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_8_migration_data_preservation(app, entry_data):
    """Property 8: Migration Data Preservation

    For any TimeEntry with morning and/or afternoon time data, after migration:
    - If morning_start and morning_end existed, a TimeBlock with those values SHALL exist
    - If afternoon_start and afternoon_end existed, a TimeBlock with those values SHALL exist
    - The entry's total_hours SHALL remain unchanged

    **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
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

        # Create a time entry with the original total_hours
        entry = TimeEntry(
            research_group_id=group.id,
            date=date(2025, 1, 1),
            task_description='Test task',
            total_hours=entry_data['total_hours']
        )
        db.session.add(entry)
        db.session.flush()

        original_total_hours = entry_data['total_hours']
        entry_id = entry.id

        # Run migration for this entry
        blocks = migrate_entry_to_time_blocks(
            entry_id=entry_id,
            morning_start=entry_data['morning_start'],
            morning_end=entry_data['morning_end'],
            afternoon_start=entry_data['afternoon_start'],
            afternoon_end=entry_data['afternoon_end'],
            original_total_hours=original_total_hours
        )

        for block in blocks:
            db.session.add(block)
        db.session.commit()

        # Verify migration results
        retrieved_entry = db.session.get(TimeEntry, entry_id)
        
        # Count expected blocks
        expected_block_count = 0
        if entry_data['morning_start'] is not None:
            expected_block_count += 1
        if entry_data['afternoon_start'] is not None:
            expected_block_count += 1

        # Verify block count
        assert len(retrieved_entry.time_blocks) == expected_block_count, (
            f"Expected {expected_block_count} blocks, got {len(retrieved_entry.time_blocks)}"
        )

        # Verify morning block exists with correct values if it was provided
        if entry_data['morning_start'] is not None:
            morning_blocks = [
                b for b in retrieved_entry.time_blocks
                if b.start_time == entry_data['morning_start'] 
                and b.end_time == entry_data['morning_end']
            ]
            assert len(morning_blocks) == 1, (
                f"Expected morning block with start={entry_data['morning_start']}, "
                f"end={entry_data['morning_end']} to exist"
            )

        # Verify afternoon block exists with correct values if it was provided
        if entry_data['afternoon_start'] is not None:
            afternoon_blocks = [
                b for b in retrieved_entry.time_blocks
                if b.start_time == entry_data['afternoon_start']
                and b.end_time == entry_data['afternoon_end']
            ]
            assert len(afternoon_blocks) == 1, (
                f"Expected afternoon block with start={entry_data['afternoon_start']}, "
                f"end={entry_data['afternoon_end']} to exist"
            )

        # Verify total_hours is preserved
        assert retrieved_entry.total_hours == original_total_hours, (
            f"Expected total_hours to be {original_total_hours}, "
            f"got {retrieved_entry.total_hours}"
        )

        # Cleanup
        db.session.delete(retrieved_entry)
        db.session.delete(group)
        db.session.commit()


# Unit Tests for Migration Edge Cases

class TestMigrationEdgeCases:
    """Unit tests for migration edge cases (Requirement 6.5)."""

    def test_migration_entry_with_no_time_data(self, app):
        """Test migration of entry with no morning or afternoon times.
        
        Requirements: 6.5 - IF a TimeEntry has no morning or afternoon times,
        THEN THE Time_Tracker SHALL skip TimeBlock creation for that entry.
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

            # Create entry with no time data
            entry = TimeEntry(
                research_group_id=group.id,
                date=date(2025, 1, 1),
                task_description='No time data task',
                total_hours=0.0
            )
            db.session.add(entry)
            db.session.flush()

            entry_id = entry.id

            # Run migration with no time data
            blocks = migrate_entry_to_time_blocks(
                entry_id=entry_id,
                morning_start=None,
                morning_end=None,
                afternoon_start=None,
                afternoon_end=None,
                original_total_hours=0.0
            )

            # Should create no blocks
            assert len(blocks) == 0, "Should not create blocks for entry with no time data"

            # Verify entry still exists with no blocks
            retrieved_entry = db.session.get(TimeEntry, entry_id)
            assert len(retrieved_entry.time_blocks) == 0

            # Cleanup
            db.session.delete(retrieved_entry)
            db.session.delete(group)
            db.session.commit()

    def test_migration_entry_with_only_morning_block(self, app):
        """Test migration of entry with only morning times.
        
        Requirements: 6.2 - WHEN migrating a TimeEntry with morning times,
        THE Time_Tracker SHALL create a TimeBlock with the morning_start and morning_end values.
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

            # Create entry
            entry = TimeEntry(
                research_group_id=group.id,
                date=date(2025, 1, 1),
                task_description='Morning only task',
                total_hours=3.0
            )
            db.session.add(entry)
            db.session.flush()

            entry_id = entry.id
            morning_start = time(9, 0)
            morning_end = time(12, 0)

            # Run migration with only morning data
            blocks = migrate_entry_to_time_blocks(
                entry_id=entry_id,
                morning_start=morning_start,
                morning_end=morning_end,
                afternoon_start=None,
                afternoon_end=None,
                original_total_hours=3.0
            )

            for block in blocks:
                db.session.add(block)
            db.session.commit()

            # Should create exactly one block
            assert len(blocks) == 1, "Should create exactly one block for morning-only entry"

            # Verify block values
            retrieved_entry = db.session.get(TimeEntry, entry_id)
            assert len(retrieved_entry.time_blocks) == 1
            block = retrieved_entry.time_blocks[0]
            assert block.start_time == morning_start
            assert block.end_time == morning_end

            # Cleanup
            db.session.delete(retrieved_entry)
            db.session.delete(group)
            db.session.commit()

    def test_migration_entry_with_only_afternoon_block(self, app):
        """Test migration of entry with only afternoon times.
        
        Requirements: 6.3 - WHEN migrating a TimeEntry with afternoon times,
        THE Time_Tracker SHALL create a TimeBlock with the afternoon_start and afternoon_end values.
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

            # Create entry
            entry = TimeEntry(
                research_group_id=group.id,
                date=date(2025, 1, 1),
                task_description='Afternoon only task',
                total_hours=4.0
            )
            db.session.add(entry)
            db.session.flush()

            entry_id = entry.id
            afternoon_start = time(13, 0)
            afternoon_end = time(17, 0)

            # Run migration with only afternoon data
            blocks = migrate_entry_to_time_blocks(
                entry_id=entry_id,
                morning_start=None,
                morning_end=None,
                afternoon_start=afternoon_start,
                afternoon_end=afternoon_end,
                original_total_hours=4.0
            )

            for block in blocks:
                db.session.add(block)
            db.session.commit()

            # Should create exactly one block
            assert len(blocks) == 1, "Should create exactly one block for afternoon-only entry"

            # Verify block values
            retrieved_entry = db.session.get(TimeEntry, entry_id)
            assert len(retrieved_entry.time_blocks) == 1
            block = retrieved_entry.time_blocks[0]
            assert block.start_time == afternoon_start
            assert block.end_time == afternoon_end

            # Cleanup
            db.session.delete(retrieved_entry)
            db.session.delete(group)
            db.session.commit()

    def test_migration_entry_with_both_blocks(self, app):
        """Test migration of entry with both morning and afternoon times.
        
        Requirements: 6.2, 6.3 - Should create both morning and afternoon TimeBlocks.
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

            # Create entry
            entry = TimeEntry(
                research_group_id=group.id,
                date=date(2025, 1, 1),
                task_description='Full day task',
                total_hours=7.0
            )
            db.session.add(entry)
            db.session.flush()

            entry_id = entry.id
            morning_start = time(9, 0)
            morning_end = time(12, 0)
            afternoon_start = time(13, 0)
            afternoon_end = time(17, 0)

            # Run migration with both blocks
            blocks = migrate_entry_to_time_blocks(
                entry_id=entry_id,
                morning_start=morning_start,
                morning_end=morning_end,
                afternoon_start=afternoon_start,
                afternoon_end=afternoon_end,
                original_total_hours=7.0
            )

            for block in blocks:
                db.session.add(block)
            db.session.commit()

            # Should create exactly two blocks
            assert len(blocks) == 2, "Should create two blocks for full-day entry"

            # Verify block values
            retrieved_entry = db.session.get(TimeEntry, entry_id)
            assert len(retrieved_entry.time_blocks) == 2

            # Find morning and afternoon blocks
            sorted_blocks = sorted(retrieved_entry.time_blocks, key=lambda b: b.start_time)
            assert sorted_blocks[0].start_time == morning_start
            assert sorted_blocks[0].end_time == morning_end
            assert sorted_blocks[1].start_time == afternoon_start
            assert sorted_blocks[1].end_time == afternoon_end

            # Cleanup
            db.session.delete(retrieved_entry)
            db.session.delete(group)
            db.session.commit()

    def test_migration_preserves_total_hours(self, app):
        """Test that migration preserves the original total_hours value.
        
        Requirements: 6.4 - WHEN migration completes, THE Time_Tracker SHALL
        preserve the original total_hours values for all migrated entries.
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

            original_total = 5.5

            # Create entry with specific total_hours
            entry = TimeEntry(
                research_group_id=group.id,
                date=date(2025, 1, 1),
                task_description='Test task',
                total_hours=original_total
            )
            db.session.add(entry)
            db.session.flush()

            entry_id = entry.id

            # Run migration
            blocks = migrate_entry_to_time_blocks(
                entry_id=entry_id,
                morning_start=time(9, 0),
                morning_end=time(12, 30),
                afternoon_start=time(13, 0),
                afternoon_end=time(16, 0),
                original_total_hours=original_total
            )

            for block in blocks:
                db.session.add(block)
            db.session.commit()

            # Verify total_hours is preserved
            retrieved_entry = db.session.get(TimeEntry, entry_id)
            assert retrieved_entry.total_hours == original_total, (
                f"Expected total_hours to be {original_total}, got {retrieved_entry.total_hours}"
            )

            # Cleanup
            db.session.delete(retrieved_entry)
            db.session.delete(group)
            db.session.commit()


class TestRunMigration:
    """Tests for the run_migration batch function."""

    def test_run_migration_multiple_entries(self, app):
        """Test batch migration of multiple entries."""
        with app.app_context():
            # Create a research group
            group = ResearchGroup(
                name='Test Group',
                manager_name='Test Manager',
                project_name='Test Project'
            )
            db.session.add(group)
            db.session.flush()

            # Create multiple entries
            entries = []
            for i in range(3):
                entry = TimeEntry(
                    research_group_id=group.id,
                    date=date(2025, 1, i + 1),
                    task_description=f'Task {i + 1}',
                    total_hours=float(i + 1)
                )
                db.session.add(entry)
                entries.append(entry)
            db.session.flush()

            # Prepare migration data
            entries_data = [
                {
                    'id': entries[0].id,
                    'morning_start': time(9, 0),
                    'morning_end': time(10, 0),
                    'afternoon_start': None,
                    'afternoon_end': None,
                    'total_hours': 1.0
                },
                {
                    'id': entries[1].id,
                    'morning_start': None,
                    'morning_end': None,
                    'afternoon_start': time(13, 0),
                    'afternoon_end': time(15, 0),
                    'total_hours': 2.0
                },
                {
                    'id': entries[2].id,
                    'morning_start': time(9, 0),
                    'morning_end': time(11, 0),
                    'afternoon_start': time(14, 0),
                    'afternoon_end': time(15, 0),
                    'total_hours': 3.0
                }
            ]

            # Run batch migration
            entries_processed, blocks_created = run_migration(entries_data)

            assert entries_processed == 3
            assert blocks_created == 4  # 1 + 1 + 2 blocks

            # Verify each entry
            for i, entry in enumerate(entries):
                retrieved = db.session.get(TimeEntry, entry.id)
                if i == 0:
                    assert len(retrieved.time_blocks) == 1
                elif i == 1:
                    assert len(retrieved.time_blocks) == 1
                else:
                    assert len(retrieved.time_blocks) == 2

            # Cleanup
            for entry in entries:
                db.session.delete(db.session.get(TimeEntry, entry.id))
            db.session.delete(group)
            db.session.commit()

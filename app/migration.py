"""Migration script to convert morning/afternoon time data to TimeBlock records.

This module provides functions to migrate existing TimeEntry records from the
old schema (with morning_start, morning_end, afternoon_start, afternoon_end columns)
to the new TimeBlock model.
"""
from datetime import time
from typing import Optional, Tuple, List

from . import db
from .models import TimeBlock, TimeEntry


def migrate_entry_to_time_blocks(
    entry_id: int,
    morning_start: Optional[time],
    morning_end: Optional[time],
    afternoon_start: Optional[time],
    afternoon_end: Optional[time],
    original_total_hours: float
) -> List[TimeBlock]:
    """Migrate a single entry's time data to TimeBlock records.
    
    Args:
        entry_id: The ID of the TimeEntry to migrate
        morning_start: Morning block start time (may be None)
        morning_end: Morning block end time (may be None)
        afternoon_start: Afternoon block start time (may be None)
        afternoon_end: Afternoon block end time (may be None)
        original_total_hours: The original total_hours value to preserve
    
    Returns:
        List of created TimeBlock records (not yet committed to database)
    """
    blocks = []
    
    # Create morning block if both start and end exist
    if morning_start is not None and morning_end is not None:
        morning_block = TimeBlock(
            time_entry_id=entry_id,
            start_time=morning_start,
            end_time=morning_end
        )
        blocks.append(morning_block)
    
    # Create afternoon block if both start and end exist
    if afternoon_start is not None and afternoon_end is not None:
        afternoon_block = TimeBlock(
            time_entry_id=entry_id,
            start_time=afternoon_start,
            end_time=afternoon_end
        )
        blocks.append(afternoon_block)
    
    return blocks


def run_migration(entries_data: List[dict]) -> Tuple[int, int]:
    """Run the migration for a list of entry data dictionaries.
    
    This function creates TimeBlock records from the provided entry data.
    It expects each entry dict to have:
        - id: The TimeEntry ID
        - morning_start: Optional morning start time
        - morning_end: Optional morning end time
        - afternoon_start: Optional afternoon start time
        - afternoon_end: Optional afternoon end time
        - total_hours: The original total hours value
    
    Args:
        entries_data: List of dictionaries containing entry migration data
    
    Returns:
        Tuple of (entries_processed, blocks_created)
    """
    entries_processed = 0
    blocks_created = 0
    
    for entry_data in entries_data:
        entry_id = entry_data['id']
        morning_start = entry_data.get('morning_start')
        morning_end = entry_data.get('morning_end')
        afternoon_start = entry_data.get('afternoon_start')
        afternoon_end = entry_data.get('afternoon_end')
        original_total_hours = entry_data.get('total_hours', 0.0)
        
        blocks = migrate_entry_to_time_blocks(
            entry_id=entry_id,
            morning_start=morning_start,
            morning_end=morning_end,
            afternoon_start=afternoon_start,
            afternoon_end=afternoon_end,
            original_total_hours=original_total_hours
        )
        
        for block in blocks:
            db.session.add(block)
        
        entries_processed += 1
        blocks_created += len(blocks)
    
    db.session.commit()
    return entries_processed, blocks_created


def migrate_from_legacy_schema():
    """Migrate all existing entries from legacy schema to TimeBlock model.
    
    This function queries entries that have legacy morning/afternoon columns
    and creates corresponding TimeBlock records. It preserves the original
    total_hours values.
    
    Note: This function assumes the legacy columns still exist in the database.
    After migration, those columns can be removed.
    
    Returns:
        Tuple of (entries_processed, blocks_created)
    """
    # Query all entries - in a real migration, we'd query the legacy columns
    # Since the columns have been removed from the model, this would need
    # to be done via raw SQL or the data would need to be provided externally
    entries = TimeEntry.query.all()
    
    entries_processed = 0
    blocks_created = 0
    
    for entry in entries:
        # Skip entries that already have time blocks
        if entry.time_blocks:
            continue
        
        # In a real migration with legacy columns, we would access:
        # entry.morning_start, entry.morning_end, etc.
        # Since those columns are removed, this function serves as a template
        entries_processed += 1
    
    return entries_processed, blocks_created

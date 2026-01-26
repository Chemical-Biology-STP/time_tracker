# Implementation Plan: Time Tracker Enhancements

## Overview

This implementation plan covers adding multiple time blocks per entry and delete functionality to the Flask Time Tracker application. Tasks are ordered to build incrementally, with testing integrated throughout.

## Tasks

- [x] 1. Create TimeBlock model and update TimeEntry
  - [x] 1.1 Create TimeBlock model in app/models.py
    - Add TimeBlock class with id, time_entry_id, start_time, end_time columns
    - Add foreign key constraint with ON DELETE CASCADE
    - Add duration_hours() method to calculate block duration
    - _Requirements: 1.1, 1.2, 4.2_
  
  - [x] 1.2 Update TimeEntry model for time blocks relationship
    - Add time_blocks relationship with backref
    - Update calculate_total_hours() to sum time block durations
    - Add get_sorted_time_blocks() method for chronological ordering
    - Remove morning_start, morning_end, afternoon_start, afternoon_end columns
    - _Requirements: 1.5, 3.3, 4.1_
  
  - [x] 1.3 Write property test for time block validation
    - **Property 1: Time Block Validation**
    - **Validates: Requirements 1.3, 2.5**
  
  - [x] 1.4 Write property test for total hours calculation
    - **Property 5: Total Hours Calculation**
    - **Validates: Requirements 4.1, 4.2, 4.3**

- [x] 2. Update utility functions
  - [x] 2.1 Add new utility functions in app/utils.py
    - Add parse_time_blocks_from_form() to extract multiple blocks from form data
    - Add calculate_total_hours_from_blocks() to sum block durations
    - Update existing validate_time_block() if needed
    - _Requirements: 2.3, 4.1_
  
  - [x] 2.2 Write unit tests for new utility functions
    - Test parse_time_blocks_from_form() with various inputs
    - Test calculate_total_hours_from_blocks() with edge cases
    - _Requirements: 2.3, 4.1_

- [x] 3. Checkpoint - Verify models and utilities
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Update entry creation route and form
  - [x] 4.1 Update entries route for multiple time blocks
    - Modify POST handler to parse multiple time blocks from form
    - Create TimeEntry first, then create associated TimeBlock records
    - Validate at least one complete time block is provided
    - Calculate and store total_hours from all blocks
    - _Requirements: 2.1, 2.3, 2.4, 2.5_
  
  - [x] 4.2 Update entries.html template for dynamic time blocks
    - Replace fixed morning/afternoon inputs with dynamic time block section
    - Add "Add Time Block" button with JavaScript handler
    - Add "Remove" button for each time block (except first)
    - Update form to submit time blocks as indexed arrays
    - _Requirements: 2.1, 2.2_
  
  - [x] 4.3 Write property test for time block retrieval
    - **Property 3: Time Block Retrieval Completeness**
    - **Validates: Requirements 3.1**
  
  - [x] 4.4 Write property test for chronological ordering
    - **Property 4: Time Block Chronological Ordering**
    - **Validates: Requirements 3.3**

- [x] 5. Update entry display
  - [x] 5.1 Update entries.html to display multiple time blocks
    - Modify table to show all time blocks per entry
    - Format times as HH:MM
    - Display blocks in chronological order
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [x] 5.2 Update summary.html for new data model
    - Ensure summary calculations work with new model
    - _Requirements: 4.4_
  
  - [x] 5.3 Write property test for group total hours
    - **Property 6: Group Total Hours Aggregation**
    - **Validates: Requirements 4.4**

- [x] 6. Checkpoint - Verify entry creation and display
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement delete functionality
  - [x] 7.1 Add delete route in app/routes.py
    - Create POST /entries/<entry_id>/delete endpoint
    - Query entry and verify it exists (404 if not)
    - Delete entry (cascade deletes time blocks)
    - Flash success message and redirect to entries list
    - _Requirements: 5.3, 5.5, 5.6_
  
  - [x] 7.2 Add delete button and confirmation to entries.html
    - Add delete button/form for each entry in the table
    - Add JavaScript confirmation dialog before submission
    - Style delete button appropriately (e.g., red/warning color)
    - _Requirements: 5.1, 5.2, 5.4_
  
  - [x] 7.3 Write property test for cascade delete
    - **Property 2: Cascade Delete Integrity**
    - **Validates: Requirements 1.4, 5.3**
  
  - [x] 7.4 Write property test for group total update on deletion
    - **Property 7: Group Total Update on Entry Deletion**
    - **Validates: Requirements 5.5**

- [x] 8. Checkpoint - Verify delete functionality
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Create data migration
  - [x] 9.1 Create migration script for existing data
    - Write migration function to convert morning/afternoon data to TimeBlock records
    - Handle entries with morning only, afternoon only, both, or neither
    - Preserve original total_hours values
    - Add migration to app initialization or as standalone script
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [x] 9.2 Write property test for migration data preservation
    - **Property 8: Migration Data Preservation**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
  
  - [x] 9.3 Write unit tests for migration edge cases
    - Test migration of entry with no time data
    - Test migration of entry with only morning block
    - Test migration of entry with only afternoon block
    - _Requirements: 6.5_

- [x] 10. Final checkpoint - Full integration verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks including tests are required for comprehensive coverage
- Each task references specific requirements for traceability
- Property tests use hypothesis library (already in project)
- Migration should be run once after deploying the new schema
- The existing test_utils.py tests may need updates after removing morning/afternoon calculation functions

# Requirements Document

## Introduction

This document specifies requirements for enhancing the Flask Time Tracker application with two new features: support for multiple time blocks per entry (replacing the fixed morning/afternoon structure) and the ability to delete time entries. These enhancements will provide users with greater flexibility in tracking their work hours and managing their time entry data.

## Glossary

- **Time_Tracker**: The Flask web application for tracking work hours across research groups
- **Time_Entry**: A record of work performed on a specific date, containing a task description and one or more time blocks
- **Time_Block**: A continuous period of work defined by a start time and end time
- **Research_Group**: An organizational unit that contains multiple time entries
- **Entry_Form**: The web form used to create new time entries with associated time blocks
- **Delete_Confirmation**: A user interface element that requires explicit user confirmation before permanently removing data

## Requirements

### Requirement 1: Multiple Time Blocks Data Model

**User Story:** As a developer, I want to store time blocks in a separate database table, so that each time entry can have a flexible number of time blocks.

#### Acceptance Criteria

1. THE Time_Tracker SHALL store time blocks in a dedicated TimeBlock table with a foreign key reference to TimeEntry
2. WHEN a TimeBlock is created, THE Time_Tracker SHALL require a valid start_time, end_time, and time_entry_id
3. THE Time_Tracker SHALL enforce that TimeBlock end_time is after start_time at the database constraint level
4. WHEN a TimeEntry is deleted, THE Time_Tracker SHALL cascade delete all associated TimeBlock records
5. THE Time_Tracker SHALL remove the morning_start, morning_end, afternoon_start, and afternoon_end columns from the TimeEntry model

### Requirement 2: Time Block Creation

**User Story:** As a user, I want to add multiple time blocks when creating a time entry, so that I can accurately track non-contiguous work periods throughout the day.

#### Acceptance Criteria

1. WHEN a user creates a time entry, THE Entry_Form SHALL allow adding at least one time block
2. WHEN a user clicks an "Add Time Block" button, THE Entry_Form SHALL dynamically add a new time block input row
3. WHEN a user submits the entry form, THE Time_Tracker SHALL validate that at least one complete time block is provided
4. WHEN a user submits the entry form with invalid time blocks, THE Time_Tracker SHALL display an error message and preserve the form data
5. IF a time block has end_time before or equal to start_time, THEN THE Time_Tracker SHALL reject the submission with a descriptive error

### Requirement 3: Time Block Display

**User Story:** As a user, I want to see all time blocks for each entry, so that I can review my work schedule accurately.

#### Acceptance Criteria

1. WHEN displaying a time entry, THE Time_Tracker SHALL show all associated time blocks with their start and end times
2. WHEN displaying time blocks, THE Time_Tracker SHALL format times in HH:MM format
3. WHEN a time entry has multiple time blocks, THE Time_Tracker SHALL display them in chronological order by start time

### Requirement 4: Total Hours Calculation

**User Story:** As a user, I want the total hours to be calculated from all my time blocks, so that my pay is computed correctly.

#### Acceptance Criteria

1. WHEN calculating total hours for a TimeEntry, THE Time_Tracker SHALL sum the duration of all associated TimeBlock records
2. THE Time_Tracker SHALL calculate each TimeBlock duration as (end_time - start_time) in hours
3. WHEN a TimeEntry total_hours is requested, THE Time_Tracker SHALL return the sum rounded to two decimal places
4. WHEN calculating total hours for a ResearchGroup, THE Time_Tracker SHALL sum the total_hours of all associated TimeEntry records

### Requirement 5: Delete Time Entry

**User Story:** As a user, I want to delete time entries I've created, so that I can remove incorrect or duplicate entries.

#### Acceptance Criteria

1. WHEN viewing time entries, THE Time_Tracker SHALL display a delete button for each entry
2. WHEN a user clicks the delete button, THE Delete_Confirmation SHALL prompt the user to confirm the deletion
3. WHEN a user confirms deletion, THE Time_Tracker SHALL permanently remove the TimeEntry and all associated TimeBlock records
4. WHEN a user cancels deletion, THE Time_Tracker SHALL preserve the TimeEntry unchanged
5. WHEN a TimeEntry is deleted, THE Time_Tracker SHALL update the ResearchGroup total hours automatically
6. WHEN deletion is successful, THE Time_Tracker SHALL display a success message and redirect to the entries list

### Requirement 6: Data Migration

**User Story:** As a developer, I want to migrate existing time entries to the new data model, so that no historical data is lost.

#### Acceptance Criteria

1. WHEN the migration runs, THE Time_Tracker SHALL create TimeBlock records from existing morning and afternoon time data
2. WHEN migrating a TimeEntry with morning times, THE Time_Tracker SHALL create a TimeBlock with the morning_start and morning_end values
3. WHEN migrating a TimeEntry with afternoon times, THE Time_Tracker SHALL create a TimeBlock with the afternoon_start and afternoon_end values
4. WHEN migration completes, THE Time_Tracker SHALL preserve the original total_hours values for all migrated entries
5. IF a TimeEntry has no morning or afternoon times, THEN THE Time_Tracker SHALL skip TimeBlock creation for that entry

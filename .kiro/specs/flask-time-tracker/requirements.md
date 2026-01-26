# Requirements Document

## Introduction

A minimal Flask web application to replace Excel-based time tracking for research groups. The system allows employees to log time entries with task descriptions, supports two time blocks per day (morning/afternoon sessions), and calculates total hours and pay automatically.

## Glossary

- **Time_Tracker**: The Flask web application system
- **Research_Group**: A project or team that employees track time against (equivalent to Excel sheets)
- **Time_Entry**: A single day's work record containing date, task, and up to two time blocks
- **Time_Block**: A start/end time pair representing a work session
- **Employee**: A user who logs time entries

## Requirements

### Requirement 1: Research Group Management

**User Story:** As an employee, I want to create and view research groups, so that I can organize my time entries by project.

#### Acceptance Criteria

1. WHEN an employee submits a new research group with name, manager name, and project name, THEN THE Time_Tracker SHALL create the research group and display it in the list
2. WHEN an employee views the research groups page, THEN THE Time_Tracker SHALL display all research groups with their names and associated project names
3. IF an employee attempts to create a research group with an empty name, THEN THE Time_Tracker SHALL reject the submission and display a validation error

### Requirement 2: Time Entry Logging

**User Story:** As an employee, I want to log time entries with task descriptions and time blocks, so that I can track my work hours.

#### Acceptance Criteria

1. WHEN an employee submits a time entry with date, task description, and at least one time block, THEN THE Time_Tracker SHALL save the entry and associate it with the selected research group
2. WHEN an employee enters two time blocks for a single entry, THEN THE Time_Tracker SHALL store both blocks and calculate the combined total hours
3. WHEN an employee submits a time entry with only one time block, THEN THE Time_Tracker SHALL accept the entry with the second block as empty
4. IF an employee submits a time entry with end time before start time, THEN THE Time_Tracker SHALL reject the submission and display a validation error
5. IF an employee submits a time entry with an empty task description, THEN THE Time_Tracker SHALL reject the submission and display a validation error

### Requirement 3: Hours Calculation

**User Story:** As an employee, I want automatic calculation of total hours, so that I don't have to manually compute my work time.

#### Acceptance Criteria

1. WHEN a time entry is saved, THEN THE Time_Tracker SHALL calculate total hours as the sum of both time blocks' durations
2. WHEN displaying a time entry, THEN THE Time_Tracker SHALL show the calculated total hours rounded to two decimal places
3. THE Time_Tracker SHALL calculate duration for each time block as (end_time - start_time) in hours

### Requirement 4: View and Filter Entries

**User Story:** As an employee, I want to view and filter my time entries by research group, so that I can review my logged hours.

#### Acceptance Criteria

1. WHEN an employee selects a research group, THEN THE Time_Tracker SHALL display all time entries for that group ordered by date descending
2. WHEN displaying time entries, THEN THE Time_Tracker SHALL show date, task description, time blocks, and total hours for each entry
3. WHEN an employee views a research group with no entries, THEN THE Time_Tracker SHALL display an empty state message

### Requirement 5: Summary and Pay Calculation

**User Story:** As an employee, I want to see a summary of total hours and calculated pay, so that I can track my earnings.

#### Acceptance Criteria

1. WHEN an employee views a research group summary, THEN THE Time_Tracker SHALL display the sum of all total hours for that group
2. WHEN displaying the summary, THEN THE Time_Tracker SHALL calculate total pay as (total_hours * rate_per_hour) using the default rate of 107.93
3. WHEN displaying the summary, THEN THE Time_Tracker SHALL show total hours and total pay formatted to two decimal places

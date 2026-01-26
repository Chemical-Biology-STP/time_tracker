# Requirements Document

## Introduction

A native macOS menu bar companion application for the existing Flask time tracker. The app runs in the background and prompts users every 30 minutes to log what they're working on, making time tracking seamless and reducing the friction of manually opening the web interface. The app integrates with the existing Flask backend to create time entries.

## Glossary

- **Companion_App**: The native macOS menu bar application
- **Flask_Backend**: The existing Flask time tracker web application running locally
- **Prompt_Dialog**: A native macOS dialog that asks the user what they're working on
- **Menu_Bar_Icon**: The system tray icon that provides quick access to app controls
- **Time_Entry**: A work record containing date, task description, and time blocks (stored in Flask backend)
- **Research_Group**: A project or team that time entries are logged against
- **Prompt_Interval**: The configurable time period between prompts (default 30 minutes)

## Requirements

### Requirement 1: Menu Bar Application

**User Story:** As a user, I want the companion app to run as a menu bar application, so that it stays out of my way while remaining easily accessible.

#### Acceptance Criteria

1. WHEN the Companion_App launches, THE Companion_App SHALL display an icon in the macOS menu bar
2. WHEN the user clicks the Menu_Bar_Icon, THE Companion_App SHALL display a dropdown menu with app controls
3. WHEN the user selects "Quit" from the menu, THE Companion_App SHALL terminate gracefully
4. THE Companion_App SHALL run without displaying a Dock icon
5. WHEN macOS starts and the app is configured for login launch, THE Companion_App SHALL start automatically

### Requirement 2: Periodic Time Prompts

**User Story:** As a user, I want to be prompted every 30 minutes to log what I'm working on, so that I can track my time without having to remember to do it manually.

#### Acceptance Criteria

1. WHILE the Companion_App is running, THE Companion_App SHALL display a Prompt_Dialog every 30 minutes by default
2. WHEN the Prompt_Dialog appears, THE Companion_App SHALL display a text field for task description and a dropdown to select a Research_Group
3. WHEN the user submits the Prompt_Dialog with a task description and selected group, THE Companion_App SHALL create a time entry in the Flask_Backend
4. WHEN the user dismisses the Prompt_Dialog without submitting, THE Companion_App SHALL not create a time entry and wait for the next interval
5. WHEN a time entry is successfully created, THE Companion_App SHALL display a brief confirmation notification

### Requirement 3: Flask Backend Integration

**User Story:** As a user, I want the companion app to integrate with my existing Flask time tracker, so that all my time entries are stored in one place.

#### Acceptance Criteria

1. WHEN the Companion_App starts, THE Companion_App SHALL attempt to connect to the Flask_Backend at the configured URL
2. WHEN fetching research groups, THE Companion_App SHALL retrieve the list of available Research_Groups from the Flask_Backend
3. WHEN creating a time entry, THE Companion_App SHALL send the task description, current date, and time block to the Flask_Backend
4. IF the Flask_Backend is unreachable, THEN THE Companion_App SHALL display an error notification and retry on the next prompt
5. WHEN creating a time entry, THE Companion_App SHALL use the current time as the end time and calculate the start time based on the Prompt_Interval

### Requirement 4: Configuration Settings

**User Story:** As a user, I want to configure the prompt interval and backend URL, so that I can customize the app to my workflow.

#### Acceptance Criteria

1. WHEN the user opens settings from the menu, THE Companion_App SHALL display a settings window
2. WHEN the user changes the Prompt_Interval, THE Companion_App SHALL update the timer to use the new interval
3. WHEN the user changes the Flask_Backend URL, THE Companion_App SHALL use the new URL for subsequent API calls
4. WHEN settings are changed, THE Companion_App SHALL persist them across app restarts
5. THE Companion_App SHALL provide a default Prompt_Interval of 30 minutes and default backend URL of http://localhost:5000

### Requirement 5: Quick Actions

**User Story:** As a user, I want quick access to common actions from the menu bar, so that I can log time or check status without waiting for a prompt.

#### Acceptance Criteria

1. WHEN the user selects "Log Time Now" from the menu, THE Companion_App SHALL immediately display the Prompt_Dialog
2. WHEN the user selects "Skip Next Prompt" from the menu, THE Companion_App SHALL skip the next scheduled prompt and resume normal scheduling after
3. WHEN the user hovers over the Menu_Bar_Icon, THE Companion_App SHALL display a tooltip showing time until next prompt
4. WHEN the menu is displayed, THE Companion_App SHALL show the currently selected Research_Group as the default

### Requirement 6: Error Handling and Resilience

**User Story:** As a user, I want the app to handle errors gracefully, so that temporary issues don't disrupt my workflow.

#### Acceptance Criteria

1. IF the Flask_Backend returns an error when creating a time entry, THEN THE Companion_App SHALL display an error notification with the failure reason
2. IF the Flask_Backend is unreachable for more than 3 consecutive prompts, THEN THE Companion_App SHALL display a persistent warning in the menu
3. WHEN the Flask_Backend becomes reachable again, THE Companion_App SHALL clear any connection warning indicators
4. IF an error occurs during app startup, THEN THE Companion_App SHALL log the error and display a user-friendly message

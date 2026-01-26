# Implementation Plan: macOS Companion App

## Overview

This implementation plan covers both the Flask API extension and the native macOS SwiftUI companion app. The Flask API is implemented first to enable testing of the macOS app against a working backend.

Francis Crick 2025!## Tasks

- [x] 1. Add REST API to Flask backend
  - [x] 1.1 Create API blueprint with health check endpoint
    - Create `app/api.py` with Blueprint and `/api/health` endpoint
    - Register blueprint in `app/__init__.py`
    - _Requirements: 3.1_
  
  - [x] 1.2 Implement GET /api/groups endpoint
    - Return all research groups as JSON array
    - Include id, name, manager_name, project_name fields
    - _Requirements: 3.2_
  
  - [x] 1.3 Implement POST /api/entries endpoint
    - Accept JSON with research_group_id, task_description, date, start_time, end_time
    - Create TimeEntry and TimeBlock records
    - Return created entry as JSON
    - _Requirements: 2.3, 3.3_
  
  - [x] 1.4 Write unit tests for API endpoints
    - Test GET /api/groups returns correct format
    - Test POST /api/entries creates records
    - Test validation errors return 400
    - _Requirements: 3.2, 3.3_

- [x] 2. Checkpoint - Flask API complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Create macOS app project structure
  - [x] 3.1 Initialize Xcode project with SwiftUI lifecycle
    - Create TimeTrackerCompanion project
    - Configure Info.plist with LSUIElement = true (no Dock icon)
    - Set deployment target to macOS 13.0+
    - _Requirements: 1.1, 1.4_
  
  - [x] 3.2 Create data models
    - Create `Models/ResearchGroup.swift` with Codable struct
    - Create `Models/TimeEntryRequest.swift` for API requests
    - Create `Models/TimeEntryResponse.swift` for API responses
    - _Requirements: 3.2, 3.3_

- [x] 4. Implement core services
  - [x] 4.1 Implement SettingsManager
    - Create `Services/SettingsManager.swift`
    - Store/retrieve promptIntervalMinutes, backendURL, defaultGroupId, launchAtLogin
    - Use UserDefaults for persistence
    - Set defaults: 30 minutes interval, http://localhost:5000
    - _Requirements: 4.4, 4.5_
  
  - [x] 4.2 Write property test for settings persistence
    - **Property 9: Settings persistence round-trip**
    - **Validates: Requirements 4.4**
  
  - [x] 4.3 Implement APIClient
    - Create `Services/APIClient.swift`
    - Implement fetchGroups() async method
    - Implement createEntry() async method
    - Implement healthCheck() async method
    - Track consecutiveFailures and isConnected state
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [x] 4.4 Write property test for connection state tracking
    - **Property 12: Connection state tracking**
    - **Validates: Requirements 6.2, 6.3**
  
  - [x] 4.5 Implement PromptManager
    - Create `Services/PromptManager.swift`
    - Implement timer scheduling with configurable interval
    - Implement triggerPromptNow() for manual triggers
    - Implement skipNext() functionality
    - Track timeUntilNextPrompt for tooltip display
    - _Requirements: 2.1, 5.1, 5.2_
  
  - [x] 4.6 Write property test for time block calculation
    - **Property 6: Time block calculation**
    - **Validates: Requirements 3.5**

- [x] 5. Checkpoint - Core services complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement UI views
  - [x] 6.1 Create MenuContentView
    - Create `Views/MenuContentView.swift`
    - Display "Log Time Now" button
    - Display "Skip Next Prompt" button
    - Show time until next prompt
    - Show connection status indicator
    - Display currently selected group
    - Add Settings and Quit menu items
    - _Requirements: 1.2, 5.1, 5.2, 5.3, 5.4, 6.2_
  
  - [x] 6.2 Create PromptView
    - Create `Views/PromptView.swift`
    - Text field for task description
    - Dropdown picker for research group selection
    - Submit and Cancel buttons
    - Show loading state during API call
    - _Requirements: 2.2, 2.3, 2.4_
  
  - [x] 6.3 Create SettingsView
    - Create `Views/SettingsView.swift`
    - Prompt interval picker (15, 30, 45, 60 minutes)
    - Backend URL text field
    - Default research group picker
    - Launch at login toggle
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 7. Wire up app entry point
  - [x] 7.1 Implement TimeTrackerCompanionApp
    - Create MenuBarExtra with clock icon
    - Use .menuBarExtraStyle(.window)
    - Initialize and inject PromptManager, SettingsManager, APIClient
    - Add Settings scene
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [x] 7.2 Connect prompt flow
    - Show PromptView when promptManager.showPrompt is true
    - On submit: call APIClient.createEntry(), show notification, dismiss
    - On cancel: dismiss without API call
    - Handle errors with notification
    - _Requirements: 2.3, 2.4, 2.5, 6.1_
  
  - [x] 7.3 Implement startup behavior
    - Fetch research groups on app launch
    - Start prompt timer with configured interval
    - Perform initial health check
    - _Requirements: 1.5, 3.1_

- [x] 8. Implement notifications
  - [x] 8.1 Add notification support
    - Request notification permissions
    - Show success notification after entry creation
    - Show error notifications for failures
    - _Requirements: 2.5, 6.1, 6.4_

- [x] 9. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - Verify menu bar app launches correctly
  - Test prompt flow end-to-end with Flask backend

## Notes

- The Flask API must be running for the macOS app to function
- macOS 13+ is required for MenuBarExtra API
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases

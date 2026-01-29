// PromptView.swift
// TimeTrackerCompanion
//
// Time logging prompt dialog view
// Requirements: 2.2, 2.3, 2.4

import SwiftUI

struct PromptView: View {
    @EnvironmentObject var promptManager: PromptManager
    @EnvironmentObject var settingsManager: SettingsManager
    @EnvironmentObject var apiClient: APIClient
    @EnvironmentObject var notificationManager: NotificationManager
    
    @State private var taskDescription: String = ""
    @State private var selectedGroupId: Int?
    @State private var groups: [ResearchGroup] = []
    @State private var isLoading: Bool = false
    @State private var errorMessage: String?
    @State private var isLoadingGroups: Bool = true
    @State private var startTime: Date = Date()
    @State private var endTime: Date = Date()
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Header
            Text("What are you working on?")
                .font(.headline)
            
            // Task description text field - Requirements: 2.2
            VStack(alignment: .leading, spacing: 4) {
                Text("Task Description")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                TextField("Enter what you've been working on...", text: $taskDescription, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(3...5)
            }
            
            // Research group picker - Requirements: 2.2
            VStack(alignment: .leading, spacing: 4) {
                Text("Research Group")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                if isLoadingGroups {
                    HStack {
                        ProgressView()
                            .scaleEffect(0.7)
                        Text("Loading groups...")
                            .foregroundColor(.secondary)
                    }
                } else if groups.isEmpty {
                    Text("No groups available")
                        .foregroundColor(.red)
                } else {
                    Picker("Select Group", selection: $selectedGroupId) {
                        Text("Select a group").tag(nil as Int?)
                        ForEach(groups) { group in
                            Text(group.name).tag(group.id as Int?)
                        }
                    }
                    .pickerStyle(.menu)
                }
            }
            
            // Time pickers
            HStack(spacing: 16) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Start Time")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    DatePicker("", selection: $startTime, displayedComponents: .hourAndMinute)
                        .labelsHidden()
                }
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("End Time")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    DatePicker("", selection: $endTime, displayedComponents: .hourAndMinute)
                        .labelsHidden()
                }
            }
            
            // Error message display
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
            }
            
            Divider()
            
            // Action buttons - Requirements: 2.3, 2.4
            HStack {
                // Cancel button - Requirements: 2.4
                Button("Cancel") {
                    promptManager.dismissPrompt()
                }
                .keyboardShortcut(.escape, modifiers: [])
                
                Spacer()
                
                // Submit button - Requirements: 2.3
                Button(action: submitEntry) {
                    if isLoading {
                        ProgressView()
                            .scaleEffect(0.7)
                    } else {
                        Text("Submit")
                    }
                }
                .keyboardShortcut(.return, modifiers: [])
                .disabled(!canSubmit || isLoading)
                .buttonStyle(.borderedProminent)
            }
        }
        .padding()
        .frame(width: 350)
        .onAppear {
            resetForm()
            Task {
                await loadGroups()
            }
        }
        .onChange(of: promptManager.showPrompt) { isShowing in
            if isShowing {
                resetForm()
            }
        }
    }
    
    private func resetForm() {
        // Reset time pickers to current time
        endTime = Date()
        startTime = endTime.addingTimeInterval(-TimeInterval(settingsManager.promptIntervalMinutes * 60))
        // Clear previous task description
        taskDescription = ""
        errorMessage = nil
        // Restore default group selection
        if let defaultId = settingsManager.defaultGroupId,
           groups.contains(where: { $0.id == defaultId }) {
            selectedGroupId = defaultId
        }
    }
    
    private var canSubmit: Bool {
        !taskDescription.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
        selectedGroupId != nil
    }
    
    private func loadGroups() async {
        isLoadingGroups = true
        do {
            groups = try await apiClient.fetchGroups()
            // Set default group if configured
            if let defaultId = settingsManager.defaultGroupId,
               groups.contains(where: { $0.id == defaultId }) {
                selectedGroupId = defaultId
            }
        } catch {
            errorMessage = "Failed to load groups: \(error.localizedDescription)"
        }
        isLoadingGroups = false
    }
    
    /// Submit the time entry - Requirements: 2.3, 2.5, 6.1
    private func submitEntry() {
        guard let groupId = selectedGroupId else { return }
        
        isLoading = true
        errorMessage = nil
        
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        
        let timeFormatter = DateFormatter()
        timeFormatter.dateFormat = "HH:mm"
        
        let request = TimeEntryRequest(
            research_group_id: groupId,
            task_description: taskDescription.trimmingCharacters(in: .whitespacesAndNewlines),
            date: dateFormatter.string(from: Date()),
            start_time: timeFormatter.string(from: startTime),
            end_time: timeFormatter.string(from: endTime)
        )
        
        Task {
            do {
                let response = try await apiClient.createEntry(request)
                await MainActor.run {
                    isLoading = false
                    promptManager.dismissPrompt()
                }
                // Show success notification - Requirements: 2.5
                await notificationManager.showEntryCreatedNotification(
                    hours: response.total_hours,
                    taskDescription: response.task_description
                )
            } catch {
                await MainActor.run {
                    errorMessage = "Failed to save entry: \(error.localizedDescription)"
                    isLoading = false
                }
                // Show error notification - Requirements: 6.1
                await notificationManager.showEntryErrorNotification(error: error)
            }
        }
    }
}

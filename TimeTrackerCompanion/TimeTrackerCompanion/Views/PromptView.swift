// PromptView.swift
// TimeTrackerCompanion
//
// Time logging prompt dialog view

import SwiftUI

struct PromptView: View {
    @EnvironmentObject var promptManager: PromptManager
    @EnvironmentObject var settingsManager: SettingsManager
    @EnvironmentObject var apiClient: APIClient
    @EnvironmentObject var notificationManager: NotificationManager
    
    @State private var taskDescription: String = ""
    @State private var selectedGroupId: Int?
    @State private var selectedProjectId: Int?
    @State private var groups: [ResearchGroup] = []
    @State private var projects: [Project] = []
    @State private var isLoading: Bool = false
    @State private var errorMessage: String?
    @State private var isLoadingGroups: Bool = true
    @State private var isLoadingProjects: Bool = false
    @State private var startTime: Date = Date()
    @State private var endTime: Date = Date()
    @State private var selectedDate: Date = Date()
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("What are you working on?")
                .font(.headline)
            
            // Task description
            VStack(alignment: .leading, spacing: 4) {
                Text("Task Description")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                TextField("Enter what you've been working on...", text: $taskDescription, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(3...5)
            }
            
            // Research group picker
            VStack(alignment: .leading, spacing: 4) {
                Text("Research Group")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                if isLoadingGroups {
                    HStack {
                        ProgressView().scaleEffect(0.7)
                        Text("Loading groups...").foregroundColor(.secondary)
                    }
                } else if groups.isEmpty {
                    Text("No groups available").foregroundColor(.red)
                } else {
                    Picker("Select Group", selection: $selectedGroupId) {
                        Text("Select a group").tag(nil as Int?)
                        ForEach(groups) { group in
                            Text(group.name).tag(group.id as Int?)
                        }
                    }
                    .pickerStyle(.menu)
                    .onChange(of: selectedGroupId) { newGroupId in
                        selectedProjectId = nil
                        if let gid = newGroupId {
                            Task { await loadProjects(groupId: gid) }
                        } else {
                            projects = []
                        }
                    }
                }
            }
            
            // Project picker
            if selectedGroupId != nil {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Project")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    if isLoadingProjects {
                        HStack {
                            ProgressView().scaleEffect(0.7)
                            Text("Loading projects...").foregroundColor(.secondary)
                        }
                    } else {
                        Picker("Select Project", selection: $selectedProjectId) {
                            Text("None").tag(nil as Int?)
                            ForEach(projects) { project in
                                Text(project.name).tag(project.id as Int?)
                            }
                        }
                        .pickerStyle(.menu)
                    }
                }
            }
            
            // Date picker
            VStack(alignment: .leading, spacing: 4) {
                Text("Date")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                DatePicker("", selection: $selectedDate, displayedComponents: .date)
                    .labelsHidden()
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
            
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
            }
            
            Divider()
            
            HStack {
                Button("Cancel") {
                    promptManager.dismissPrompt()
                }
                .keyboardShortcut(.escape, modifiers: [])
                
                Spacer()
                
                Button(action: submitEntry) {
                    if isLoading {
                        ProgressView().scaleEffect(0.7)
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
            Task { await loadGroups() }
        }
        .onChange(of: promptManager.showPrompt) { isShowing in
            if isShowing {
                resetForm()
                Task { await loadGroups() }
            }
        }
    }
    
    private func resetForm() {
        selectedDate = Date()
        endTime = Date()
        startTime = endTime.addingTimeInterval(-TimeInterval(settingsManager.promptIntervalMinutes * 60))
        taskDescription = ""
        errorMessage = nil
        selectedProjectId = nil
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
            if let defaultId = settingsManager.defaultGroupId,
               groups.contains(where: { $0.id == defaultId }) {
                selectedGroupId = defaultId
                await loadProjects(groupId: defaultId)
            }
        } catch {
            errorMessage = "Failed to load groups: \(error.localizedDescription)"
        }
        isLoadingGroups = false
    }
    
    private func loadProjects(groupId: Int) async {
        isLoadingProjects = true
        do {
            projects = try await apiClient.fetchProjects(groupId: groupId)
        } catch {
            projects = []
        }
        isLoadingProjects = false
    }
    
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
            project_id: selectedProjectId,
            task_description: taskDescription.trimmingCharacters(in: .whitespacesAndNewlines),
            date: dateFormatter.string(from: selectedDate),
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
                await notificationManager.showEntryCreatedNotification(
                    hours: response.total_hours,
                    taskDescription: response.task_description
                )
            } catch {
                await MainActor.run {
                    errorMessage = "Failed to save entry: \(error.localizedDescription)"
                    isLoading = false
                }
                await notificationManager.showEntryErrorNotification(error: error)
            }
        }
    }
}

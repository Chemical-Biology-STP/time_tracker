// SettingsView.swift
// TimeTrackerCompanion
//
// Configuration settings view
// Requirements: 4.1, 4.2, 4.3

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var settingsManager: SettingsManager
    @EnvironmentObject var apiClient: APIClient
    @EnvironmentObject var promptManager: PromptManager
    
    @State private var groups: [ResearchGroup] = []
    @State private var isLoadingGroups: Bool = false
    @State private var connectionStatus: String = "Checking..."
    @State private var showingNewGroupSheet: Bool = false
    @State private var showingNewProjectSheet: Bool = false
    @State private var projectsForSelectedGroup: [Project] = []
    @State private var selectedGroupForProjects: Int?
    
    // Available prompt intervals in minutes
    private let intervalOptions = [15, 30, 45, 60]
    
    var body: some View {
        Form {
            // Prompt Interval Section - Requirements: 4.1, 4.2
            Section {
                Picker("Prompt Interval", selection: $settingsManager.promptIntervalMinutes) {
                    ForEach(intervalOptions, id: \.self) { minutes in
                        Text("\(minutes) minutes").tag(minutes)
                    }
                }
                .pickerStyle(.segmented)
            } header: {
                Text("Timing")
            } footer: {
                Text("How often you'll be prompted to log your time.")
            }
            
            // Working Hours Section
            Section {
                Toggle("Only prompt during working hours", isOn: $settingsManager.workingHoursEnabled)
                
                if settingsManager.workingHoursEnabled {
                    // Working days
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Working Days")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                        HStack(spacing: 8) {
                            ForEach([(1, "Sun"), (2, "Mon"), (3, "Tue"), (4, "Wed"), (5, "Thu"), (6, "Fri"), (7, "Sat")], id: \.0) { day, name in
                                Button(action: {
                                    settingsManager.toggleWorkingDay(day)
                                }) {
                                    Text(name)
                                        .font(.caption)
                                        .frame(width: 36, height: 28)
                                        .background(settingsManager.workingDays.contains(day) ? Color.accentColor : Color.gray.opacity(0.2))
                                        .foregroundColor(settingsManager.workingDays.contains(day) ? .white : .primary)
                                        .cornerRadius(4)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                    
                    HStack {
                        Text("Start:")
                        Picker(String(format: "%02d", settingsManager.workStartHour), selection: $settingsManager.workStartHour) {
                            ForEach(0..<24, id: \.self) { hour in
                                Text(String(format: "%02d", hour)).tag(hour)
                            }
                        }
                        .frame(width: 60)
                        Text(":")
                        Picker(String(format: "%02d", settingsManager.workStartMinute), selection: $settingsManager.workStartMinute) {
                            ForEach([0, 15, 30, 45], id: \.self) { minute in
                                Text(String(format: "%02d", minute)).tag(minute)
                            }
                        }
                        .frame(width: 60)
                        
                        Spacer()
                        
                        Text("End:")
                        Picker(String(format: "%02d", settingsManager.workEndHour), selection: $settingsManager.workEndHour) {
                            ForEach(0..<24, id: \.self) { hour in
                                Text(String(format: "%02d", hour)).tag(hour)
                            }
                        }
                        .frame(width: 60)
                        Text(":")
                        Picker(String(format: "%02d", settingsManager.workEndMinute), selection: $settingsManager.workEndMinute) {
                            ForEach([0, 15, 30, 45], id: \.self) { minute in
                                Text(String(format: "%02d", minute)).tag(minute)
                            }
                        }
                        .frame(width: 60)
                    }
                }
            } header: {
                Text("Working Hours")
            } footer: {
                Text("Prompts will be suppressed outside these hours and days.")
            }
            
            // Hourly Rate Section
            Section {
                HStack {
                    Text("£")
                    TextField("Hourly Rate", value: $settingsManager.hourlyRate, format: .number.precision(.fractionLength(2)))
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 100)
                    Text("per hour")
                        .foregroundColor(.secondary)
                }
            } header: {
                Text("Pay Rate")
            } footer: {
                Text("Used for calculating total pay in CSV exports.")
            }
            
            // Backend URL Section - Requirements: 4.3
            Section {
                TextField("Backend URL", text: $settingsManager.backendURL)
                    .textFieldStyle(.roundedBorder)
                
                HStack {
                    Text("Status:")
                        .foregroundColor(.secondary)
                    Text(connectionStatus)
                        .foregroundColor(connectionStatus == "Connected" ? .green : .red)
                    Spacer()
                    Button("Test Connection") {
                        Task {
                            await testConnection()
                        }
                    }
                    .buttonStyle(.bordered)
                }
                
                Button("Open Web App") {
                    if let url = URL(string: settingsManager.backendURL) {
                        NSWorkspace.shared.open(url)
                    }
                }
                .buttonStyle(.bordered)
            } header: {
                Text("Server")
            } footer: {
                Text("URL of your Flask time tracker backend.")
            }

            // Default Research Group Section
            Section {
                if isLoadingGroups {
                    HStack {
                        ProgressView().scaleEffect(0.7)
                        Text("Loading groups...").foregroundColor(.secondary)
                    }
                } else if groups.isEmpty {
                    HStack {
                        Text("No groups available").foregroundColor(.secondary)
                        Spacer()
                        Button("Refresh") { Task { await loadGroups() } }
                            .buttonStyle(.bordered)
                    }
                } else {
                    Picker("Default Group", selection: $settingsManager.defaultGroupId) {
                        Text("None").tag(nil as Int?)
                        ForEach(groups) { group in
                            Text(group.name).tag(group.id as Int?)
                        }
                    }
                    
                    ForEach(groups) { group in
                        HStack {
                            VStack(alignment: .leading) {
                                Text(group.name).font(.body)
                                if !group.project_name.isEmpty {
                                    Text(group.project_name).font(.caption).foregroundColor(.secondary)
                                }
                            }
                            Spacer()
                            Button(role: .destructive) {
                                Task { await deleteGroup(group) }
                            } label: {
                                Image(systemName: "trash").foregroundColor(.red)
                            }
                            .buttonStyle(.borderless)
                        }
                    }
                }
                
                HStack {
                    Spacer()
                    Button("New Group...") { showingNewGroupSheet = true }
                        .buttonStyle(.bordered)
                }
            } header: {
                Text("Research Groups")
            } footer: {
                Text("Pre-selected group when logging time.")
            }
            
            // Projects Section
            Section {
                if groups.isEmpty {
                    Text("Create a research group first").foregroundColor(.secondary)
                } else {
                    Picker("Group", selection: $selectedGroupForProjects) {
                        Text("Select a group").tag(nil as Int?)
                        ForEach(groups) { group in
                            Text(group.name).tag(group.id as Int?)
                        }
                    }
                    .onChange(of: selectedGroupForProjects) { newGroupId in
                        if let gid = newGroupId {
                            Task { await loadProjects(groupId: gid) }
                        } else {
                            projectsForSelectedGroup = []
                        }
                    }
                    
                    if selectedGroupForProjects != nil {
                        if projectsForSelectedGroup.isEmpty {
                            Text("No projects yet").foregroundColor(.secondary)
                        } else {
                            ForEach(projectsForSelectedGroup) { project in
                                HStack {
                                    VStack(alignment: .leading) {
                                        Text(project.name).font(.body)
                                        if project.archived {
                                            Text("Archived").font(.caption).foregroundColor(.orange)
                                        }
                                    }
                                    Spacer()
                                    Button {
                                        Task {
                                            let _ = try? await apiClient.archiveProject(
                                                projectId: project.id,
                                                archived: !project.archived
                                            )
                                            if let gid = selectedGroupForProjects {
                                                await loadProjects(groupId: gid)
                                            }
                                        }
                                    } label: {
                                        Image(systemName: project.archived ? "arrow.uturn.backward" : "archivebox")
                                            .foregroundColor(.orange)
                                    }
                                    .buttonStyle(.borderless)
                                    .help(project.archived ? "Unarchive" : "Archive")
                                    
                                    Button(role: .destructive) {
                                        Task {
                                            try? await apiClient.deleteProject(projectId: project.id)
                                            if let gid = selectedGroupForProjects {
                                                await loadProjects(groupId: gid)
                                            }
                                        }
                                    } label: {
                                        Image(systemName: "trash").foregroundColor(.red)
                                    }
                                    .buttonStyle(.borderless)
                                }
                            }
                        }
                        
                        HStack {
                            Spacer()
                            Button("New Project...") { showingNewProjectSheet = true }
                                .buttonStyle(.bordered)
                        }
                    }
                }
            } header: {
                Text("Projects")
            } footer: {
                Text("Organize work under projects within each group.")
            }
            
            // Launch at Login Section - Requirements: 4.1
            Section {
                Toggle("Launch at Login", isOn: $settingsManager.launchAtLogin)
            } header: {
                Text("Startup")
            } footer: {
                Text("Automatically start Time Tracker Companion when you log in.")
            }
        }
        .formStyle(.grouped)
        .padding()
        .frame(width: 500, height: 600)
        .task {
            // Migrate existing project_name fields to Project records
            let _ = try? await apiClient.migrateProjects()
            await loadGroups()
            await testConnection()
        }
        .onChange(of: settingsManager.backendURL) { newValue in
            if let url = URL(string: newValue) {
                apiClient.updateBaseURL(url)
                Task {
                    await testConnection()
                }
            }
        }
        .onChange(of: settingsManager.promptIntervalMinutes) { newValue in
            // Update prompt manager when interval changes - Requirements: 4.2
            promptManager.updateInterval(newValue)
        }
        .sheet(isPresented: $showingNewGroupSheet) {
            NewGroupSheet(apiClient: apiClient) { newGroup in
                groups.append(newGroup)
                settingsManager.defaultGroupId = newGroup.id
            }
        }
        .sheet(isPresented: $showingNewProjectSheet) {
            if let groupId = selectedGroupForProjects {
                NewProjectSheet(apiClient: apiClient, groupId: groupId) { _ in
                    Task { await loadProjects(groupId: groupId) }
                }
            }
        }
    }
    
    private func loadGroups() async {
        isLoadingGroups = true
        do {
            groups = try await apiClient.fetchGroups()
            // Auto-select group for projects section
            if selectedGroupForProjects == nil {
                if let defaultId = settingsManager.defaultGroupId,
                   groups.contains(where: { $0.id == defaultId }) {
                    selectedGroupForProjects = defaultId
                } else if let first = groups.first {
                    selectedGroupForProjects = first.id
                }
            }
            // Load projects for the selected group
            if let gid = selectedGroupForProjects {
                await loadProjects(groupId: gid)
            }
        } catch {
            groups = []
        }
        isLoadingGroups = false
    }
    
    private func loadProjects(groupId: Int) async {
        do {
            projectsForSelectedGroup = try await apiClient.fetchProjects(groupId: groupId, includeArchived: true)
        } catch {
            projectsForSelectedGroup = []
        }
    }
    
    private func deleteGroup(_ group: ResearchGroup) async {
        do {
            try await apiClient.deleteGroup(groupId: group.id)
            groups.removeAll { $0.id == group.id }
            if settingsManager.defaultGroupId == group.id {
                settingsManager.defaultGroupId = nil
            }
        } catch {
            // Silently fail - could add error handling UI if needed
        }
    }
    
    private func testConnection() async {
        connectionStatus = "Checking..."
        let connected = await apiClient.healthCheck()
        connectionStatus = connected ? "Connected" : "Disconnected"
    }
}

struct NewGroupSheet: View {
    let apiClient: APIClient
    let onCreated: (ResearchGroup) -> Void
    
    @Environment(\.dismiss) private var dismiss
    
    @State private var name: String = ""
    @State private var managerName: String = ""
    @State private var projectName: String = ""
    @State private var isCreating: Bool = false
    @State private var errorMessage: String?
    
    var body: some View {
        VStack(spacing: 16) {
            Text("New Research Group")
                .font(.headline)
            
            Form {
                TextField("Group Name", text: $name)
                TextField("Manager Name (optional)", text: $managerName)
                TextField("Project Name (optional)", text: $projectName)
            }
            .formStyle(.grouped)
            
            if let error = errorMessage {
                Text(error)
                    .foregroundColor(.red)
                    .font(.caption)
            }
            
            HStack {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)
                
                Spacer()
                
                Button("Create") {
                    Task {
                        await createGroup()
                    }
                }
                .keyboardShortcut(.defaultAction)
                .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty || isCreating)
            }
        }
        .padding()
        .frame(width: 350, height: 250)
    }
    
    private func createGroup() async {
        isCreating = true
        errorMessage = nil
        
        do {
            let group = try await apiClient.createGroup(
                name: name.trimmingCharacters(in: .whitespaces),
                managerName: managerName.trimmingCharacters(in: .whitespaces),
                projectName: projectName.trimmingCharacters(in: .whitespaces)
            )
            onCreated(group)
            dismiss()
        } catch {
            errorMessage = "Failed to create group: \(error.localizedDescription)"
        }
        
        isCreating = false
    }
}


struct NewProjectSheet: View {
    let apiClient: APIClient
    let groupId: Int
    let onCreated: (Project) -> Void
    
    @Environment(\.dismiss) private var dismiss
    
    @State private var name: String = ""
    @State private var isCreating: Bool = false
    @State private var errorMessage: String?
    
    var body: some View {
        VStack(spacing: 16) {
            Text("New Project")
                .font(.headline)
            
            Form {
                TextField("Project Name", text: $name)
            }
            .formStyle(.grouped)
            
            if let error = errorMessage {
                Text(error)
                    .foregroundColor(.red)
                    .font(.caption)
            }
            
            HStack {
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.cancelAction)
                
                Spacer()
                
                Button("Create") {
                    Task { await createProject() }
                }
                .keyboardShortcut(.defaultAction)
                .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty || isCreating)
            }
        }
        .padding()
        .frame(width: 300, height: 180)
    }
    
    private func createProject() async {
        isCreating = true
        errorMessage = nil
        
        do {
            let project = try await apiClient.createProject(
                groupId: groupId,
                name: name.trimmingCharacters(in: .whitespaces)
            )
            onCreated(project)
            dismiss()
        } catch {
            errorMessage = "Failed to create project: \(error.localizedDescription)"
        }
        
        isCreating = false
    }
}

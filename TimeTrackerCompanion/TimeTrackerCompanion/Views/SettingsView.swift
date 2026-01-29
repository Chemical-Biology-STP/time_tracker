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
                Text("Prompts will be suppressed outside these hours.")
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
            } header: {
                Text("Server")
            } footer: {
                Text("URL of your Flask time tracker backend.")
            }

            // Default Research Group Section - Requirements: 4.1
            Section {
                if isLoadingGroups {
                    HStack {
                        ProgressView()
                            .scaleEffect(0.7)
                        Text("Loading groups...")
                            .foregroundColor(.secondary)
                    }
                } else if groups.isEmpty {
                    HStack {
                        Text("No groups available")
                            .foregroundColor(.secondary)
                        Spacer()
                        Button("Refresh") {
                            Task {
                                await loadGroups()
                            }
                        }
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
                                Text(group.name)
                                    .font(.body)
                                if !group.project_name.isEmpty {
                                    Text(group.project_name)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                            Spacer()
                            Button(role: .destructive) {
                                Task {
                                    await deleteGroup(group)
                                }
                            } label: {
                                Image(systemName: "trash")
                                    .foregroundColor(.red)
                            }
                            .buttonStyle(.borderless)
                        }
                    }
                }
                
                HStack {
                    Spacer()
                    Button("New Group...") {
                        showingNewGroupSheet = true
                    }
                    .buttonStyle(.bordered)
                }
            } header: {
                Text("Default Research Group")
            } footer: {
                Text("Pre-selected group when logging time.")
            }
            
            // Launch at Login Section - Requirements: 4.1
            Section {
                Toggle("Launch at Login", isOn: $settingsManager.launchAtLogin)
            } header: {
                Text("Startup")
            } footer: {
                Text("Automatically start Time Tracker Companion when you log in.")
            }
            
            // Flask Server Section
            Section {
                Toggle("Auto-start Flask server", isOn: $settingsManager.autoStartServer)
                
                HStack {
                    Text("Project Path:")
                    TextField("Path to time_tracker folder", text: $settingsManager.projectPath)
                        .textFieldStyle(.roundedBorder)
                    Button("Browse...") {
                        selectProjectFolder()
                    }
                    .buttonStyle(.bordered)
                }
                
                HStack {
                    Text("Port:")
                    TextField("Port", value: $settingsManager.serverPort, format: .number)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 80)
                    
                    Spacer()
                    
                    if FlaskServerManager.shared.isRunning {
                        HStack {
                            Circle()
                                .fill(Color.green)
                                .frame(width: 8, height: 8)
                            Text("Server Running")
                                .foregroundColor(.green)
                        }
                    } else {
                        HStack {
                            Circle()
                                .fill(Color.red)
                                .frame(width: 8, height: 8)
                            Text("Server Stopped")
                                .foregroundColor(.red)
                        }
                    }
                }
                
                HStack {
                    Button("Start Server") {
                        FlaskServerManager.shared.startServer(
                            projectPath: settingsManager.projectPath,
                            port: settingsManager.serverPort
                        )
                    }
                    .disabled(settingsManager.projectPath.isEmpty || FlaskServerManager.shared.isRunning)
                    .buttonStyle(.bordered)
                    
                    Button("Stop Server") {
                        FlaskServerManager.shared.stopServer()
                    }
                    .disabled(!FlaskServerManager.shared.isRunning)
                    .buttonStyle(.bordered)
                }
            } header: {
                Text("Flask Server")
            } footer: {
                Text("Automatically start the Flask backend when the app launches.")
            }
        }
        .formStyle(.grouped)
        .padding()
        .frame(width: 500, height: 700)
        .task {
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
    }
    
    private func loadGroups() async {
        isLoadingGroups = true
        do {
            groups = try await apiClient.fetchGroups()
        } catch {
            groups = []
        }
        isLoadingGroups = false
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
    
    private func selectProjectFolder() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.message = "Select the time_tracker project folder"
        panel.prompt = "Select"
        
        if panel.runModal() == .OK, let url = panel.url {
            settingsManager.projectPath = url.path
        }
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

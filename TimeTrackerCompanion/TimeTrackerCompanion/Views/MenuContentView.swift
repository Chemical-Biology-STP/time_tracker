// MenuContentView.swift
// TimeTrackerCompanion
//
// Menu bar dropdown content view
// Requirements: 1.2, 5.1, 5.2, 5.3, 5.4, 6.2

import SwiftUI

struct MenuContentView: View {
    @EnvironmentObject var promptManager: PromptManager
    @EnvironmentObject var settingsManager: SettingsManager
    @EnvironmentObject var apiClient: APIClient
    @EnvironmentObject var appDelegate: AppDelegate
    
    @Environment(\.dismiss) private var dismiss
    
    @State private var groups: [ResearchGroup] = []
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Header with connection status
            HStack {
                Text("Time Tracker")
                    .font(.headline)
                Spacer()
                connectionStatusIndicator
            }
            
            Divider()
            
            // Time until next prompt - Requirements: 5.3
            HStack {
                Image(systemName: "clock")
                    .foregroundColor(.secondary)
                Text("Next prompt in:")
                    .foregroundColor(.secondary)
                Spacer()
                Text(promptManager.formattedTimeUntilNextPrompt)
                    .monospacedDigit()
                    .fontWeight(.medium)
            }
            .font(.subheadline)
            
            // Currently selected group - Requirements: 5.4
            if let groupId = settingsManager.defaultGroupId,
               let group = groups.first(where: { $0.id == groupId }) {
                HStack {
                    Image(systemName: "folder")
                        .foregroundColor(.secondary)
                    Text("Group:")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(group.name)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }
                .font(.subheadline)
            }
            
            Divider()
            
            // Log Time Now button - Requirements: 5.1
            Button(action: {
                dismiss()
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                    promptManager.triggerPromptNow()
                }
            }) {
                HStack {
                    Image(systemName: "plus.circle.fill")
                    Text("Log Time Now")
                    Spacer()
                }
            }
            .buttonStyle(.plain)
            .padding(.vertical, 4)

            // Skip Next Prompt button - Requirements: 5.2
            Button(action: {
                promptManager.skipNext()
            }) {
                HStack {
                    Image(systemName: "forward.fill")
                    Text("Skip Next Prompt")
                    if promptManager.skipNextPrompt {
                        Spacer()
                        Image(systemName: "checkmark")
                            .foregroundColor(.green)
                    } else {
                        Spacer()
                    }
                }
            }
            .buttonStyle(.plain)
            .padding(.vertical, 4)
            
            Divider()
            
            // Settings - Requirements: 1.2
            Button(action: {
                dismiss()
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                    appDelegate.showSettingsWindow()
                }
            }) {
                HStack {
                    Image(systemName: "gear")
                    Text("Settings...")
                    Spacer()
                }
            }
            .buttonStyle(.plain)
            .padding(.vertical, 4)
            
            // Quit - Requirements: 1.3
            Button(action: {
                NSApplication.shared.terminate(nil)
            }) {
                HStack {
                    Image(systemName: "power")
                    Text("Quit")
                    Spacer()
                }
            }
            .buttonStyle(.plain)
            .padding(.vertical, 4)
            
            Divider()
            
            // Version info
            HStack {
                Spacer()
                Text("v\(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?")")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .frame(width: 250)
        .task {
            await loadGroups()
        }
    }
    
    // Connection status indicator - Requirements: 6.2
    private var connectionStatusIndicator: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(apiClient.isConnected ? Color.green : Color.red)
                .frame(width: 8, height: 8)
            Text(apiClient.isConnected ? "Connected" : "Disconnected")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
    
    private func loadGroups() async {
        do {
            groups = try await apiClient.fetchGroups()
        } catch {
            // Groups will remain empty, which is fine for display purposes
        }
    }
}

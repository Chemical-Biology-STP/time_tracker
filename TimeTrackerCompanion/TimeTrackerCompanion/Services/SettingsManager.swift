// SettingsManager.swift
// TimeTrackerCompanion
//
// Manages user settings persistence using UserDefaults

import Foundation

class SettingsManager: ObservableObject {
    @Published var promptIntervalMinutes: Int {
        didSet { UserDefaults.standard.set(promptIntervalMinutes, forKey: "promptInterval") }
    }
    
    @Published var backendURL: String {
        didSet { UserDefaults.standard.set(backendURL, forKey: "backendURL") }
    }
    
    @Published var defaultGroupId: Int? {
        didSet { UserDefaults.standard.set(defaultGroupId, forKey: "defaultGroupId") }
    }
    
    @Published var launchAtLogin: Bool {
        didSet { UserDefaults.standard.set(launchAtLogin, forKey: "launchAtLogin") }
    }
    
    @Published var projectPath: String {
        didSet { UserDefaults.standard.set(projectPath, forKey: "projectPath") }
    }
    
    @Published var autoStartServer: Bool {
        didSet { UserDefaults.standard.set(autoStartServer, forKey: "autoStartServer") }
    }
    
    @Published var serverPort: Int {
        didSet { UserDefaults.standard.set(serverPort, forKey: "serverPort") }
    }
    
    init() {
        // Read all values first before assigning to avoid Swift initialization order issues
        let storedInterval = UserDefaults.standard.integer(forKey: "promptInterval")
        let storedURL = UserDefaults.standard.string(forKey: "backendURL")
        let storedGroupId = UserDefaults.standard.object(forKey: "defaultGroupId") as? Int
        let storedLaunchAtLogin = UserDefaults.standard.bool(forKey: "launchAtLogin")
        let storedProjectPath = UserDefaults.standard.string(forKey: "projectPath")
        let storedAutoStartServer = UserDefaults.standard.bool(forKey: "autoStartServer")
        let storedServerPort = UserDefaults.standard.integer(forKey: "serverPort")
        
        // Initialize all properties with defaults if needed
        self.promptIntervalMinutes = storedInterval == 0 ? 30 : storedInterval
        self.backendURL = storedURL ?? "http://localhost:5001"
        self.defaultGroupId = storedGroupId
        self.launchAtLogin = storedLaunchAtLogin
        self.projectPath = storedProjectPath ?? ""
        self.autoStartServer = storedAutoStartServer
        self.serverPort = storedServerPort == 0 ? 5001 : storedServerPort
    }
}

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
    
    @Published var workingHoursEnabled: Bool {
        didSet { UserDefaults.standard.set(workingHoursEnabled, forKey: "workingHoursEnabled") }
    }
    
    @Published var workStartHour: Int {
        didSet { UserDefaults.standard.set(workStartHour, forKey: "workStartHour") }
    }
    
    @Published var workStartMinute: Int {
        didSet { UserDefaults.standard.set(workStartMinute, forKey: "workStartMinute") }
    }
    
    @Published var workEndHour: Int {
        didSet { UserDefaults.standard.set(workEndHour, forKey: "workEndHour") }
    }
    
    @Published var workEndMinute: Int {
        didSet { UserDefaults.standard.set(workEndMinute, forKey: "workEndMinute") }
    }
    
    @Published var workingDays: Set<Int> {
        didSet { UserDefaults.standard.set(Array(workingDays), forKey: "workingDays") }
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
        let storedWorkingHoursEnabled = UserDefaults.standard.bool(forKey: "workingHoursEnabled")
        let storedWorkStartHour = UserDefaults.standard.object(forKey: "workStartHour") as? Int
        let storedWorkStartMinute = UserDefaults.standard.integer(forKey: "workStartMinute")
        let storedWorkEndHour = UserDefaults.standard.object(forKey: "workEndHour") as? Int
        let storedWorkEndMinute = UserDefaults.standard.integer(forKey: "workEndMinute")
        let storedWorkingDays = UserDefaults.standard.array(forKey: "workingDays") as? [Int]
        
        // Initialize all properties with defaults if needed
        self.promptIntervalMinutes = storedInterval == 0 ? 30 : storedInterval
        self.backendURL = storedURL ?? "http://localhost:5001"
        self.defaultGroupId = storedGroupId
        self.launchAtLogin = storedLaunchAtLogin
        self.projectPath = storedProjectPath ?? ""
        self.autoStartServer = storedAutoStartServer
        self.serverPort = storedServerPort == 0 ? 5001 : storedServerPort
        self.workingHoursEnabled = storedWorkingHoursEnabled
        self.workStartHour = storedWorkStartHour ?? 9
        self.workStartMinute = storedWorkStartMinute
        self.workEndHour = storedWorkEndHour ?? 17
        self.workEndMinute = storedWorkEndMinute
        // Default to Monday-Friday (2-6 in Calendar, where 1=Sunday)
        self.workingDays = storedWorkingDays != nil ? Set(storedWorkingDays!) : Set([2, 3, 4, 5, 6])
    }
    
    /// Check if current time is within working hours and on a working day
    func isWithinWorkingHours() -> Bool {
        guard workingHoursEnabled else { return true }
        
        let now = Date()
        let calendar = Calendar.current
        let weekday = calendar.component(.weekday, from: now)
        let hour = calendar.component(.hour, from: now)
        let minute = calendar.component(.minute, from: now)
        
        // Check if today is a working day
        guard workingDays.contains(weekday) else { return false }
        
        let currentMinutes = hour * 60 + minute
        let startMinutes = workStartHour * 60 + workStartMinute
        let endMinutes = workEndHour * 60 + workEndMinute
        
        return currentMinutes >= startMinutes && currentMinutes < endMinutes
    }
    
    /// Toggle a working day
    func toggleWorkingDay(_ day: Int) {
        if workingDays.contains(day) {
            workingDays.remove(day)
        } else {
            workingDays.insert(day)
        }
    }
}

// TimeTrackerCompanionApp.swift
// TimeTrackerCompanion
//
// Main entry point for the macOS menu bar companion app
// Requirements: 1.1, 1.2, 1.3

import SwiftUI
import UserNotifications
import Combine

@main
struct TimeTrackerCompanionApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        // Menu bar icon with dropdown - Requirements: 1.1, 1.2
        MenuBarExtra("Time Tracker", image: "MenuBarIcon") {
            MenuContentView()
                .environmentObject(appDelegate.promptManager)
                .environmentObject(appDelegate.settingsManager)
                .environmentObject(appDelegate.apiClient)
                .environmentObject(appDelegate.notificationManager)
                .environmentObject(appDelegate)
        }
        .menuBarExtraStyle(.window)
    }
}

/// App delegate to handle startup behavior and prompt window management
/// Requirements: 1.5, 2.3, 2.4, 2.5, 3.1, 6.1, 6.4
class AppDelegate: NSObject, NSApplicationDelegate, ObservableObject, NSWindowDelegate {
    let promptManager = PromptManager()
    let settingsManager = SettingsManager()
    let apiClient = APIClient()
    let notificationManager = NotificationManager.shared
    let flaskServerManager = FlaskServerManager.shared
    
    @Published var showSettings = false
    
    private var promptWindow: NSWindow?
    private var settingsWindow: NSWindow?
    private var cancellables = Set<AnyCancellable>()
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Request notification permissions - Requirements: 2.5, 6.1
        Task {
            await notificationManager.requestAuthorization()
        }
        
        // Start Flask server if bundled server available OR if configured for development
        let shouldStartServer = flaskServerManager.hasBundledServer || 
            (settingsManager.autoStartServer && !settingsManager.projectPath.isEmpty)
        
        if shouldStartServer {
            flaskServerManager.startServer(
                projectPath: settingsManager.projectPath,
                port: settingsManager.serverPort
            )
            // Wait a bit for server to start before health check
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
                Task {
                    await self?.performStartupTasks()
                }
            }
        } else {
            // Perform startup tasks immediately
            Task {
                await performStartupTasks()
            }
        }
        
        // Observe showPrompt changes to show/hide prompt window
        promptManager.$showPrompt
            .receive(on: DispatchQueue.main)
            .sink { [weak self] showPrompt in
                if showPrompt {
                    self?.showPromptWindow()
                } else {
                    self?.hidePromptWindow()
                }
            }
            .store(in: &cancellables)
        
        // Observe showSettings changes
        $showSettings
            .receive(on: DispatchQueue.main)
            .sink { [weak self] show in
                if show {
                    self?.showSettingsWindow()
                }
            }
            .store(in: &cancellables)
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        // Stop Flask server when app quits
        flaskServerManager.stopServer()
    }
    
    /// Perform startup tasks: health check, fetch groups, start timer
    /// Requirements: 1.5, 3.1, 6.4
    private func performStartupTasks() async {
        do {
            // Update API client base URL from settings
            if let url = URL(string: settingsManager.backendURL) {
                apiClient.updateBaseURL(url)
            }
            
            // Perform initial health check - Requirements: 3.1
            let isHealthy = await apiClient.healthCheck()
            if !isHealthy {
                await notificationManager.showConnectionErrorNotification()
            }
            
            // Fetch research groups on app launch - Requirements: 1.5
            do {
                _ = try await apiClient.fetchGroups()
            } catch {
                // Groups will be fetched again when needed
                print("Failed to fetch groups on startup: \(error.localizedDescription)")
            }
            
            // Start prompt timer with configured interval - Requirements: 2.1
            await MainActor.run {
                promptManager.start(intervalMinutes: settingsManager.promptIntervalMinutes)
            }
        } catch {
            // Log and show startup error - Requirements: 6.4
            print("Startup error: \(error.localizedDescription)")
            await notificationManager.showStartupErrorNotification(error: error)
        }
    }
    
    /// Show the prompt window - Requirements: 2.2
    private func showPromptWindow() {
        if promptWindow == nil {
            let promptView = PromptView()
                .environmentObject(promptManager)
                .environmentObject(settingsManager)
                .environmentObject(apiClient)
                .environmentObject(notificationManager)
            
            let hostingController = NSHostingController(rootView: promptView)
            
            let window = NSWindow(contentViewController: hostingController)
            window.title = "Log Time"
            window.styleMask = [.titled, .closable]
            window.level = .floating
            window.center()
            window.isReleasedWhenClosed = false
            window.delegate = self
            
            promptWindow = window
        }
        
        promptWindow?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    
    /// Hide the prompt window - Requirements: 2.4
    private func hidePromptWindow() {
        promptWindow?.orderOut(nil)
    }
    
    /// Handle window close button click
    func windowWillClose(_ notification: Notification) {
        if let window = notification.object as? NSWindow, window == promptWindow {
            promptManager.dismissPrompt()
        }
    }
    
    /// Show the settings window with floating level
    func showSettingsWindow() {
        if settingsWindow == nil {
            let settingsView = SettingsView()
                .environmentObject(settingsManager)
                .environmentObject(apiClient)
                .environmentObject(promptManager)
            
            let hostingController = NSHostingController(rootView: settingsView)
            
            let window = NSWindow(contentViewController: hostingController)
            window.title = "Settings"
            window.styleMask = [.titled, .closable]
            window.level = .floating
            window.center()
            window.isReleasedWhenClosed = false
            
            settingsWindow = window
        }
        
        settingsWindow?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        showSettings = false
    }
}

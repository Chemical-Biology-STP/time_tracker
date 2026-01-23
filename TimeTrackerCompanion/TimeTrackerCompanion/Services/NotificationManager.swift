// NotificationManager.swift
// TimeTrackerCompanion
//
// Centralized notification management service
// Requirements: 2.5, 6.1, 6.4

import Foundation
import UserNotifications

/// Manages all user notifications for the app
/// Requirements: 2.5, 6.1, 6.4
class NotificationManager: ObservableObject {
    static let shared = NotificationManager()
    
    @Published private(set) var isAuthorized: Bool = false
    
    private init() {}
    
    /// Request notification permissions from the user
    /// Requirements: 2.5, 6.1
    func requestAuthorization() async {
        do {
            let granted = try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge])
            await MainActor.run {
                self.isAuthorized = granted
            }
            if !granted {
                print("Notification permission denied by user")
            }
        } catch {
            print("Notification permission error: \(error.localizedDescription)")
            await MainActor.run {
                self.isAuthorized = false
            }
        }
    }
    
    /// Check current notification authorization status
    func checkAuthorizationStatus() async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        await MainActor.run {
            self.isAuthorized = settings.authorizationStatus == .authorized
        }
    }
    
    /// Show a success notification after time entry creation
    /// - Parameters:
    ///   - hours: Number of hours logged
    ///   - taskDescription: Description of the task
    /// Requirements: 2.5
    func showEntryCreatedNotification(hours: Double, taskDescription: String) async {
        await showNotification(
            title: "Time Entry Saved",
            body: "Logged \(String(format: "%.2f", hours)) hours: \(taskDescription)",
            identifier: "entry-created-\(UUID().uuidString)"
        )
    }
    
    /// Show an error notification for API failures
    /// - Parameter error: The error that occurred
    /// Requirements: 6.1
    func showEntryErrorNotification(error: Error) async {
        let message: String
        if let apiError = error as? APIError {
            switch apiError {
            case .requestFailed:
                message = "Request failed. Please check your connection."
            case .serverError(let code):
                message = "Server error (code \(code)). Please try again."
            case .decodingError:
                message = "Invalid response from server."
            case .invalidURL:
                message = "Invalid server URL. Please check your settings."
            }
        } else {
            message = error.localizedDescription
        }
        
        await showNotification(
            title: "Failed to Save Entry",
            body: message,
            identifier: "entry-error-\(UUID().uuidString)"
        )
    }
    
    /// Show a connection error notification
    /// - Parameter message: Optional custom message
    /// Requirements: 6.4
    func showConnectionErrorNotification(message: String? = nil) async {
        await showNotification(
            title: "Connection Error",
            body: message ?? "Cannot connect to time tracker. Is the Flask server running?",
            identifier: "connection-error-\(UUID().uuidString)"
        )
    }
    
    /// Show a startup error notification
    /// - Parameter error: The error that occurred during startup
    /// Requirements: 6.4
    func showStartupErrorNotification(error: Error) async {
        await showNotification(
            title: "Time Tracker Startup Error",
            body: "An error occurred during startup: \(error.localizedDescription)",
            identifier: "startup-error-\(UUID().uuidString)"
        )
    }
    
    /// Show a generic notification
    /// - Parameters:
    ///   - title: Notification title
    ///   - body: Notification body text
    ///   - identifier: Unique identifier for the notification
    func showNotification(title: String, body: String, identifier: String? = nil) async {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        
        let request = UNNotificationRequest(
            identifier: identifier ?? UUID().uuidString,
            content: content,
            trigger: nil // Deliver immediately
        )
        
        do {
            try await UNUserNotificationCenter.current().add(request)
        } catch {
            print("Failed to show notification: \(error.localizedDescription)")
        }
    }
}

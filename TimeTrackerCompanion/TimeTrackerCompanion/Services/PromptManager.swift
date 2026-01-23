// PromptManager.swift
// TimeTrackerCompanion
//
// Manages prompt timing and scheduling

import Foundation

class PromptManager: ObservableObject {
    @Published var showPrompt = false
    @Published var timeUntilNextPrompt: TimeInterval = 0
    @Published var skipNextPrompt = false
    
    private var timer: Timer?
    private var intervalMinutes: Int = 30
    private var lastPromptTime: Date?
    
    /// Start the prompt timer with the specified interval
    /// - Parameter intervalMinutes: Minutes between prompts
    /// - Requirements: 2.1
    func start(intervalMinutes: Int) {
        self.intervalMinutes = intervalMinutes
        scheduleNextPrompt()
    }
    
    /// Stop the prompt timer
    func stop() {
        timer?.invalidate()
        timer = nil
    }
    
    /// Trigger a prompt immediately (manual trigger)
    /// - Requirements: 5.1
    func triggerPromptNow() {
        showPrompt = true
        lastPromptTime = Date()
        scheduleNextPrompt()
    }
    
    /// Skip the next scheduled prompt
    /// - Requirements: 5.2
    func skipNext() {
        skipNextPrompt = true
    }
    
    /// Update the prompt interval and reschedule
    /// - Parameter minutes: New interval in minutes
    /// - Requirements: 4.2
    func updateInterval(_ minutes: Int) {
        self.intervalMinutes = minutes
        scheduleNextPrompt()
    }
    
    /// Dismiss the current prompt
    func dismissPrompt() {
        showPrompt = false
    }
    
    /// Schedule the next prompt based on current interval
    private func scheduleNextPrompt() {
        timer?.invalidate()
        
        let interval = TimeInterval(intervalMinutes * 60)
        timeUntilNextPrompt = interval
        
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            self.timeUntilNextPrompt -= 1
            
            if self.timeUntilNextPrompt <= 0 {
                if self.skipNextPrompt {
                    self.skipNextPrompt = false
                } else {
                    self.showPrompt = true
                    self.lastPromptTime = Date()
                }
                self.timeUntilNextPrompt = interval
            }
        }
    }
    
    /// Calculate the time block for a time entry based on current interval
    /// - Returns: Tuple with start and end time strings in HH:mm format
    /// - Requirements: 3.5
    func calculateTimeBlock() -> (start: String, end: String) {
        let end = Date()
        let start = end.addingTimeInterval(-TimeInterval(intervalMinutes * 60))
        
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        
        return (formatter.string(from: start), formatter.string(from: end))
    }
    
    /// Calculate the time block for a time entry with a specific interval
    /// - Parameters:
    ///   - intervalMinutes: The interval in minutes
    ///   - endDate: The end date/time for the block
    /// - Returns: Tuple with start and end time strings in HH:mm format
    /// - Requirements: 3.5
    func calculateTimeBlock(intervalMinutes: Int, endDate: Date) -> (start: String, end: String) {
        let start = endDate.addingTimeInterval(-TimeInterval(intervalMinutes * 60))
        
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        
        return (formatter.string(from: start), formatter.string(from: endDate))
    }
    
    /// Get formatted time until next prompt for display
    /// - Returns: Formatted string like "25:30" (minutes:seconds)
    /// - Requirements: 5.3
    var formattedTimeUntilNextPrompt: String {
        let minutes = Int(timeUntilNextPrompt) / 60
        let seconds = Int(timeUntilNextPrompt) % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
}

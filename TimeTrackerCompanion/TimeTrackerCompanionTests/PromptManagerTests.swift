// PromptManagerTests.swift
// TimeTrackerCompanionTests
//
// Property-based tests for PromptManager time block calculation

import XCTest
@testable import TimeTrackerCompanion

/// Property test for time block calculation
/// **Validates: Requirements 3.5**
///
/// Property 6: Time block calculation
/// For any prompt interval of N minutes, when creating a time entry,
/// the start_time SHALL equal (current_time - N minutes) and end_time SHALL equal current_time.
final class PromptManagerTests: XCTestCase {
    
    // MARK: - Property Test: Time Block Calculation
    
    /// Property 6: Time block calculation
    /// **Validates: Requirements 3.5**
    ///
    /// Tests that for any interval and end time, the calculated start time
    /// equals (end_time - interval) and the end time is preserved.
    func testPropertyTimeBlockCalculation() {
        let promptManager = PromptManager()
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        
        // Run 100 iterations with random values as per design document
        for iteration in 0..<100 {
            // Generate random interval (1-120 minutes as per design)
            let intervalMinutes = Int.random(in: 1...120)
            
            // Generate random end time (any time of day)
            let calendar = Calendar.current
            let randomHour = Int.random(in: 0...23)
            let randomMinute = Int.random(in: 0...59)
            
            var components = calendar.dateComponents([.year, .month, .day], from: Date())
            components.hour = randomHour
            components.minute = randomMinute
            components.second = 0
            
            guard let endDate = calendar.date(from: components) else {
                XCTFail("Failed to create end date for iteration \(iteration)")
                continue
            }
            
            // Calculate expected start time
            let expectedStartDate = endDate.addingTimeInterval(-TimeInterval(intervalMinutes * 60))
            let expectedStartTime = formatter.string(from: expectedStartDate)
            let expectedEndTime = formatter.string(from: endDate)
            
            // Get actual time block from PromptManager
            let (actualStartTime, actualEndTime) = promptManager.calculateTimeBlock(
                intervalMinutes: intervalMinutes,
                endDate: endDate
            )
            
            // Verify start_time = end_time - interval
            XCTAssertEqual(
                actualStartTime, expectedStartTime,
                "Iteration \(iteration): start_time mismatch. " +
                "Interval: \(intervalMinutes) min, End: \(expectedEndTime). " +
                "Expected start: \(expectedStartTime), got: \(actualStartTime)"
            )
            
            // Verify end_time is preserved
            XCTAssertEqual(
                actualEndTime, expectedEndTime,
                "Iteration \(iteration): end_time mismatch. " +
                "Expected: \(expectedEndTime), got: \(actualEndTime)"
            )
            
            // Verify the time difference is exactly the interval
            let startComponents = actualStartTime.split(separator: ":").compactMap { Int($0) }
            let endComponents = actualEndTime.split(separator: ":").compactMap { Int($0) }
            
            guard startComponents.count == 2, endComponents.count == 2 else {
                XCTFail("Iteration \(iteration): Invalid time format")
                continue
            }
            
            let startMinutes = startComponents[0] * 60 + startComponents[1]
            let endMinutes = endComponents[0] * 60 + endComponents[1]
            
            // Handle day boundary crossing
            var diff = endMinutes - startMinutes
            if diff < 0 {
                diff += 24 * 60 // Add a day's worth of minutes
            }
            
            XCTAssertEqual(
                diff, intervalMinutes,
                "Iteration \(iteration): Time difference should equal interval. " +
                "Expected \(intervalMinutes) min, got \(diff) min. " +
                "Start: \(actualStartTime), End: \(actualEndTime)"
            )
        }
    }
    
    // MARK: - Specific Time Block Tests
    
    /// Test time block calculation with 30 minute interval (default)
    func testTimeBlockWith30MinuteInterval() {
        let promptManager = PromptManager()
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        
        // Create a specific end time: 10:30
        var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
        components.hour = 10
        components.minute = 30
        let endDate = Calendar.current.date(from: components)!
        
        let (start, end) = promptManager.calculateTimeBlock(intervalMinutes: 30, endDate: endDate)
        
        XCTAssertEqual(start, "10:00", "Start should be 10:00 for 30 min interval ending at 10:30")
        XCTAssertEqual(end, "10:30", "End should be 10:30")
    }
    
    /// Test time block calculation with 15 minute interval
    func testTimeBlockWith15MinuteInterval() {
        let promptManager = PromptManager()
        
        var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
        components.hour = 14
        components.minute = 45
        let endDate = Calendar.current.date(from: components)!
        
        let (start, end) = promptManager.calculateTimeBlock(intervalMinutes: 15, endDate: endDate)
        
        XCTAssertEqual(start, "14:30", "Start should be 14:30 for 15 min interval ending at 14:45")
        XCTAssertEqual(end, "14:45", "End should be 14:45")
    }
    
    /// Test time block calculation with 60 minute interval
    func testTimeBlockWith60MinuteInterval() {
        let promptManager = PromptManager()
        
        var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
        components.hour = 16
        components.minute = 0
        let endDate = Calendar.current.date(from: components)!
        
        let (start, end) = promptManager.calculateTimeBlock(intervalMinutes: 60, endDate: endDate)
        
        XCTAssertEqual(start, "15:00", "Start should be 15:00 for 60 min interval ending at 16:00")
        XCTAssertEqual(end, "16:00", "End should be 16:00")
    }
    
    /// Test time block calculation crossing midnight
    func testTimeBlockCrossingMidnight() {
        let promptManager = PromptManager()
        
        var components = Calendar.current.dateComponents([.year, .month, .day], from: Date())
        components.hour = 0
        components.minute = 15
        let endDate = Calendar.current.date(from: components)!
        
        let (start, end) = promptManager.calculateTimeBlock(intervalMinutes: 30, endDate: endDate)
        
        XCTAssertEqual(start, "23:45", "Start should be 23:45 for 30 min interval ending at 00:15")
        XCTAssertEqual(end, "00:15", "End should be 00:15")
    }
    
    /// Test formatted time until next prompt
    func testFormattedTimeUntilNextPrompt() {
        let promptManager = PromptManager()
        
        // Set time to 25 minutes 30 seconds
        promptManager.timeUntilNextPrompt = 25 * 60 + 30
        
        XCTAssertEqual(promptManager.formattedTimeUntilNextPrompt, "25:30")
        
        // Set time to 5 minutes 5 seconds
        promptManager.timeUntilNextPrompt = 5 * 60 + 5
        
        XCTAssertEqual(promptManager.formattedTimeUntilNextPrompt, "05:05")
        
        // Set time to 0
        promptManager.timeUntilNextPrompt = 0
        
        XCTAssertEqual(promptManager.formattedTimeUntilNextPrompt, "00:00")
    }
}

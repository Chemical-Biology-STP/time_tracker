// TimeEntryResponse.swift
// TimeTrackerCompanion
//
// Model for time entry responses from the Flask backend API

import Foundation

/// Response model from POST /api/entries endpoint
/// Returned after successfully creating a time entry
struct TimeEntryResponse: Codable {
    /// Unique identifier of the created time entry
    let id: Int
    
    /// Date of the time entry in ISO format (YYYY-MM-DD)
    let date: String
    
    /// Description of the logged task
    let task_description: String
    
    /// Total hours calculated from the time block
    let total_hours: Double
}

// TimeEntryRequest.swift
// TimeTrackerCompanion
//
// Model for creating time entries via the Flask backend API

import Foundation

/// Request model for POST /api/entries endpoint
/// Contains all required fields to create a new time entry
struct TimeEntryRequest: Codable {
    /// ID of the research group to log time against
    let research_group_id: Int
    
    /// ID of the project (optional)
    let project_id: Int?
    
    /// Description of the task being logged
    let task_description: String
    
    /// Date of the time entry in ISO format (YYYY-MM-DD)
    let date: String
    
    /// Start time of the time block in HH:mm format
    let start_time: String
    
    /// End time of the time block in HH:mm format
    let end_time: String
}

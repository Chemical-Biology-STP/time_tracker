// ResearchGroup.swift
// TimeTrackerCompanion
//
// Model representing a research group from the Flask backend

import Foundation

/// Research group model matching the Flask backend API response
/// Used for displaying available groups in the prompt dialog dropdown
struct ResearchGroup: Codable, Identifiable, Hashable {
    /// Unique identifier for the research group
    let id: Int
    
    /// Display name of the research group
    let name: String
    
    /// Name of the group manager
    let manager_name: String
    
    /// Associated project name
    let project_name: String
}

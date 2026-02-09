// Project.swift
// TimeTrackerCompanion
//
// Model representing a project within a research group

import Foundation

struct Project: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let research_group_id: Int
    let archived: Bool
}

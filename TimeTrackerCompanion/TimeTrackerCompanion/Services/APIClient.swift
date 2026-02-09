// APIClient.swift
// TimeTrackerCompanion
//
// HTTP client for Flask backend API communication

import Foundation

enum APIError: Error, LocalizedError {
    case requestFailed
    case serverError(Int)
    case decodingError
    case invalidURL
    
    var errorDescription: String? {
        switch self {
        case .requestFailed:
            return "Request failed. Check your network connection."
        case .serverError(let code):
            return "Server error (HTTP \(code))"
        case .decodingError:
            return "Failed to parse server response"
        case .invalidURL:
            return "Invalid server URL"
        }
    }
}

class APIClient: ObservableObject {
    @Published var isConnected = false
    @Published var consecutiveFailures = 0
    
    private var baseURL: URL
    
    /// Threshold for consecutive failures before marking as disconnected
    private let failureThreshold = 3
    
    init(baseURL: URL = URL(string: "http://localhost:5000")!) {
        self.baseURL = baseURL
    }
    
    func updateBaseURL(_ url: URL) {
        self.baseURL = url
    }
    
    /// Fetch all research groups from the Flask backend
    /// - Returns: Array of ResearchGroup objects
    /// - Throws: APIError on failure
    /// - Requirements: 3.2
    func fetchGroups() async throws -> [ResearchGroup] {
        let url = baseURL.appendingPathComponent("/api/groups")
        
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse else {
                recordFailure()
                throw APIError.requestFailed
            }
            
            guard httpResponse.statusCode == 200 else {
                recordFailure()
                throw APIError.serverError(httpResponse.statusCode)
            }
            
            do {
                let groups = try JSONDecoder().decode([ResearchGroup].self, from: data)
                recordSuccess()
                return groups
            } catch {
                recordFailure()
                throw APIError.decodingError
            }
        } catch let error as APIError {
            throw error
        } catch {
            recordFailure()
            throw APIError.requestFailed
        }
    }
    
    /// Create a new time entry in the Flask backend
    /// - Parameter request: TimeEntryRequest containing entry details
    /// - Returns: TimeEntryResponse with created entry details
    /// - Throws: APIError on failure
    /// - Requirements: 3.3
    func createEntry(_ request: TimeEntryRequest) async throws -> TimeEntryResponse {
        let url = baseURL.appendingPathComponent("/api/entries")
        
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            urlRequest.httpBody = try JSONEncoder().encode(request)
        } catch {
            throw APIError.decodingError
        }
        
        do {
            let (data, response) = try await URLSession.shared.data(for: urlRequest)
            
            guard let httpResponse = response as? HTTPURLResponse else {
                recordFailure()
                throw APIError.requestFailed
            }
            
            if httpResponse.statusCode == 201 {
                do {
                    let entryResponse = try JSONDecoder().decode(TimeEntryResponse.self, from: data)
                    recordSuccess()
                    return entryResponse
                } catch {
                    recordFailure()
                    throw APIError.decodingError
                }
            } else {
                recordFailure()
                throw APIError.serverError(httpResponse.statusCode)
            }
        } catch let error as APIError {
            throw error
        } catch {
            recordFailure()
            throw APIError.requestFailed
        }
    }
    
    /// Check if the Flask backend is reachable
    /// - Returns: true if backend responds with 200 OK
    /// - Requirements: 3.1
    func healthCheck() async -> Bool {
        let url = baseURL.appendingPathComponent("/api/health")
        
        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            let connected = (response as? HTTPURLResponse)?.statusCode == 200
            
            if connected {
                recordSuccess()
            } else {
                recordFailure()
            }
            
            return connected
        } catch {
            recordFailure()
            return false
        }
    }
    
    /// Create a new research group in the Flask backend
    /// - Parameters:
    ///   - name: Group name (required)
    ///   - managerName: Manager name (optional)
    ///   - projectName: Project name (optional)
    /// - Returns: Created ResearchGroup
    /// - Throws: APIError on failure
    func createGroup(name: String, managerName: String = "", projectName: String = "") async throws -> ResearchGroup {
        let url = baseURL.appendingPathComponent("/api/groups")
        
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: String] = [
            "name": name,
            "manager_name": managerName,
            "project_name": projectName
        ]
        
        urlRequest.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        do {
            let (data, response) = try await URLSession.shared.data(for: urlRequest)
            
            guard let httpResponse = response as? HTTPURLResponse else {
                recordFailure()
                throw APIError.requestFailed
            }
            
            if httpResponse.statusCode == 201 {
                do {
                    let group = try JSONDecoder().decode(ResearchGroup.self, from: data)
                    recordSuccess()
                    return group
                } catch {
                    recordFailure()
                    throw APIError.decodingError
                }
            } else {
                recordFailure()
                throw APIError.serverError(httpResponse.statusCode)
            }
        } catch let error as APIError {
            throw error
        } catch {
            recordFailure()
            throw APIError.requestFailed
        }
    }
    
    /// Delete a research group from the Flask backend
    func deleteGroup(groupId: Int) async throws {
        let url = baseURL.appendingPathComponent("/api/groups/\(groupId)")
        
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "DELETE"
        
        do {
            let (_, response) = try await URLSession.shared.data(for: urlRequest)
            
            guard let httpResponse = response as? HTTPURLResponse else {
                recordFailure()
                throw APIError.requestFailed
            }
            
            if httpResponse.statusCode == 200 {
                recordSuccess()
            } else {
                recordFailure()
                throw APIError.serverError(httpResponse.statusCode)
            }
        } catch let error as APIError {
            throw error
        } catch {
            recordFailure()
            throw APIError.requestFailed
        }
    }
    
    // MARK: - Project Methods
    
    /// Fetch projects for a research group
    func fetchProjects(groupId: Int, includeArchived: Bool = false) async throws -> [Project] {
        var urlComponents = URLComponents(url: baseURL.appendingPathComponent("/api/groups/\(groupId)/projects"), resolvingAgainstBaseURL: false)!
        if includeArchived {
            urlComponents.queryItems = [URLQueryItem(name: "include_archived", value: "true")]
        }
        
        let url = urlComponents.url!
        
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                recordFailure()
                throw APIError.requestFailed
            }
            
            let projects = try JSONDecoder().decode([Project].self, from: data)
            recordSuccess()
            return projects
        } catch let error as APIError {
            throw error
        } catch {
            recordFailure()
            throw APIError.requestFailed
        }
    }
    
    /// Create a new project under a research group
    func createProject(groupId: Int, name: String) async throws -> Project {
        let url = baseURL.appendingPathComponent("/api/groups/\(groupId)/projects")
        
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try JSONSerialization.data(withJSONObject: ["name": name])
        
        do {
            let (data, response) = try await URLSession.shared.data(for: urlRequest)
            
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 201 else {
                recordFailure()
                throw APIError.requestFailed
            }
            
            let project = try JSONDecoder().decode(Project.self, from: data)
            recordSuccess()
            return project
        } catch let error as APIError {
            throw error
        } catch {
            recordFailure()
            throw APIError.requestFailed
        }
    }
    
    /// Archive or unarchive a project
    func archiveProject(projectId: Int, archived: Bool) async throws -> Project {
        let url = baseURL.appendingPathComponent("/api/projects/\(projectId)/archive")
        
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try JSONSerialization.data(withJSONObject: ["archived": archived])
        
        do {
            let (data, response) = try await URLSession.shared.data(for: urlRequest)
            
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                recordFailure()
                throw APIError.requestFailed
            }
            
            let project = try JSONDecoder().decode(Project.self, from: data)
            recordSuccess()
            return project
        } catch let error as APIError {
            throw error
        } catch {
            recordFailure()
            throw APIError.requestFailed
        }
    }
    
    /// Delete a project
    func deleteProject(projectId: Int) async throws {
        let url = baseURL.appendingPathComponent("/api/projects/\(projectId)")
        
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "DELETE"
        
        do {
            let (_, response) = try await URLSession.shared.data(for: urlRequest)
            
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                recordFailure()
                throw APIError.requestFailed
            }
            
            recordSuccess()
        } catch let error as APIError {
            throw error
        } catch {
            recordFailure()
            throw APIError.requestFailed
        }
    }
    
    /// Migrate existing project_name fields on groups into Project records
    func migrateProjects() async throws -> Int {
        let url = baseURL.appendingPathComponent("/api/migrate-projects")
        
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            let (data, response) = try await URLSession.shared.data(for: urlRequest)
            
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                recordFailure()
                throw APIError.requestFailed
            }
            
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let migrated = json["migrated"] as? Int {
                recordSuccess()
                return migrated
            }
            recordSuccess()
            return 0
        } catch let error as APIError {
            throw error
        } catch {
            recordFailure()
            throw APIError.requestFailed
        }
    }
    
    // MARK: - Connection State Tracking
    
    /// Record a successful API call
    /// Resets consecutive failures and marks as connected
    /// - Requirements: 6.3
    private func recordSuccess() {
        DispatchQueue.main.async {
            self.consecutiveFailures = 0
            self.isConnected = true
        }
    }
    
    /// Record a failed API call
    /// Increments consecutive failures and marks as disconnected after threshold
    /// - Requirements: 6.2
    private func recordFailure() {
        DispatchQueue.main.async {
            self.consecutiveFailures += 1
            if self.consecutiveFailures >= self.failureThreshold {
                self.isConnected = false
            }
        }
    }
    
    // MARK: - Testing Support
    
    /// Simulate a successful API call (for testing)
    func simulateSuccess() {
        recordSuccess()
    }
    
    /// Simulate a failed API call (for testing)
    func simulateFailure() {
        recordFailure()
    }
    
    /// Simulate a successful API call synchronously (for testing)
    func simulateSuccessSync() {
        consecutiveFailures = 0
        isConnected = true
    }
    
    /// Simulate a failed API call synchronously (for testing)
    func simulateFailureSync() {
        consecutiveFailures += 1
        if consecutiveFailures >= failureThreshold {
            isConnected = false
        }
    }
}

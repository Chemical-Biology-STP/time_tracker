// FlaskServerManager.swift
// TimeTrackerCompanion
//
// Manages the Flask backend server lifecycle

import Foundation

class FlaskServerManager: ObservableObject {
    static let shared = FlaskServerManager()
    
    @Published var isRunning = false
    @Published var serverOutput = ""
    
    private var process: Process?
    private var outputPipe: Pipe?
    
    private init() {}
    
    /// Get the path to the bundled server executable
    private var bundledServerPath: String? {
        // Look for the server in the app bundle's Resources folder
        if let resourcePath = Bundle.main.resourcePath {
            let serverPath = (resourcePath as NSString).appendingPathComponent("TimeTrackerServer")
            if FileManager.default.fileExists(atPath: serverPath) {
                return serverPath
            }
        }
        return nil
    }
    
    /// Start the Flask server
    /// - Parameters:
    ///   - projectPath: Path to the time_tracker project directory (for development mode)
    ///   - port: Port to run the server on (default 5001)
    func startServer(projectPath: String = "", port: Int = 5001) {
        guard !isRunning else { return }
        
        let process = Process()
        let pipe = Pipe()
        
        // Check if we have a bundled server
        if let bundledPath = bundledServerPath {
            // Use bundled server
            process.executableURL = URL(fileURLWithPath: bundledPath)
            process.arguments = ["--port", String(port)]
            print("Using bundled server at: \(bundledPath)")
        } else if !projectPath.isEmpty {
            // Fall back to development mode with pixi
            process.executableURL = URL(fileURLWithPath: "/bin/zsh")
            process.arguments = ["-c", "cd '\(projectPath)' && pixi run flask run --port \(port)"]
            process.environment = ProcessInfo.processInfo.environment
            process.environment?["FLASK_APP"] = "run.py"
            print("Using development server from: \(projectPath)")
        } else {
            print("No server available - neither bundled nor project path specified")
            serverOutput = "Error: No server available. Please configure the project path in Settings.\n"
            return
        }
        
        process.standardOutput = pipe
        process.standardError = pipe
        
        // Handle output
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if let output = String(data: data, encoding: .utf8), !output.isEmpty {
                DispatchQueue.main.async {
                    self?.serverOutput += output
                }
            }
        }
        
        // Handle termination
        process.terminationHandler = { [weak self] _ in
            DispatchQueue.main.async {
                self?.isRunning = false
                self?.process = nil
            }
        }
        
        do {
            try process.run()
            self.process = process
            self.outputPipe = pipe
            isRunning = true
            print("Flask server started on port \(port)")
        } catch {
            print("Failed to start Flask server: \(error)")
            serverOutput += "Failed to start: \(error.localizedDescription)\n"
        }
    }
    
    /// Check if a bundled server is available
    var hasBundledServer: Bool {
        return bundledServerPath != nil
    }
    
    /// Stop the Flask server
    func stopServer() {
        guard let process = process, isRunning else { return }
        
        // Send SIGTERM to gracefully stop
        process.terminate()
        
        // Give it a moment, then force kill if needed
        DispatchQueue.global().asyncAfter(deadline: .now() + 2) { [weak self] in
            if self?.process?.isRunning == true {
                self?.process?.interrupt()
            }
        }
        
        outputPipe?.fileHandleForReading.readabilityHandler = nil
        self.process = nil
        self.outputPipe = nil
        isRunning = false
        print("Flask server stopped")
    }
    
    deinit {
        stopServer()
    }
}

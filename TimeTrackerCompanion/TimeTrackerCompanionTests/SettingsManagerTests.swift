// SettingsManagerTests.swift
// TimeTrackerCompanionTests
//
// Property-based tests for SettingsManager persistence

import XCTest
@testable import TimeTrackerCompanion

/// Property test for settings persistence round-trip
/// **Validates: Requirements 4.4**
///
/// Property 9: Settings persistence round-trip
/// For any settings value (interval, URL, default group), saving the value
/// and then reading it back (including after simulated restart) SHALL return the same value.
final class SettingsManagerTests: XCTestCase {
    
    private let testSuiteName = "SettingsManagerTests"
    private var testDefaults: UserDefaults!
    
    override func setUp() {
        super.setUp()
        // Use a separate UserDefaults suite for testing to avoid polluting real settings
        testDefaults = UserDefaults(suiteName: testSuiteName)
        testDefaults?.removePersistentDomain(forName: testSuiteName)
    }
    
    override func tearDown() {
        testDefaults?.removePersistentDomain(forName: testSuiteName)
        testDefaults = nil
        super.tearDown()
    }
    
    // MARK: - Property Test: Settings Persistence Round-Trip
    
    /// Property 9: Settings persistence round-trip
    /// **Validates: Requirements 4.4**
    ///
    /// Tests that for any valid settings values, saving and reading back
    /// (simulating app restart) returns the same values.
    func testPropertySettingsPersistenceRoundTrip() {
        // Run 100 iterations with random values as per design document
        for iteration in 0..<100 {
            // Generate random valid settings
            let randomInterval = Int.random(in: 1...120)
            let randomPort = Int.random(in: 1000...9999)
            let randomURL = "http://localhost:\(randomPort)"
            let randomGroupId: Int? = Bool.random() ? Int.random(in: 1...1000) : nil
            let randomLaunchAtLogin = Bool.random()
            
            // Clear UserDefaults before each iteration
            let keys = ["promptInterval", "backendURL", "defaultGroupId", "launchAtLogin"]
            keys.forEach { UserDefaults.standard.removeObject(forKey: $0) }
            
            // Create first instance and set values
            let manager1 = SettingsManager()
            manager1.promptIntervalMinutes = randomInterval
            manager1.backendURL = randomURL
            manager1.defaultGroupId = randomGroupId
            manager1.launchAtLogin = randomLaunchAtLogin
            
            // Simulate app restart by creating a new instance
            // This reads values from UserDefaults
            let manager2 = SettingsManager()
            
            // Verify round-trip persistence
            XCTAssertEqual(
                manager2.promptIntervalMinutes, randomInterval,
                "Iteration \(iteration): promptIntervalMinutes should persist. Expected \(randomInterval), got \(manager2.promptIntervalMinutes)"
            )
            XCTAssertEqual(
                manager2.backendURL, randomURL,
                "Iteration \(iteration): backendURL should persist. Expected \(randomURL), got \(manager2.backendURL)"
            )
            XCTAssertEqual(
                manager2.defaultGroupId, randomGroupId,
                "Iteration \(iteration): defaultGroupId should persist. Expected \(String(describing: randomGroupId)), got \(String(describing: manager2.defaultGroupId))"
            )
            XCTAssertEqual(
                manager2.launchAtLogin, randomLaunchAtLogin,
                "Iteration \(iteration): launchAtLogin should persist. Expected \(randomLaunchAtLogin), got \(manager2.launchAtLogin)"
            )
        }
    }
    
    // MARK: - Default Values Tests
    
    /// Verify default values are set correctly on fresh install
    func testDefaultValues() {
        // Clear all settings
        let keys = ["promptInterval", "backendURL", "defaultGroupId", "launchAtLogin"]
        keys.forEach { UserDefaults.standard.removeObject(forKey: $0) }
        
        let manager = SettingsManager()
        
        XCTAssertEqual(manager.promptIntervalMinutes, 30, "Default interval should be 30 minutes")
        XCTAssertEqual(manager.backendURL, "http://localhost:5000", "Default URL should be http://localhost:5000")
        XCTAssertNil(manager.defaultGroupId, "Default group ID should be nil")
        XCTAssertFalse(manager.launchAtLogin, "Default launchAtLogin should be false")
    }
    
    // MARK: - Individual Property Persistence Tests
    
    /// Test promptIntervalMinutes persistence with various values
    func testPromptIntervalPersistence() {
        let keys = ["promptInterval"]
        keys.forEach { UserDefaults.standard.removeObject(forKey: $0) }
        
        let testValues = [15, 30, 45, 60, 90, 120]
        
        for value in testValues {
            let manager1 = SettingsManager()
            manager1.promptIntervalMinutes = value
            
            let manager2 = SettingsManager()
            XCTAssertEqual(manager2.promptIntervalMinutes, value, "Interval \(value) should persist")
        }
    }
    
    /// Test backendURL persistence with various URLs
    func testBackendURLPersistence() {
        UserDefaults.standard.removeObject(forKey: "backendURL")
        
        let testURLs = [
            "http://localhost:5000",
            "http://localhost:8080",
            "http://192.168.1.100:5000",
            "https://api.example.com"
        ]
        
        for url in testURLs {
            let manager1 = SettingsManager()
            manager1.backendURL = url
            
            let manager2 = SettingsManager()
            XCTAssertEqual(manager2.backendURL, url, "URL \(url) should persist")
        }
    }
    
    /// Test defaultGroupId persistence including nil values
    func testDefaultGroupIdPersistence() {
        UserDefaults.standard.removeObject(forKey: "defaultGroupId")
        
        // Test with a value
        let manager1 = SettingsManager()
        manager1.defaultGroupId = 42
        
        let manager2 = SettingsManager()
        XCTAssertEqual(manager2.defaultGroupId, 42, "Group ID 42 should persist")
        
        // Test setting back to nil
        manager2.defaultGroupId = nil
        
        let manager3 = SettingsManager()
        XCTAssertNil(manager3.defaultGroupId, "nil group ID should persist")
    }
    
    /// Test launchAtLogin persistence
    func testLaunchAtLoginPersistence() {
        UserDefaults.standard.removeObject(forKey: "launchAtLogin")
        
        let manager1 = SettingsManager()
        manager1.launchAtLogin = true
        
        let manager2 = SettingsManager()
        XCTAssertTrue(manager2.launchAtLogin, "launchAtLogin true should persist")
        
        manager2.launchAtLogin = false
        
        let manager3 = SettingsManager()
        XCTAssertFalse(manager3.launchAtLogin, "launchAtLogin false should persist")
    }
}

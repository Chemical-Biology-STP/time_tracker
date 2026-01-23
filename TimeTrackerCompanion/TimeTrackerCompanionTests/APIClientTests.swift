// APIClientTests.swift
// TimeTrackerCompanionTests
//
// Property-based tests for APIClient connection state tracking

import XCTest
@testable import TimeTrackerCompanion

/// Property test for connection state tracking
/// **Validates: Requirements 6.2, 6.3**
///
/// Property 12: Connection state tracking
/// For any sequence of API calls, if 3 or more consecutive calls fail,
/// the isConnected state SHALL be false. When a call succeeds after failures,
/// isConnected SHALL become true and consecutiveFailures SHALL reset to 0.
final class APIClientTests: XCTestCase {
    
    // MARK: - Property Test: Connection State Tracking
    
    /// Property 12: Connection state tracking
    /// **Validates: Requirements 6.2, 6.3**
    ///
    /// Tests that for any sequence of success/failure API results,
    /// the connection state machine transitions correctly.
    func testPropertyConnectionStateTracking() {
        // Run 100 iterations with random sequences as per design document
        for iteration in 0..<100 {
            let client = APIClient()
            
            // Generate a random sequence of success/failure events (5-20 events)
            let sequenceLength = Int.random(in: 5...20)
            var sequence: [Bool] = []
            for _ in 0..<sequenceLength {
                sequence.append(Bool.random())
            }
            
            // Track expected state
            var expectedConsecutiveFailures = 0
            var expectedIsConnected = false
            
            // Apply each event and verify state synchronously
            for (index, isSuccess) in sequence.enumerated() {
                if isSuccess {
                    client.simulateSuccessSync()
                    expectedConsecutiveFailures = 0
                    expectedIsConnected = true
                } else {
                    client.simulateFailureSync()
                    expectedConsecutiveFailures += 1
                    if expectedConsecutiveFailures >= 3 {
                        expectedIsConnected = false
                    }
                }
                
                // Verify state matches expected
                XCTAssertEqual(
                    client.consecutiveFailures, expectedConsecutiveFailures,
                    "Iteration \(iteration), event \(index): consecutiveFailures mismatch. " +
                    "Expected \(expectedConsecutiveFailures), got \(client.consecutiveFailures). " +
                    "Sequence so far: \(sequence.prefix(index + 1).map { $0 ? "S" : "F" })"
                )
                XCTAssertEqual(
                    client.isConnected, expectedIsConnected,
                    "Iteration \(iteration), event \(index): isConnected mismatch. " +
                    "Expected \(expectedIsConnected), got \(client.isConnected). " +
                    "Sequence so far: \(sequence.prefix(index + 1).map { $0 ? "S" : "F" })"
                )
            }
        }
    }
    
    // MARK: - Specific State Transition Tests
    
    /// Test that 3 consecutive failures marks as disconnected
    func testThreeConsecutiveFailuresDisconnects() {
        let client = APIClient()
        
        // Initial state
        XCTAssertEqual(client.consecutiveFailures, 0)
        XCTAssertFalse(client.isConnected)
        
        // First failure
        client.simulateFailureSync()
        XCTAssertEqual(client.consecutiveFailures, 1)
        XCTAssertFalse(client.isConnected) // Still false (was never connected)
        
        // Second failure
        client.simulateFailureSync()
        XCTAssertEqual(client.consecutiveFailures, 2)
        XCTAssertFalse(client.isConnected)
        
        // Third failure - should mark as disconnected
        client.simulateFailureSync()
        XCTAssertEqual(client.consecutiveFailures, 3)
        XCTAssertFalse(client.isConnected)
    }
    
    /// Test that success after failures resets state
    func testSuccessResetsFailures() {
        let client = APIClient()
        
        // Simulate 2 failures
        client.simulateFailureSync()
        client.simulateFailureSync()
        XCTAssertEqual(client.consecutiveFailures, 2)
        
        // Success should reset
        client.simulateSuccessSync()
        XCTAssertEqual(client.consecutiveFailures, 0)
        XCTAssertTrue(client.isConnected)
    }
    
    /// Test that success after 3+ failures reconnects
    func testSuccessAfterDisconnectReconnects() {
        let client = APIClient()
        
        // Simulate 3 failures to disconnect
        client.simulateFailureSync()
        client.simulateFailureSync()
        client.simulateFailureSync()
        XCTAssertFalse(client.isConnected)
        XCTAssertEqual(client.consecutiveFailures, 3)
        
        // Success should reconnect
        client.simulateSuccessSync()
        XCTAssertTrue(client.isConnected)
        XCTAssertEqual(client.consecutiveFailures, 0)
    }
    
    /// Test that success marks as connected
    func testSuccessMarksConnected() {
        let client = APIClient()
        
        XCTAssertFalse(client.isConnected)
        
        client.simulateSuccessSync()
        
        XCTAssertTrue(client.isConnected)
        XCTAssertEqual(client.consecutiveFailures, 0)
    }
    
    /// Test alternating success/failure pattern
    func testAlternatingSuccessFailure() {
        let client = APIClient()
        
        // Success -> connected
        client.simulateSuccessSync()
        XCTAssertTrue(client.isConnected)
        XCTAssertEqual(client.consecutiveFailures, 0)
        
        // Failure -> still connected (only 1 failure)
        client.simulateFailureSync()
        XCTAssertTrue(client.isConnected) // Still connected, only 1 failure
        XCTAssertEqual(client.consecutiveFailures, 1)
        
        // Success -> reset failures
        client.simulateSuccessSync()
        XCTAssertTrue(client.isConnected)
        XCTAssertEqual(client.consecutiveFailures, 0)
        
        // Failure -> still connected
        client.simulateFailureSync()
        XCTAssertTrue(client.isConnected)
        XCTAssertEqual(client.consecutiveFailures, 1)
    }
}

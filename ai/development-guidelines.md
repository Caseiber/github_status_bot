# Development Guidelines - Keep It Simple

## Overview

This document provides practical guidance for maintaining simplicity during technical implementation. These guidelines help prevent over-engineering while ensuring thorough testing and real-world reliability.

## Core Principles

### 🎯 **Build for Real Behavior**
Test every feature by actually exercising it as intended, not just as isolated code

### 🧹 **Start Simple, Iterate**
Write the simplest solution that works, then improve based on actual needs

### 🔍 **Test Like a Consumer**
Focus on "does the system behave correctly end-to-end?" not just "does this function return the right value?"

### ⚡ **Measure Before Optimizing**
Don't solve performance problems that don't exist yet

---

## API & Backend Development

### ❌ **Don't Over-Complicate**

- **Excessive Middleware**: Avoid layering abstractions for basic error handling
- **Complex Abstractions**: Don't build elaborate abstraction layers before you need them
- **Premature Optimization**: Don't add caching, rate limiting, or pooling from day one
- **Micro-Services for Everything**: Don't create separate goroutines or services for every operation

### ✅ **Do This Instead**

- **Start with Basic Error Handling**: Use simple, readable error paths
  ```go
  // Simple and effective
  result, err := processData(input)
  if err != nil {
      logger.Errorf("processing failed for %s: %v", input.Identity, err)
      return fmt.Errorf("process: %w", err)
  }
  ```

- **Test with Real Requests**: Use actual HTTP/WebSocket connections, not just unit tests
- **Helpful Error Responses**: Ensure errors are useful to callers and observable via metrics
- **One Thing at a Time**: Build features incrementally and verify each change

---

## File Structure & Organization

### ❌ **Don't Over-Organize**

- **Excessive Directories**: Avoid splitting a small package across many folders
- **File-Per-Function**: Don't split every function into its own file
- **Abstract Folder Names**: Don't use vague names like `core`, `shared`, `common`

### ✅ **Do This Instead**

- **Keep Related Code Together**: Group functionality logically by domain
  ```
  usecase/websocket/
    client.go       # readPump, writePump, serveWs
    hub.go          # Hub, run(), sendResult
    nonce_store.go  # NonceStore and eviction
    usecase.go      # Server, NewServer, Shutdown
  ```

- **Descriptive File Names**: Names should match their primary responsibility
- **Test Navigation**: A new team member should be able to find any file within two steps

---

## Testing Strategy

### ❌ **Don't Over-Test Implementation**

- **Mock Everything**: Don't mock every dependency in unit tests
- **Complex Test Code**: Avoid tests more complex than the code being tested
- **Implementation Details**: Don't test internal call sequences over observable behavior
- **Elaborate Test Fixtures**: Don't create complex mock data for simple tests

### ✅ **Do Focus on Real Behavior**

- **Integration Tests**: Write tests that exercise real workflows end-to-end
- **Actual Usage Testing**: Manually exercise the system during development
- **Edge Cases That Matter**: Test scenarios that will actually occur in production
- **Race Detector**: Run `go test -race ./...` for any concurrent code changes

---

## Practical Testing Guidelines

### 🧪 **Behavior-Focused Testing**

**Manual Verification Checklist:**
- [ ] Try to break the behavior with realistic edge cases
- [ ] Test with actual data volumes, not minimal fixtures
- [ ] Verify error paths are observable (logs, metrics)
- [ ] Exercise the feature for its intended purpose end-to-end

**Real-World Scenarios:**
- [ ] What happens when a dependency is slow or unavailable?
- [ ] How does the system behave under sustained load?
- [ ] Can the system recover from errors without leaking resources?
- [ ] Does concurrent access produce correct results?

### 🔗 **Integration Over Isolation**

**Integration Testing Priorities:**
- [ ] Test complete workflows end-to-end
- [ ] Use real connections and real data where practical
- [ ] Verify the full component interaction works together
- [ ] Test real concurrency scenarios with the race detector

---

## General Development Principles

### 🚫 **Avoid These Patterns**

- **Design Patterns for Pattern's Sake**: Don't apply patterns "because they're best practices"
- **Theoretical Future-Proofing**: Don't build for requirements that don't exist yet
- **Premature Abstractions**: Don't create abstractions before you have 3+ similar use cases
- **Performance Optimization**: Don't optimize before measuring actual bottlenecks

### ✅ **Follow These Instead**

- **Readable Code**: Write code that's easy to read and debug
- **Incremental Development**: Build the simplest solution that works, then improve
- **Actual Requirements**: Build for current, real needs
- **Measure First**: Use actual performance data to guide optimization

### 📏 **Simple Complexity Metrics**

**Red Flags (Time to Simplify):**
- Function has more than 20 lines
- File has more than 200 lines
- You can't explain the code in one sentence
- Test takes more than 30 seconds to run

**Green Flags (Good Simplicity):**
- New team member can understand the code in 5 minutes
- Tests read like documentation
- Error paths are explicit and observable
- Code changes require minimal updates elsewhere

---

## Quick Reference Checklist

Before submitting any change, verify:

### ✅ **Functionality**
- [ ] Feature works as intended when exercised manually
- [ ] Error cases are handled and observable via logs/metrics
- [ ] Performance is acceptable for real-world usage
- [ ] Code is readable and well-commented where non-obvious

### ✅ **Testing**
- [ ] Tests cover real workflows, not just code coverage
- [ ] `go build ./...` passes
- [ ] `go vet ./...` passes
- [ ] `go test -race ./...` passes for any concurrent code

### ✅ **Simplicity**
- [ ] Code solves the actual problem, not a theoretical one
- [ ] No unnecessary abstractions or over-engineering
- [ ] File structure is logical and navigable
- [ ] Documentation explains "why" not just "what"

---

*Remember: The best code is code that works reliably, is easy to understand, and solves real problems without unnecessary complexity.*

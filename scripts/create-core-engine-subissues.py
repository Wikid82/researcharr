#!/usr/bin/env python3
"""
Script to create sub-issues for Core Processing Engine Implementation (#94)
"""

import os

import requests

# GitHub API configuration
REPO_OWNER = "Wikid82"
REPO_NAME = "researcharr"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN environment variable not set")
    exit(1)

# Sub-issues for Core Processing Engine (#94) - organized by priority
CORE_ENGINE_ISSUES = [
    # CRITICAL PRIORITY - Foundation components that everything depends on
    {
        "title": "🏗️ Core Application Architecture Design",
        "body": """## Overview
Design and implement the foundational application architecture for the core processing engine.

## Related
- Parent Epic: #94 (🔧 Core Processing Engine Implementation)

## Tasks
- [ ] Define application architecture patterns and principles
- [ ] Design module structure and separation of concerns
- [ ] Create dependency injection and service container
- [ ] Implement application lifecycle management
- [ ] Design event/message bus architecture
- [ ] Create configuration and settings management
- [ ] Define error handling and logging strategies
- [ ] Document architectural decisions and patterns

## Acceptance Criteria
- Clear separation between application layers
- Dependency injection container works reliably
- Configuration system is flexible and extensible
- Architecture supports testing and modularity
- Documentation covers design decisions

## Definition of Done
- [ ] Architecture design document completed
- [ ] Core application framework implemented
- [ ] Basic dependency injection working
- [ ] Configuration system functional
- [ ] Unit tests for core components

## Priority
Critical - Foundation for all other components

## Estimated Effort
8 story points

## Technical Notes
- Consider using factory pattern for service creation
- Implement clean architecture principles
- Ensure testability from the start
""",
        "labels": [
            "alpha",
            "priority:critical",
            "type:epic",
            "component:core",
            "parent:94",
            "milestone:alpha-core",
        ],
    },
    {
        "title": "📡 Media Discovery Service Implementation",
        "body": """## Overview
Implement the core service responsible for discovering and indexing media content.

## Related
- Parent Epic: #94 (🔧 Core Processing Engine Implementation)

## Tasks
- [ ] Design media discovery interface and contracts
- [ ] Implement file system scanning capabilities
- [ ] Add support for multiple media sources (local, remote)
- [ ] Create media metadata extraction
- [ ] Implement incremental discovery and change detection
- [ ] Add filtering and exclusion rules
- [ ] Create discovery scheduling and triggers
- [ ] Add progress tracking and status reporting

## Acceptance Criteria
- Can discover media from multiple source types
- Metadata extraction works for common formats
- Incremental updates only process changes
- Discovery can be scheduled or triggered manually
- Progress and status are visible to users

## Definition of Done
- [ ] Discovery service interface defined
- [ ] File system discovery implemented
- [ ] Metadata extraction working
- [ ] Change detection functional
- [ ] Unit and integration tests pass

## Priority
Critical - Core functionality requirement

## Estimated Effort
13 story points

## Technical Notes
- Use async/await for I/O operations
- Consider using watchdog for file system events
- Plan for extensibility to other source types
""",
        "labels": [
            "alpha",
            "priority:critical",
            "type:feature",
            "component:core",
            "parent:94",
            "milestone:alpha-core",
        ],
    },
    {
        "title": "⚙️ Processing Pipeline Framework",
        "body": """## Overview
Create the core processing pipeline framework that handles media processing workflows.

## Related
- Parent Epic: #94 (🔧 Core Processing Engine Implementation)

## Tasks
- [ ] Design pipeline architecture and interfaces
- [ ] Implement pipeline execution engine
- [ ] Create step/stage abstraction for processing
- [ ] Add pipeline configuration and serialization
- [ ] Implement error handling and retry logic
- [ ] Add progress tracking and status updates
- [ ] Create pipeline templating system
- [ ] Add debugging and monitoring capabilities

## Acceptance Criteria
- Pipelines can be defined, configured, and executed
- Individual steps can be independently tested
- Error handling gracefully manages failures
- Progress tracking provides real-time updates
- Pipeline configuration is persistent and reusable

## Definition of Done
- [ ] Pipeline framework implemented
- [ ] Basic processing steps working
- [ ] Error handling and retry logic functional
- [ ] Configuration system integrated
- [ ] Comprehensive tests written

## Priority
Critical - Core processing capability

## Estimated Effort
13 story points

## Technical Notes
- Consider using async generators for pipeline flow
- Implement circuit breaker pattern for external calls
- Design for horizontal scaling in future
""",
        "labels": [
            "alpha",
            "priority:critical",
            "type:feature",
            "component:core",
            "parent:94",
            "milestone:alpha-core",
        ],
    },
    # HIGH PRIORITY - Important functionality needed for alpha
    {
        "title": "💾 Data Storage and Repository Layer",
        "body": """## Overview
Implement data storage abstractions and repository patterns for media and processing data.

## Related
- Parent Epic: #94 (🔧 Core Processing Engine Implementation)

## Tasks
- [ ] Design data models for media and processing state
- [ ] Implement repository pattern abstractions
- [ ] Create database schema and migrations
- [ ] Add data access layer with ORM/query builder
- [ ] Implement caching layer for performance
- [ ] Add data validation and constraints
- [ ] Create backup and recovery procedures
- [ ] Add database health monitoring

## Acceptance Criteria
- Data models support all required use cases
- Repository pattern abstracts storage implementation
- Database performance is acceptable for expected load
- Data integrity is maintained with constraints
- Caching improves response times

## Definition of Done
- [ ] Database schema designed and implemented
- [ ] Repository interfaces and implementations ready
- [ ] Data validation working
- [ ] Basic caching implemented
- [ ] Database tests pass

## Priority
High - Required for data persistence

## Estimated Effort
8 story points

## Technical Notes
- Use SQLAlchemy or similar ORM for flexibility
- Consider Redis for caching layer
- Plan for database migrations from start
""",
        "labels": [
            "alpha",
            "priority:high",
            "type:feature",
            "component:core",
            "parent:94",
            "milestone:alpha-core",
        ],
    },
    {
        "title": "🔄 Job Queue and Task Management",
        "body": """## Overview
Implement job queue system for managing background processing tasks.

## Related
- Parent Epic: #94 (🔧 Core Processing Engine Implementation)

## Tasks
- [ ] Design job queue architecture and interfaces
- [ ] Implement background task execution
- [ ] Add job priority and scheduling capabilities
- [ ] Create job status tracking and monitoring
- [ ] Implement job retry and failure handling
- [ ] Add job result storage and retrieval
- [ ] Create worker management and scaling
- [ ] Add job queue health monitoring

## Acceptance Criteria
- Jobs can be queued and executed asynchronously
- Job status and progress are trackable
- Failed jobs are retried with backoff strategy
- Job results are accessible when complete
- Worker processes can be monitored and managed

## Definition of Done
- [ ] Job queue system implemented
- [ ] Background workers functional
- [ ] Job status tracking working
- [ ] Retry logic implemented
- [ ] Monitoring capabilities added

## Priority
High - Essential for background processing

## Estimated Effort
8 story points

## Technical Notes
- Consider Celery, RQ, or similar task queue
- Plan for distributed workers in future
- Implement dead letter queue for failed jobs
""",
        "labels": [
            "alpha",
            "priority:high",
            "type:feature",
            "component:core",
            "parent:94",
            "milestone:alpha-core",
        ],
    },
    {
        "title": "📊 Core API and Service Layer",
        "body": """## Overview
Create the core API layer that exposes processing engine functionality.

## Related
- Parent Epic: #94 (🔧 Core Processing Engine Implementation)

## Tasks
- [ ] Design REST API architecture and endpoints
- [ ] Implement API routing and middleware
- [ ] Add request validation and serialization
- [ ] Create response formatting and error handling
- [ ] Implement API authentication and authorization
- [ ] Add rate limiting and throttling
- [ ] Create API documentation and OpenAPI spec
- [ ] Add API testing and validation

## Acceptance Criteria
- API endpoints expose all core functionality
- Request/response handling is robust and consistent
- Authentication and authorization work properly
- API documentation is complete and accurate
- Rate limiting prevents abuse

## Definition of Done
- [ ] Core API endpoints implemented
- [ ] Authentication middleware working
- [ ] Input validation functional
- [ ] API documentation generated
- [ ] Integration tests pass

## Priority
High - Required for UI and external integrations

## Estimated Effort
8 story points

## Technical Notes
- Use FastAPI or Flask for implementation
- Consider GraphQL for complex queries
- Implement proper HTTP status codes
""",
        "labels": [
            "alpha",
            "priority:high",
            "type:feature",
            "component:api",
            "parent:94",
            "milestone:alpha-core",
        ],
    },
    # MEDIUM PRIORITY - Important for alpha completeness
    {
        "title": "🏥 Health Monitoring and Diagnostics",
        "body": """## Overview
Implement comprehensive health monitoring and diagnostic capabilities for the core engine.

## Related
- Parent Epic: #94 (🔧 Core Processing Engine Implementation)

## Tasks
- [ ] Create health check endpoints for all services
- [ ] Implement system resource monitoring
- [ ] Add processing performance metrics
- [ ] Create diagnostic tools and utilities
- [ ] Implement alerting for critical issues
- [ ] Add self-healing capabilities where possible
- [ ] Create health dashboard and reporting
- [ ] Add troubleshooting guides and documentation

## Acceptance Criteria
- All critical services have health checks
- System performance can be monitored
- Critical issues trigger appropriate alerts
- Diagnostic tools help troubleshoot problems
- Health status is visible to administrators

## Definition of Done
- [ ] Health check system implemented
- [ ] Performance monitoring working
- [ ] Alerting system functional
- [ ] Diagnostic tools available
- [ ] Documentation complete

## Priority
Medium - Important for production readiness

## Estimated Effort
5 story points

## Technical Notes
- Use Prometheus-style metrics where possible
- Consider integrating with existing monitoring tools
- Plan for distributed system health monitoring
""",
        "labels": [
            "alpha",
            "priority:medium",
            "type:feature",
            "component:monitoring",
            "parent:94",
            "milestone:alpha-ops",
        ],
    },
    {
        "title": "🔧 Configuration and Settings Management",
        "body": """## Overview
Implement comprehensive configuration management for the core processing engine.

## Related
- Parent Epic: #94 (🔧 Core Processing Engine Implementation)

## Tasks
- [ ] Design configuration schema and validation
- [ ] Implement hierarchical configuration system
- [ ] Add environment-specific configurations
- [ ] Create configuration file format support (YAML, JSON, TOML)
- [ ] Implement hot-reload for configuration changes
- [ ] Add configuration validation and error reporting
- [ ] Create configuration backup and versioning
- [ ] Add configuration documentation and examples

## Acceptance Criteria
- Configuration is easily readable and maintainable
- Environment-specific overrides work correctly
- Invalid configurations are caught and reported
- Configuration changes can be applied without restart
- Documentation covers all configuration options

## Definition of Done
- [ ] Configuration system implemented
- [ ] File format support working
- [ ] Validation and error handling functional
- [ ] Hot-reload capability added
- [ ] Documentation complete

## Priority
Medium - Improves operational flexibility

## Estimated Effort
5 story points

## Technical Notes
- Use Pydantic or similar for validation
- Consider configuration encryption for secrets
- Plan for configuration management UI
""",
        "labels": [
            "alpha",
            "priority:medium",
            "type:feature",
            "component:core",
            "parent:94",
            "milestone:alpha-core",
        ],
    },
    # LOW PRIORITY - Nice to have, can be deferred
    {
        "title": "📈 Performance Optimization and Caching",
        "body": """## Overview
Optimize core engine performance and implement strategic caching.

## Related
- Parent Epic: #94 (🔧 Core Processing Engine Implementation)

## Tasks
- [ ] Profile application performance and identify bottlenecks
- [ ] Implement result caching for expensive operations
- [ ] Add database query optimization
- [ ] Create async processing for I/O operations
- [ ] Implement connection pooling and resource management
- [ ] Add memory usage optimization
- [ ] Create performance benchmarking suite
- [ ] Document performance characteristics and limits

## Acceptance Criteria
- Core operations complete within acceptable time limits
- Memory usage is stable and predictable
- Database queries are optimized
- Caching improves response times significantly
- Performance benchmarks are established

## Definition of Done
- [ ] Performance profiling completed
- [ ] Key optimizations implemented
- [ ] Caching system working
- [ ] Benchmarking suite available
- [ ] Performance documentation written

## Priority
Low - Optimization can be done after core functionality

## Estimated Effort
8 story points

## Technical Notes
- Use profiling tools to identify actual bottlenecks
- Consider Redis for distributed caching
- Plan for horizontal scaling optimizations
""",
        "labels": [
            "alpha",
            "priority:low",
            "type:enhancement",
            "component:core",
            "parent:94",
            "milestone:alpha-perf",
        ],
    },
]


def create_issue(issue_data):
    """Create a GitHub issue"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    response = requests.post(url, headers=headers, json=issue_data, timeout=30)
    if response.status_code == 201:
        issue = response.json()
        print(f"✅ Created sub-issue #{issue['number']}: {issue['title']}")
        return issue
    else:
        print(f"❌ Failed to create issue: {issue_data['title']}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def update_parent_issue():
    """Update issue #94 with links to sub-issues"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/94"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # Get current issue
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        print("❌ Failed to get parent issue #94")
        return

    current_issue = response.json()
    current_body = current_issue["body"]

    # Add sub-issues section
    sub_issues_section = """

## 🏗️ Sub-Issues Breakdown

This epic has been broken down into prioritized sub-issues:

### 🚨 Critical Priority - Foundation
- [ ] #105+ 🏗️ Core Application Architecture Design (8 pts)
- [ ] #106+ 📡 Media Discovery Service Implementation (13 pts)
- [ ] #107+ ⚙️ Processing Pipeline Framework (13 pts)

### 🔥 High Priority - Core Features
- [ ] #108+ 💾 Data Storage and Repository Layer (8 pts)
- [ ] #109+ 🔄 Job Queue and Task Management (8 pts)
- [ ] #110+ 📊 Core API and Service Layer (8 pts)

### 📋 Medium Priority - Operations
- [ ] #111+ 🏥 Health Monitoring and Diagnostics (5 pts)
- [ ] #112+ 🔧 Configuration and Settings Management (5 pts)

### 💭 Low Priority - Optimization
- [ ] #113+ 📈 Performance Optimization and Caching (8 pts)

**Total Effort:** 76 story points

## 🎯 Implementation Strategy

### Phase 1: Foundation (Weeks 1-3)
Start with **Critical Priority** items - these are blockers for everything else:
1. Core Architecture (#105) - Establishes patterns
2. Media Discovery (#106) - Core functionality
3. Pipeline Framework (#107) - Processing capability

### Phase 2: Integration (Weeks 4-6)
Add **High Priority** items to make it functional:
4. Data Storage (#108) - Persistence
5. Job Queue (#109) - Background processing
6. Core API (#110) - External interface

### Phase 3: Operations (Weeks 7-8)
Complete **Medium Priority** for alpha readiness:
7. Health Monitoring (#111) - Operational visibility
8. Configuration Management (#112) - Flexibility

### Phase 4: Optimization (Future)
**Low Priority** can be done post-alpha:
9. Performance Optimization (#113) - When needed

## 📊 Progress Tracking
- **Current Phase**: Sub-issue creation complete
- **Next Step**: Begin Core Architecture Design (#105)
- **Blockers**: None currently identified
- **Dependencies**: Plugin System (#95) can start in parallel

"""

    updated_body = current_body + sub_issues_section

    update_data = {"body": updated_body}

    response = requests.patch(url, headers=headers, json=update_data, timeout=30)
    if response.status_code == 200:
        print("✅ Updated parent issue #94 with sub-issue roadmap")
    else:
        print("❌ Failed to update parent issue #94")


def main():
    print("🔧 Creating sub-issues for Core Processing Engine (#94)...")
    print(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    print()

    # Group by priority for reporting
    priority_groups = {"Critical": [], "High": [], "Medium": [], "Low": []}

    created_issues = []
    total_effort = 0

    for issue_data in CORE_ENGINE_ISSUES:
        issue = create_issue(issue_data)
        if issue:
            created_issues.append(issue)

            # Extract effort points
            body = issue_data["body"]
            if "story points" in body:
                import re

                effort_match = re.search(r"(\d+)\s+story points", body)
                if effort_match:
                    total_effort += int(effort_match.group(1))

            # Categorize by priority
            priority = "Medium"  # default
            for label in issue_data["labels"]:
                if "priority:critical" in label:
                    priority = "Critical"
                elif "priority:high" in label:
                    priority = "High"
                elif "priority:medium" in label:
                    priority = "Medium"
                elif "priority:low" in label:
                    priority = "Low"
            priority_groups[priority].append(issue)

    print(f"\n✨ Created {len(created_issues)} sub-issues for Core Processing Engine!")
    print(f"📊 Total Estimated Effort: {total_effort} story points")

    print("\n🎯 Issues by Priority:")
    for priority, issues in priority_groups.items():
        if issues:
            priority_effort = 0
            for issue in issues:
                # Calculate effort for this priority
                for orig_issue in CORE_ENGINE_ISSUES:
                    if issue["title"] == orig_issue["title"]:
                        body = orig_issue["body"]
                        if "story points" in body:
                            import re

                            effort_match = re.search(r"(\d+)\s+story points", body)
                            if effort_match:
                                priority_effort += int(effort_match.group(1))
                        break

            print(f"\n{priority} Priority ({len(issues)} issues, {priority_effort} pts):")
            for issue in issues:
                print(f"  - #{issue['number']}: {issue['title']}")

    # Update parent issue
    print("\n🔗 Updating parent issue #94...")
    update_parent_issue()

    print("\n🚀 Recommended Next Steps:")
    print("1. Start with #105 (Core Architecture) - assign and move to 'In Progress'")
    print("2. Plan #106 (Media Discovery) for parallel development")
    print("3. #107 (Pipeline Framework) depends on architecture completion")
    print("4. Use project board to track progress through phases")
    print("5. Critical items should be completed before moving to high priority")

    print("\nAll sub-issues will automatically appear in your project board! 🎯")


if __name__ == "__main__":
    main()

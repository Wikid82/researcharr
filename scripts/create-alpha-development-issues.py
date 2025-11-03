#!/usr/bin/env python3
"""
Script to create comprehensive project development and alpha tracking issues
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

# Alpha and Development Issues - organized by priority
ALPHA_DEVELOPMENT_ISSUES = [
    # CRITICAL PRIORITY - Core functionality that must work
    {
        "title": "🔧 Core Processing Engine Implementation",
        "body": """## Overview
Implement the core processing engine that handles media discovery and processing workflows.

## Scope
Alpha milestone - Core functionality

## Tasks
- [ ] Design core processing architecture
- [ ] Implement media discovery mechanisms
- [ ] Create processing pipeline framework
- [ ] Add basic error handling and logging
- [ ] Create configuration management system
- [ ] Add basic testing for core functions
- [ ] Document core API and workflows

## Acceptance Criteria
- Core engine can discover and process media
- Basic configuration system works
- Essential error handling prevents crashes
- Core functionality is testable

## Priority
Critical - Foundation for all other features

## Effort
21 story points

## Alpha Milestone
Core Engine v1 - Essential for alpha release
""",
        "labels": [
            "alpha",
            "priority:critical",
            "type:epic",
            "component:core",
            "milestone:alpha-core",
        ],
    },
    {
        "title": "🔗 Plugin System Foundation",
        "body": """## Overview
Establish the plugin system architecture that allows extensible functionality.

## Scope
Alpha milestone - Extensibility foundation

## Tasks
- [ ] Design plugin interface and contracts
- [ ] Implement plugin loading and management
- [ ] Create base plugin classes and utilities
- [ ] Add plugin configuration system
- [ ] Implement plugin lifecycle management
- [ ] Create example plugins for testing
- [ ] Document plugin development guide

## Acceptance Criteria
- Plugins can be loaded and managed
- Plugin interface is stable and documented
- Example plugins demonstrate functionality
- Plugin system is extensible

## Priority
Critical - Required for modular architecture

## Effort
13 story points

## Alpha Milestone
Plugin Foundation v1 - Enables community extensions
""",
        "labels": [
            "alpha",
            "priority:critical",
            "type:epic",
            "component:plugins",
            "milestone:alpha-core",
        ],
    },
    {
        "title": "📊 Basic Web UI Implementation",
        "body": """## Overview
Create a functional web interface for basic operations and monitoring.

## Scope
Alpha milestone - Essential user interface

## Tasks
- [ ] Design basic UI layout and navigation
- [ ] Implement core pages (dashboard, settings, logs)
- [ ] Add basic configuration management UI
- [ ] Create status monitoring and health checks
- [ ] Implement basic authentication
- [ ] Add responsive design for mobile
- [ ] Create API endpoints for UI functionality

## Acceptance Criteria
- Web interface is functional and accessible
- Users can configure basic settings
- Status and health information is visible
- Authentication protects access
- Interface works on desktop and mobile

## Priority
Critical - Required for user interaction

## Effort
21 story points

## Alpha Milestone
Basic UI v1 - Essential user experience
""",
        "labels": [
            "alpha",
            "priority:critical",
            "type:epic",
            "component:ui",
            "milestone:alpha-core",
        ],
    },
    # HIGH PRIORITY - Important functionality for alpha
    {
        "title": "🔐 Authentication and Security System",
        "body": """## Overview
Implement secure authentication and basic security measures for alpha release.

## Scope
Alpha milestone - Security foundation

## Tasks
- [ ] Design authentication architecture
- [ ] Implement user management system
- [ ] Add session management
- [ ] Create secure API authentication
- [ ] Implement basic authorization/permissions
- [ ] Add security headers and protections
- [ ] Create password management features

## Acceptance Criteria
- Secure authentication works reliably
- API access is properly protected
- Basic security best practices implemented
- User management is functional

## Priority
High - Security essential for testing

## Effort
8 story points

## Alpha Milestone
Auth System v1 - Secure alpha testing
""",
        "labels": [
            "alpha",
            "priority:high",
            "type:feature",
            "component:security",
            "milestone:alpha-core",
        ],
    },
    {
        "title": "📈 Monitoring and Health Checks",
        "body": """## Overview
Implement monitoring, health checks, and basic metrics for alpha operations.

## Scope
Alpha milestone - Operational visibility

## Tasks
- [ ] Create health check endpoints
- [ ] Implement basic metrics collection
- [ ] Add system status monitoring
- [ ] Create performance monitoring
- [ ] Implement log aggregation
- [ ] Add alerting for critical issues
- [ ] Create monitoring dashboard

## Acceptance Criteria
- Health status is visible and accurate
- Basic metrics are collected and displayed
- Critical issues trigger alerts
- Performance can be monitored

## Priority
High - Essential for alpha stability

## Effort
8 story points

## Alpha Milestone
Monitoring v1 - Alpha operational visibility
""",
        "labels": [
            "alpha",
            "priority:high",
            "type:feature",
            "component:monitoring",
            "milestone:alpha-ops",
        ],
    },
    {
        "title": "⚙️ Configuration Management System",
        "body": """## Overview
Create comprehensive configuration management for alpha deployment and testing.

## Scope
Alpha milestone - Configuration foundation

## Tasks
- [ ] Design configuration schema and validation
- [ ] Implement file-based configuration
- [ ] Add environment variable support
- [ ] Create configuration UI in web interface
- [ ] Implement configuration validation and defaults
- [ ] Add configuration backup and restore
- [ ] Document configuration options

## Acceptance Criteria
- Configuration is easily manageable
- Validation prevents invalid settings
- Multiple configuration sources supported
- Documentation is comprehensive

## Priority
High - Required for alpha deployment

## Effort
5 story points

## Alpha Milestone
Config System v1 - Flexible alpha configuration
""",
        "labels": [
            "alpha",
            "priority:high",
            "type:feature",
            "component:core",
            "milestone:alpha-core",
        ],
    },
    # MEDIUM PRIORITY - Nice to have for alpha
    {
        "title": "🔄 Basic Scheduling and Automation",
        "body": """## Overview
Implement basic scheduling capabilities for automated processing workflows.

## Scope
Alpha milestone - Basic automation

## Tasks
- [ ] Design scheduling architecture
- [ ] Implement cron-like scheduling
- [ ] Add manual trigger capabilities
- [ ] Create job queue management
- [ ] Implement basic retry logic
- [ ] Add scheduling UI controls
- [ ] Create job status tracking

## Acceptance Criteria
- Basic scheduled jobs work reliably
- Manual triggering is available
- Job status is visible to users
- Simple retry logic handles failures

## Priority
Medium - Automation improves alpha testing

## Effort
8 story points

## Alpha Milestone
Scheduler v1 - Basic alpha automation
""",
        "labels": [
            "alpha",
            "priority:medium",
            "type:feature",
            "component:scheduler",
            "milestone:alpha-ops",
        ],
    },
    {
        "title": "📝 Basic Logging and Debugging",
        "body": """## Overview
Implement comprehensive logging and debugging capabilities for alpha development.

## Scope
Alpha milestone - Development support

## Tasks
- [ ] Set up structured logging framework
- [ ] Implement log levels and filtering
- [ ] Add debug logging for troubleshooting
- [ ] Create log viewing interface
- [ ] Implement log rotation and retention
- [ ] Add performance logging
- [ ] Create debugging utilities

## Acceptance Criteria
- Logs provide useful debugging information
- Log levels can be adjusted as needed
- Log viewing is user-friendly
- Performance impact is minimal

## Priority
Medium - Important for alpha debugging

## Effort
5 story points

## Alpha Milestone
Logging v1 - Alpha debugging support
""",
        "labels": [
            "alpha",
            "priority:medium",
            "type:feature",
            "component:core",
            "milestone:alpha-ops",
        ],
    },
    {
        "title": "🧪 Alpha Testing Framework",
        "body": """## Overview
Create testing framework and tools specifically for alpha validation and feedback.

## Scope
Alpha milestone - Testing infrastructure

## Tasks
- [ ] Set up alpha testing infrastructure
- [ ] Create integration test suite
- [ ] Implement smoke tests for deployments
- [ ] Add performance benchmarking
- [ ] Create test data and scenarios
- [ ] Implement automated test reporting
- [ ] Document testing procedures

## Acceptance Criteria
- Alpha testing can be automated
- Test results are comprehensive and clear
- Performance benchmarks are established
- Testing procedures are documented

## Priority
Medium - Quality assurance for alpha

## Effort
8 story points

## Alpha Milestone
Testing v1 - Alpha quality assurance
""",
        "labels": [
            "alpha",
            "priority:medium",
            "type:testing",
            "component:testing",
            "milestone:alpha-ops",
        ],
    },
    # LOW PRIORITY - Future enhancements
    {
        "title": "📦 Alpha Deployment and Packaging",
        "body": """## Overview
Create deployment packages and installation procedures for alpha testing.

## Scope
Alpha milestone - Deployment readiness

## Tasks
- [ ] Create Docker images for alpha
- [ ] Set up development deployment scripts
- [ ] Create installation documentation
- [ ] Implement basic update mechanisms
- [ ] Add deployment health checks
- [ ] Create backup and restore procedures
- [ ] Document deployment troubleshooting

## Acceptance Criteria
- Alpha can be deployed easily
- Installation documentation is clear
- Basic update mechanisms work
- Deployment issues can be diagnosed

## Priority
Low - Nice to have for alpha distribution

## Effort
5 story points

## Alpha Milestone
Deployment v1 - Alpha distribution ready
""",
        "labels": [
            "alpha",
            "priority:low",
            "type:infrastructure",
            "component:deployment",
            "milestone:alpha-dist",
        ],
    },
    {
        "title": "📋 Alpha Documentation and Guides",
        "body": """## Overview
Create essential documentation for alpha users and developers.

## Scope
Alpha milestone - User and developer documentation

## Tasks
- [ ] Write alpha user guide
- [ ] Create developer setup documentation
- [ ] Document API and plugin interfaces
- [ ] Create troubleshooting guide
- [ ] Add configuration reference
- [ ] Write contribution guidelines
- [ ] Create alpha testing guide

## Acceptance Criteria
- Alpha users can get started quickly
- Developers can contribute effectively
- Common issues have documented solutions
- API and plugin development is documented

## Priority
Low - Important for alpha adoption

## Effort
5 story points

## Alpha Milestone
Documentation v1 - Alpha user and developer guides
""",
        "labels": [
            "alpha",
            "priority:low",
            "type:documentation",
            "component:docs",
            "milestone:alpha-dist",
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
        print(f"✅ Created issue #{issue['number']}: {issue['title']}")
        return issue
    else:
        print(f"❌ Failed to create issue: {issue_data['title']}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def main():
    print("🚀 Creating Alpha Development tracking issues...")
    print(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    print()

    # Group issues by priority for better organization
    priority_groups = {"Critical": [], "High": [], "Medium": [], "Low": []}

    created_issues = []
    for issue_data in ALPHA_DEVELOPMENT_ISSUES:
        issue = create_issue(issue_data)
        if issue:
            created_issues.append(issue)
            # Determine priority from labels
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

    print(f"\n✨ Created {len(created_issues)} alpha development issues!")
    print("\n📊 Issues by Priority:")
    for priority, issues in priority_groups.items():
        if issues:
            print(f"\n{priority} Priority ({len(issues)} issues):")
            for issue in issues:
                print(f"  - #{issue['number']}: {issue['title']}")

    print("\n🎯 Recommended Alpha Development Flow:")
    print("1. CRITICAL: Start with Core Engine (#94), Plugin System (#95), Basic UI (#96)")
    print("2. HIGH: Add Auth System (#97), Monitoring (#98), Config Management (#99)")
    print("3. MEDIUM: Implement Scheduler (#100), Logging (#101), Testing Framework (#102)")
    print("4. LOW: Package for alpha distribution (#103), Create documentation (#104)")

    print("\n📋 Priority-Based Project Board Setup:")
    print("- Issues are labeled with priority:critical/high/medium/low")
    print("- Use GitHub's 'Sort by Labels' feature to organize by priority")
    print("- Create custom views in your project board filtered by priority")
    print("- The automation will still move items through your workflow columns")

    print("\nAll issues will automatically appear in your project board!")


if __name__ == "__main__":
    main()

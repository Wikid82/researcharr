#!/usr/bin/env python3
"""
Script to create GitHub issues for beta release tracking
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

# Issues to create for beta tracking
BETA_ISSUES = [
    {
        "title": "🚀 Beta Release Preparation - Core Stability",
        "body": """## Overview
This issue tracks the core stability improvements needed for beta release readiness.

## Tasks
- [ ] Complete test coverage analysis and improve to >90%
- [ ] Fix any critical bugs identified in testing
- [ ] Implement proper error handling and recovery mechanisms
- [ ] Add comprehensive logging for debugging production issues
- [ ] Performance testing and optimization
- [ ] Memory leak detection and prevention

## Acceptance Criteria
- All tests passing with >90% coverage
- No critical or high-severity bugs
- Performance benchmarks meet target thresholds
- Clean memory profile under load testing

## Priority
High - Blocking for beta release

## Estimated Effort
8 story points
""",
        "labels": ["beta", "priority:high", "type:epic"],
    },
    {
        "title": "📦 Package and Distribution System",
        "body": """## Overview
Implement native package distribution for beta testers across multiple platforms.

## Tasks
- [ ] Create DEB packages for Debian/Ubuntu
- [ ] Create Windows MSI/EXE installers
- [ ] Create macOS PKG or Homebrew formula
- [ ] Set up automated package building in CI
- [ ] Create installation documentation
- [ ] Test package installation on clean systems
- [ ] Set up package signing and verification

## Acceptance Criteria
- Native packages available for Linux, Windows, macOS
- Automated CI builds packages on releases
- Documentation covers installation on all platforms
- Packages are properly signed where applicable

## Priority
High - Required for beta distribution

## Estimated Effort
13 story points
""",
        "labels": ["beta", "priority:high", "type:feature", "component:packaging"],
    },
    {
        "title": "🔔 Notification System Implementation",
        "body": """## Overview
Implement webhook and notification system for beta release.

## Tasks
- [ ] Design notification architecture and API
- [ ] Implement webhook endpoints for external integrations
- [ ] Add Discord notification support (priority)
- [ ] Integrate Apprise for broad service support
- [ ] Add notification configuration UI
- [ ] Create notification templates and formatting
- [ ] Add notification testing and validation
- [ ] Document notification setup and usage

## Acceptance Criteria
- Webhook system supports external integrations
- Discord notifications work reliably
- Apprise integration supports major services
- Configuration is user-friendly
- Comprehensive documentation available

## Priority
Medium - Nice to have for beta

## Estimated Effort
8 story points
""",
        "labels": ["beta", "priority:medium", "type:feature", "component:notifications"],
    },
    {
        "title": "⚡ Event-Driven Processing Architecture",
        "body": """## Overview
Move away from cron-only scheduling to event-driven processing for better responsiveness.

## Tasks
- [ ] Design event-driven architecture
- [ ] Implement WebSocket support for real-time updates
- [ ] Create scheduler service or sidecar approach
- [ ] Add event queue and processing system
- [ ] Implement real-time UI updates
- [ ] Add event monitoring and debugging
- [ ] Performance testing of event system
- [ ] Documentation and migration guide

## Acceptance Criteria
- Event-driven processing works reliably
- WebSocket updates function in UI
- Performance is better than cron-based approach
- System is stable under load
- Migration path from existing setup

## Priority
Medium - Improvement for beta

## Estimated Effort
21 story points
""",
        "labels": ["beta", "priority:medium", "type:enhancement", "component:core"],
    },
    {
        "title": "🛠️ Release-Aware Processing",
        "body": """## Overview
Implement smart processing that handles release timing and avoids noisy updates.

## Tasks
- [ ] Design release detection system
- [ ] Implement configurable processing delays (default: 7 days)
- [ ] Add release date parsing and validation
- [ ] Skip items without release dates (configurable)
- [ ] Add release-aware filtering options
- [ ] Create UI controls for release settings
- [ ] Add release processing status indicators
- [ ] Test with various release scenarios

## Acceptance Criteria
- System respects release timing windows
- Configurable delay periods work correctly
- UI clearly shows release-aware status
- No false positives on release detection
- Performance impact is minimal

## Priority
Medium - Quality of life for beta

## Estimated Effort
5 story points
""",
        "labels": ["beta", "priority:medium", "type:feature", "component:core"],
    },
    {
        "title": "🔒 Security Audit and Hardening",
        "body": """## Overview
Comprehensive security review and hardening for beta release.

## Tasks
- [ ] Security audit of authentication system
- [ ] Review and secure API endpoints
- [ ] Input validation and sanitization review
- [ ] Dependency security scan and updates
- [ ] Container security hardening
- [ ] Secret management review
- [ ] Rate limiting and DOS protection
- [ ] Security documentation

## Acceptance Criteria
- No critical or high security vulnerabilities
- All inputs properly validated and sanitized
- Dependencies are up-to-date and secure
- Authentication is robust and tested
- Security best practices documented

## Priority
High - Critical for beta release

## Estimated Effort
8 story points
""",
        "labels": ["beta", "priority:critical", "type:security"],
    },
    {
        "title": "📖 Beta Documentation and User Guides",
        "body": """## Overview
Create comprehensive documentation for beta users.

## Tasks
- [ ] Update installation documentation
- [ ] Create user guide for common workflows
- [ ] Document API endpoints and usage
- [ ] Create troubleshooting guide
- [ ] Add configuration reference
- [ ] Create video tutorials (optional)
- [ ] Beta testing guide for users
- [ ] Known issues and limitations documentation

## Acceptance Criteria
- Documentation covers all major features
- Installation guides work on all platforms
- API documentation is complete and accurate
- Troubleshooting covers common issues
- Beta testers can self-serve most questions

## Priority
High - Required for beta success

## Estimated Effort
5 story points
""",
        "labels": ["beta", "priority:high", "type:documentation"],
    },
    {
        "title": "🧪 Beta Testing Infrastructure",
        "body": """## Overview
Set up infrastructure and processes for beta testing program.

## Tasks
- [ ] Create beta testing signup process
- [ ] Set up beta testing communication channels
- [ ] Create feedback collection system
- [ ] Set up crash reporting and telemetry
- [ ] Create beta testing guidelines
- [ ] Set up staging/beta deployment pipeline
- [ ] Create beta testing metrics dashboard
- [ ] Plan beta testing phases and milestones

## Acceptance Criteria
- Beta signup process is smooth and automated
- Feedback collection captures useful data
- Crash reporting works reliably
- Beta deployments are automated
- Clear testing phases and success criteria

## Priority
High - Infrastructure for beta program

## Estimated Effort
8 story points
""",
        "labels": ["beta", "priority:high", "type:infrastructure"],
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
    print("🚀 Creating beta release tracking issues...")
    print(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    print()

    created_issues = []
    for issue_data in BETA_ISSUES:
        issue = create_issue(issue_data)
        if issue:
            created_issues.append(issue)

    print(f"\n✨ Created {len(created_issues)} issues for beta tracking!")
    print("\nNext steps:")
    print("1. Review and prioritize the created issues")
    print("2. Assign team members to specific issues")
    print("3. Break down large issues into smaller tasks")
    print("4. Start working on high-priority items")
    print("\nThe issues will automatically be added to your project board!")


if __name__ == "__main__":
    main()

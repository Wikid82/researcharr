#!/usr/bin/env python3
"""
Script to add existing issues to the project board.
"""

import os

import requests


def get_project_id(owner, project_number, token):
    """Get the project ID from the project number."""
    # Try user query first, then organization
    user_query = """
    query($owner: String!, $projectNumber: Int!) {
        user(login: $owner) {
            projectV2(number: $projectNumber) {
                id
                fields(first: 20) {
                    nodes {
                        ... on ProjectV2Field {
                            id
                            name
                        }
                        ... on ProjectV2SingleSelectField {
                            id
                            name
                            options {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
    }
    """

    org_query = """
    query($owner: String!, $projectNumber: Int!) {
        organization(login: $owner) {
            projectV2(number: $projectNumber) {
                id
                fields(first: 20) {
                    nodes {
                        ... on ProjectV2Field {
                            id
                            name
                        }
                        ... on ProjectV2SingleSelectField {
                            id
                            name
                            options {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
    }
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Try user query first
    for query_type, query in [("user", user_query), ("organization", org_query)]:
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query, "variables": {"owner": owner, "projectNumber": project_number}},
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"📊 Trying {query_type} query...")

            if (
                "data" in data
                and data["data"][query_type]
                and data["data"][query_type]["projectV2"]
            ):
                project_data = data["data"][query_type]["projectV2"]
                print(f"✅ Found project ID: {project_data['id']}")

                # Find status field
                status_field_id = None
                status_options = {}

                for field in project_data["fields"]["nodes"]:
                    if field["name"] == "Status":
                        status_field_id = field["id"]
                        if "options" in field:
                            for option in field["options"]:
                                status_options[option["name"]] = option["id"]
                        break

                return project_data["id"], status_field_id, status_options
            else:
                print(f"❌ No project found with {query_type} query")
        else:
            print(f"❌ Failed to query {query_type}: {response.status_code}")
            if response.content:
                print(response.json())

    return None, None, None


def get_issue_ids(owner, repo, token, issue_numbers):
    """Get issue node IDs for the given issue numbers."""
    issue_ids = {}

    for issue_number in issue_numbers:
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

        if response.status_code == 200:
            issue_data = response.json()
            issue_ids[issue_number] = issue_data["node_id"]
            print(f"✅ Found issue #{issue_number}: {issue_data['title']}")
        else:
            print(f"❌ Failed to get issue #{issue_number}: {response.status_code}")

    return issue_ids


def add_issue_to_project(project_id, issue_id, token):
    """Add an issue to the project."""
    mutation = """
    mutation($projectId: ID!, $contentId: ID!) {
        addProjectV2ItemByContentId(input: {
            projectId: $projectId,
            contentId: $contentId
        }) {
            item {
                id
            }
        }
    }
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://api.github.com/graphql",
        headers=headers,
        json={"query": mutation, "variables": {"projectId": project_id, "contentId": issue_id}},
        timeout=30,
    )

    return response.status_code == 200


def main():
    # Configuration
    owner = "Wikid82"
    repo = "researcharr"
    project_number = 2

    # Issues to add (all the new issues we created)
    issue_numbers = list(range(80, 114))  # Issues #80-113

    # Get token from environment
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        return

    print(f"🚀 Adding {len(issue_numbers)} issues to project #{project_number}")

    # Get project data
    project_id, status_field_id, status_options = get_project_id(owner, project_number, token)
    if not project_id:
        return

    print(f"📋 Project ID: {project_id}")
    if status_options:
        print(f"📊 Status options: {list(status_options.keys())}")

    # Get issue node IDs
    print("\n📝 Getting issue data...")
    issue_ids = get_issue_ids(owner, repo, token, issue_numbers)

    # Add issues to project
    print(f"\n📌 Adding {len(issue_ids)} issues to project...")
    added_count = 0

    for issue_number, issue_id in issue_ids.items():
        if add_issue_to_project(project_id, issue_id, token):
            print(f"✅ Added issue #{issue_number} to project")
            added_count += 1
        else:
            print(f"❌ Failed to add issue #{issue_number} to project")

    print(f"\n🎉 Successfully added {added_count}/{len(issue_ids)} issues to the project board!")
    print("\n📍 Next steps:")
    print(f"1. Visit: https://github.com/users/{owner}/projects/{project_number}")
    print("2. Set up priority-based views using PRIORITY_SETUP_GUIDE.md")
    print("3. Move issues to appropriate columns (Backlog, In Progress, etc.)")


if __name__ == "__main__":
    main()

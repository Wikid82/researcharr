# GitHub Projects v2 Automation

This repository includes automated GitHub Projects v2 board management with the following features:

## Features

### Automated Project Board Management
- **Auto-add items**: New issues and pull requests are automatically added to the project board
- **Status transitions**: Items move through statuses based on their lifecycle:
  - New issues start in "Backlog"
  - Assigned issues move to "In Progress"
  - Closed issues move to "Done"
  - PRs ready for review move to "Review"
  - Merged/closed PRs move to "Done"
  - Items with "beta" labels move to "Beta Candidate"

### Custom Fields
- **Status**: Backlog, In Progress, Review, Done, Beta Candidate
- **Priority**: Low, Medium, High, Critical
- **Story Points**: Numeric field for effort estimation

### Multiple Views
- **Kanban Board**: Card-based view grouped by status
- **All Items**: Table view showing all fields

## Setup Instructions

### 1. Create the Project Board

Run the "Create Project Board" workflow manually:

1. Go to Actions → Create Project Board
2. Click "Run workflow"
3. Enter a project name (default: "Researcharr Development")
4. Enter a description (optional)
5. Click "Run workflow"

### 2. Update Project Number

After creating the project:

1. Note the project number from the workflow output
2. Update the `PROJECT_NUMBER` in `.github/workflows/project-automation.yml`
3. Update the `PROJECT_NUMBER` in `.github/workflows/sync-project.yml`

### 3. Sync Existing Issues (Optional)

To add existing issues and PRs to the project:

1. Go to Actions → Sync Issues to Project
2. Click "Run workflow"
3. Check "Sync existing issues and PRs to project"
4. Click "Run workflow"

## Workflow Files

- **`project-automation.yml`**: Main automation for real-time updates
- **`create-project.yml`**: One-time project creation
- **`sync-project.yml`**: Sync existing issues and PRs

## Customization

### Adding Custom Fields

Edit the `create-project.yml` workflow to add additional fields:

```yaml
# Add a custom single-select field
gh api graphql -f query='
  mutation($projectId: ID!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
    createProjectV2Field(input: {
      projectId: $projectId
      dataType: SINGLE_SELECT
      name: $name
      singleSelectOptions: $options
    }) {
      projectV2Field {
        ... on ProjectV2SingleSelectField {
          id
          name
        }
      }
    }
  }' -f projectId=$PROJECT_ID -f name="Component" -f options='[
    {name: "Frontend", color: "BLUE"},
    {name: "Backend", color: "GREEN"},
    {name: "Database", color: "PURPLE"}
  ]'
```

### Modifying Status Transitions

Edit the `project-automation.yml` workflow to change when items move between statuses. The automation currently handles:

- Issues opened → Backlog
- Issues assigned → In Progress
- Issues closed → Done
- Issues labeled with "beta" → Beta Candidate
- PRs opened → Backlog
- PRs ready for review → Review
- PRs merged/closed → Done

### Adding Custom Views

You can create additional views programmatically or through the GitHub UI:

```yaml
# Create a view filtered by priority
gh api graphql -f query='
  mutation($projectId: ID!, $name: String!) {
    createProjectV2View(input: {
      projectId: $projectId
      name: $name
      layout: TABLE_LAYOUT
    }) {
      projectV2View {
        id
        name
      }
    }
  }' -f projectId=$PROJECT_ID -f name="High Priority"
```

## Troubleshooting

### Permission Issues
Ensure the repository has access to the organization's projects and the `GITHUB_TOKEN` has sufficient permissions.

### Project Not Found
Verify the `PROJECT_NUMBER` is correct and the project exists in your organization/user account.

### GraphQL API Limits
The workflows include pagination and error handling, but for large repositories, you may need to adjust batch sizes.

## Manual Project Management

You can also manage the project manually through the GitHub UI:
1. Go to your repository
2. Click "Projects" tab
3. Select your project board
4. Drag and drop items between columns
5. Edit field values directly

The automation will respect manual changes and continue to work alongside manual updates.

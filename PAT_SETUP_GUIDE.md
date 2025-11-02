# PAT Setup Guide for Full Project Automation

## 🔑 Step 1: Create Personal Access Token (PAT)

1. **Go to GitHub Settings**: https://github.com/settings/personal-access-tokens/new

2. **Choose "Fine-grained personal access tokens"**

3. **Configure the token**:
   - **Token name**: `researcharr-project-automation`
   - **Expiration**: Choose your preferred duration (90 days recommended)
   - **Resource owner**: Select your account (Wikid82)
   - **Repository access**: Selected repositories → `researcharr`

4. **Set Repository permissions**:
   - `Issues`: **Write**
   - `Metadata`: **Read**
   - `Pull requests`: **Write**

5. **Set Account permissions**:
   - `Projects`: **Write** ⭐ (This is the critical permission!)

6. **Generate token** and copy it immediately

## 🔐 Step 2: Add PAT as Repository Secret

1. **Go to repository secrets**: https://github.com/Wikid82/researcharr/settings/secrets/actions

2. **Click "New repository secret"**

3. **Configure secret**:
   - **Name**: `PROJECT_TOKEN`
   - **Secret**: [Paste your PAT here]

4. **Click "Add secret"**

## 🚀 Step 3: Test the Automation

Once you've added the `PROJECT_TOKEN` secret:

### Option A: Run the bulk add workflow
```bash
# This will add all issues #80-113 to the project board
gh workflow run add-all-issues-to-project.yml
```

### Option B: Test with a single issue
```bash
# Create a test issue to verify automation works
gh issue create --title "🧪 Test Automation Issue" --body "Testing project board automation"
```

## 📊 Step 4: Verify Project Board Integration

1. **Check the workflow run**:
   ```bash
   gh run list --workflow=add-all-issues-to-project.yml
   ```

2. **Visit your project board**: https://github.com/users/Wikid82/projects/2

3. **Verify issues are added** and automatically set to "Backlog" status

## ⚙️ What the Automation Does

### Automatic Features (after PAT setup):
- ✅ **New issues** automatically added to project board
- ✅ **Status management** based on issue events
- ✅ **Column transitions** when issues are closed/reopened
- ✅ **Pull request integration** with project tracking

### Manual Features Available:
- 🔧 **Bulk issue sync** workflow (`add-all-issues-to-project.yml`)
- 🔧 **Individual issue sync** workflow (`sync-issues-to-project.yml`)
- 🔧 **Manual workflow triggers** for debugging

## 🔧 Troubleshooting

### If automation doesn't work:
1. **Check PAT permissions**: Ensure `Projects: Write` is enabled
2. **Verify secret name**: Must be exactly `PROJECT_TOKEN`
3. **Check workflow logs**: `gh run list` and `gh run view [run-id] --log`

### Rate limits:
- GitHub API allows 5000 requests/hour with PAT
- Workflows include delays to avoid hitting limits

## 📚 Next Steps

1. **Set up PAT and secret** (Steps 1-2 above)
2. **Run bulk add workflow** to sync existing issues
3. **Set up priority-based views** using `PRIORITY_SETUP_GUIDE.md`
4. **Start development** with issue #105 (Core Architecture Design)

## 🎯 Development Workflow

With automation enabled:
1. **Create issues** → Automatically added to project
2. **Move to "In Progress"** → Start working
3. **Create PR** → Linked to issue
4. **Merge PR** → Issue auto-moves to "Done"
5. **Mark as beta candidate** → Moves to "Beta Candidate" column

The automation handles all the project board management while you focus on development!
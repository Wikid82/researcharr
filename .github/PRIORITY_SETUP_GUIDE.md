# Priority-Based Project Board Setup Guide

This guide shows you how to organize your GitHub Projects v2 board by priority rather than issue numbers, making it easier to focus on the most important work first.

## 🏷️ Priority Label System

Issues are labeled with consistent priority levels:

- `priority:critical` - Must have for milestone (RED)
- `priority:high` - Important for milestone (ORANGE)
- `priority:medium` - Nice to have for milestone (YELLOW)
- `priority:low` - Future consideration (GREEN)

## 📊 Setting Up Priority-Based Views

### Method 1: Custom Project Views (Recommended)

1. **Go to your Project Board (#2)**
2. **Create Priority Views**:
   - Click "New View" → "Table View"
   - Name: "Critical Priority Items"
   - Add filter: `label:priority:critical`
   - Repeat for High, Medium, Low priorities

3. **Create Combined Priority View**:
   - Name: "All Items by Priority"
   - Sort by: Custom field "Priority" (if you have one) or use grouping
   - Group by: Labels containing "priority:"

### Method 2: Priority Field in Project

1. **Add Priority Field to Project**:
   - Go to your project settings
   - Add new field: "Priority" (Single Select)
   - Options: Critical, High, Medium, Low
   - Set colors: Red, Orange, Yellow, Green

2. **Sort by Priority Field**:
   - In any view, click "Sort"
   - Select "Priority" field
   - Order: Critical → High → Medium → Low

### Method 3: Label-Based Sorting

1. **In any Project View**:
   - Click the "Sort" dropdown
   - Select "Labels"
   - Issues will group by label alphabetically
   - Priority labels will naturally group together

## 🔄 Automated Priority Management

The project automation will work with priorities:

```yaml
# Issues with priority labels move to appropriate columns
- priority:critical → In Progress (when assigned)
- priority:high → In Progress (when assigned)
- priority:medium → Backlog (by default)
- priority:low → Backlog (by default)
```

## 📈 Priority-Based Kanban Board

### Recommended Column Setup:

1. **Critical & High** (Combined urgent work)
2. **In Progress** (Active work - any priority)
3. **Review** (Ready for review)
4. **Beta Candidate** (Ready for beta testing)
5. **Done** (Completed work)
6. **Medium & Low** (Future work)

### Board Filters by Priority:

**Critical Work View:**
- Filter: `label:priority:critical OR label:priority:high`
- Focus on urgent items only

**Full Backlog View:**
- No filters - see everything
- Sort by priority labels

**Future Planning View:**
- Filter: `label:priority:medium OR label:priority:low`
- Plan future iterations

## 🎯 Sprint Planning with Priorities

### Sprint Selection Strategy:

1. **Always include**: All `priority:critical` items
2. **Fill capacity with**: `priority:high` items
3. **Add if space**: `priority:medium` items
4. **Park for later**: `priority:low` items

### Effort vs Priority Matrix:

```
High Effort + Critical Priority = Plan carefully, break down
Low Effort + Critical Priority = Do immediately
High Effort + Low Priority = Consider deferring
Low Effort + Low Priority = Quick wins when available
```

## 🛠️ GitHub CLI Commands for Priority Management

### List issues by priority:
```bash
# Critical issues
gh issue list --label="priority:critical" --state=open

# All priorities sorted
gh issue list --label="priority:critical,priority:high,priority:medium,priority:low" --state=open
```

### Bulk update priorities:
```bash
# Add priority to existing issue
gh issue edit 123 --add-label="priority:high"

# Change priority
gh issue edit 123 --remove-label="priority:medium" --add-label="priority:high"
```

## 📊 Milestone Integration

Combine priorities with milestones for better planning:

- `milestone:alpha-core` + `priority:critical` = Must have for alpha
- `milestone:alpha-ops` + `priority:high` = Important for alpha
- `milestone:beta` + `priority:critical` = Beta blockers

### Query Examples:
```
milestone:alpha-core label:priority:critical
milestone:beta -label:priority:low
```

## 🔍 Advanced Filtering

### GitHub Issue Search Syntax:
```
# Critical items not in progress
label:priority:critical -label:status:in-progress

# High priority items assigned to you
label:priority:high assignee:@me

# Medium/Low priority items for future planning
label:priority:medium,priority:low milestone:future

# Alpha items by priority
milestone:alpha-core sort:label-desc
```

## 📱 Mobile-Friendly Priority Views

For mobile project management:

1. **Create "Priority Today" view**:
   - Filter: `label:priority:critical OR label:priority:high`
   - Compact card layout
   - Essential info only

2. **Use issue templates** with priority selection:
   - Pre-populate priority levels
   - Consistent labeling
   - Faster issue creation

## 🎨 Visual Priority Indicators

### Label Colors (Recommended):
- `priority:critical` - #d73a49 (Red)
- `priority:high` - #e36209 (Orange)
- `priority:medium` - #ffd33d (Yellow)
- `priority:low` - #28a745 (Green)

### Card Styling:
- Use consistent emoji in titles
- Critical: 🚨 or ⚡
- High: 🔥 or ⭐
- Medium: 📋 or ✨
- Low: 💭 or 🔮

---

**Pro Tip**: Start with Method 1 (Custom Views) as it's the most flexible and doesn't require changing your existing project structure!

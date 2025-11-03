# Coverage Gutters - Visual Quick Start Guide

## ✅ Setup Complete!

Your project now has:
- ✓ Coverage Gutters extension installed
- ✓ `coverage.xml` configured and ready
- ✓ VS Code settings optimized
- ✓ Test tasks configured

---

## 🚀 How to Use (3 Simple Steps)

### Step 1: Generate Coverage (Run Tests)

**Option A - Use VS Code Task (Recommended):**
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type: "Tasks: Run Test Task"
3. Press Enter
4. Watch tests run in the terminal panel

**Option B - Use Terminal:**
```bash
python -m pytest tests/ --cov=. --cov-report=xml
```

**Result:** Creates `coverage.xml` in your project root ✓

---

### Step 2: Enable Coverage Display

**Option A - Status Bar (Easiest):**
1. Look at the **bottom status bar** in VS Code
2. Click the **"Watch"** button (or coverage percentage if visible)
3. Coverage gutters activate!

**Option B - Command Palette:**
1. Press `Ctrl+Shift+P`
2. Type: "Coverage Gutters: Display Coverage"
3. Press Enter

**Option C - Keyboard Shortcut:**
- Default: `Ctrl+Shift+7` (Windows/Linux)
- Default: `Cmd+Shift+7` (Mac)

---

### Step 3: See Coverage in Your Code!

Once enabled, you'll see:

```
┌─────────────────────────────────────────┐
│ Line │ Gutter │ Code                   │
├─────────────────────────────────────────┤
│  1   │   🟢   │ def calculate(x, y):   │  ← Green = Covered
│  2   │   🟢   │     if x > 0:          │
│  3   │   🟢   │         return x + y   │
│  4   │   🔴   │     else:              │  ← Red = Not Covered
│  5   │   🔴   │         return x - y   │
│  6   │   🟡   │     return 0           │  ← Yellow = Partial
└─────────────────────────────────────────┘
```

**Visual indicators:**
- **Green gutter bar** = Line is covered by tests ✅
- **Red gutter bar** = Line is NOT covered ❌
- **Yellow gutter bar** = Line is partially covered ⚠️
- **Background highlighting** = Subtle color overlay on the line

---

## 📊 View Full Coverage Report

### HTML Report (Detailed)
1. Press `Ctrl+Shift+P`
2. Type: "Coverage Gutters: Preview Coverage Report"
3. Opens `htmlcov/index.html` in browser
4. Shows complete coverage tables, file-by-file

### Status Bar Percentage
- Bottom-right corner shows: **"Coverage: 42.84%"** (example)
- Click it to toggle coverage display on/off

---

## 🔄 Workflow Tips

### Watch Mode (Auto-Update)
1. Click **"Watch"** in the status bar
2. Coverage auto-refreshes when `coverage.xml` changes
3. Run tests → Coverage updates automatically! 🔥

### Quick Test → See Coverage Flow
```
1. Make code changes
2. Ctrl+Shift+P → "Tasks: Run Test Task"
3. Watch tests run
4. Coverage updates automatically (if Watch is on)
5. See green/red gutters update in your file!
```

### Focus on Specific Files
- Open a Python file in the editor
- Coverage Gutters shows coverage **only for that file**
- Switch files → Coverage updates for the new file

---

## 🎨 What You'll See (Visual Examples)

### Status Bar (Bottom of VS Code)
```
┌────────────────────────────────────────────────────────┐
│ [Watch] Coverage: 42.84%   Ln 25, Col 10   Python     │
│   ↑                ↑                                   │
│  Click to        Current                               │
│  toggle         coverage                               │
└────────────────────────────────────────────────────────┘
```

### Gutter Icons (Left Margin)
```
Line numbers  Gutters      Code
    23       │  🟢  │     def tested_function():
    24       │  🟢  │         return True
    25       │      │
    26       │  🔴  │     def untested_function():
    27       │  🔴  │         return False
```

### Scrollbar Overview (Right Side)
- Small colored marks show coverage throughout the file
- Green marks = covered sections
- Red marks = uncovered sections
- Click marks to jump to that line

---

## 🛠️ Common Actions

| Action | How To |
|--------|--------|
| **Show coverage** | Click "Watch" in status bar OR `Ctrl+Shift+7` |
| **Hide coverage** | Click status bar again OR `Ctrl+Shift+7` |
| **Update coverage** | Run tests (Watch mode auto-updates) |
| **See full report** | `Ctrl+Shift+P` → "Preview Coverage Report" |
| **Toggle watch mode** | Click "Watch" in status bar |

---

## 💡 Pro Tips

1. **Keep Watch Mode On**: Set it once, coverage updates after every test run
2. **Use Tasks**: `Ctrl+Shift+P` → "Run Test Task" is faster than typing commands
3. **Focus on Red Lines**: They show exactly what needs tests
4. **Check Partial Coverage**: Yellow lines often hide edge cases
5. **Compare Before/After**: Run tests, add test, run again, see green increase!

---

## 🎯 Your Current Setup

✓ **Coverage file**: `coverage.xml` (auto-generated)
✓ **HTML report**: `htmlcov/index.html`
✓ **Watch enabled**: Yes (auto-refresh)
✓ **Gutter icons**: Enabled
✓ **Line highlighting**: Enabled (subtle colors)
✓ **Scrollbar marks**: Enabled

**Current coverage**: Run tests to see your percentage!

---

## 🐛 Troubleshooting

**Coverage not showing?**
1. Ensure `coverage.xml` exists (check project root)
2. Click "Watch" in the status bar
3. Try: `Ctrl+Shift+P` → "Coverage Gutters: Display Coverage"
4. Check Output panel: View → Output → Select "Coverage Gutters"

**Wrong file covered?**
- Coverage Gutters shows coverage for the **currently open file**
- Make sure you're viewing the Python file you want to check

**Coverage not updating?**
- Click "Watch" in status bar to enable auto-refresh
- Or manually: `Ctrl+Shift+P` → "Coverage Gutters: Display Coverage"

---

## 📚 Next Steps

1. **Try it now:**
   - Run: `Ctrl+Shift+P` → "Tasks: Run Test Task"
   - Click "Watch" in status bar
   - Open any `.py` file
   - See the coverage! 🎉

2. **Explore:**
   - Open `htmlcov/index.html` for detailed report
   - Hover over yellow (partial) lines to understand branches
   - Use coverage to guide new test creation

3. **Customize:**
   - Edit `.vscode/settings.json` to change colors
   - Adjust coverage thresholds in `pyproject.toml`

---

## 🔗 More Info

- Extension: [Coverage Gutters on Marketplace](https://marketplace.visualstudio.com/items?itemName=ryanluker.vscode-coverage-gutters)
- Docs: [GitHub Repository](https://github.com/ryanluker/vscode-coverage-gutters)
- Your config: `.vscode/settings.json`
- Coverage config: `pyproject.toml`

---

**Ready to go!** 🚀 Just run tests and click "Watch" to see coverage in action.

# Coverage Gutters - Quick Reference Card

## 🎯 3-Step Quick Start

1. **Run Tests**
   ```
   Ctrl+Shift+P → "Tasks: Run Test Task"
   ```

2. **Click "Watch"** in status bar (bottom-right)

3. **Open any .py file** → See coverage! 🎉

---

## ⌨️ Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Toggle coverage | `Ctrl+Shift+7` |
| Run test task | `Ctrl+Shift+P` → type "test" |
| Command palette | `Ctrl+Shift+P` |

---

## 🎨 Visual Guide

### What You See

```
┌──────────────────────────────────┐
│ Ln │ Gutter │ Your Code         │
├──────────────────────────────────┤
│ 23 │   🟢   │ def func():       │ ← GREEN = Covered ✅
│ 24 │   🟢   │     return True   │
│ 25 │        │                   │
│ 26 │   🔴   │ def unused():     │ ← RED = Not covered ❌
│ 27 │   🔴   │     return False  │
│ 28 │        │                   │
│ 29 │   🟡   │ if x > 0:         │ ← YELLOW = Partial ⚠️
└──────────────────────────────────┘
```

### Status Bar
```
[Watch] Coverage: 42.84%  ← Click to toggle
```

---

## 📋 Common Commands

Type `Ctrl+Shift+P` then:

- `Coverage Gutters: Display Coverage` - Show coverage
- `Coverage Gutters: Watch` - Auto-update mode
- `Coverage Gutters: Remove Coverage` - Hide coverage
- `Coverage Gutters: Preview Coverage Report` - Open HTML report
- `Tasks: Run Test Task` - Run tests with coverage

---

## 📊 Reports

### Quick (Terminal)
```bash
python -m pytest tests/ --cov=. --cov-report=term
```

### Visual (Gutters in Editor)
1. Run tests
2. Click "Watch"
3. Open files

### Detailed (HTML)
```
Ctrl+Shift+P → "Coverage Gutters: Preview Coverage Report"
```
Opens `htmlcov/index.html`

---

## 🔄 Recommended Workflow

```
┌─────────────────────────────────────────┐
│ 1. Enable "Watch" mode (one time)       │
│    Click "Watch" in status bar          │
├─────────────────────────────────────────┤
│ 2. Write/edit code                      │
├─────────────────────────────────────────┤
│ 3. Run tests                            │
│    Ctrl+Shift+P → "Run Test Task"       │
├─────────────────────────────────────────┤
│ 4. Coverage updates automatically!      │
│    See green/red gutters                │
├─────────────────────────────────────────┤
│ 5. Add tests for red lines              │
├─────────────────────────────────────────┤
│ 6. Run tests again                      │
├─────────────────────────────────────────┤
│ 7. Watch red turn green! 🎉             │
└─────────────────────────────────────────┘
```

---

## 🐛 Quick Fixes

| Problem | Solution |
|---------|----------|
| No coverage showing | 1. Check `coverage.xml` exists<br>2. Click "Watch"<br>3. Run Display Coverage command |
| Wrong file coverage | Make sure correct .py file is open |
| Coverage not updating | Enable Watch mode |
| Can't find coverage file | Run tests first: `Ctrl+Shift+P` → "Run Test Task" |

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `coverage.xml` | Coverage data (auto-generated) |
| `htmlcov/index.html` | Detailed HTML report |
| `.vscode/settings.json` | Coverage Gutters config |
| `.vscode/tasks.json` | Test tasks |
| `pyproject.toml` | Pytest coverage settings |

---

## 💡 Pro Tips

✨ **Keep Watch On** - Set once, coverage auto-updates
✨ **Use Tasks** - `Ctrl+Shift+P` → "Run Test Task" is faster
✨ **Focus on Red** - Shows exactly what needs tests
✨ **Check Yellow** - Partial coverage = edge cases
✨ **Preview HTML** - Full detailed tables

---

## 🎯 Colors Meaning

| Color | Meaning | Action |
|-------|---------|--------|
| 🟢 Green | Line is covered by tests | ✅ Good! |
| 🔴 Red | Line NOT covered | ❌ Needs test |
| 🟡 Yellow | Partially covered (some branches) | ⚠️ Add more cases |
| ⚪ None | Not executable (comments, blanks) | - |

---

## 📖 Full Documentation

- **Quick Start (Visual):** `docs/Coverage-Gutters-Quick-Start.md`
- **Setup Guide:** `docs/Coverage-Gutters-Setup.md`
- **Example Comparison:** `docs/Coverage-Gutters-Example-Comparison.md`
- **Summary:** `COVERAGE_GUTTERS_SETUP_SUMMARY.md`

---

**Print this reference card or keep it open in a tab!** 📌

Now go forth and increase that coverage! 🚀

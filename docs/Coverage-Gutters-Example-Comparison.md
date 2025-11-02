# Coverage Gutters Example Structure

This document shows how the vscode-coverage-gutters Python example is structured,
and how our project aligns with it.

## Example Structure from vscode-coverage-gutters

```
example/python/
├── README.md
├── cov.xml                    # Coverage XML file
└── python/
    └── foobar/
        ├── __init__.py
        ├── bar/
        │   ├── __init__.py
        │   └── a.py           # Source code
        ├── foo/
        │   ├── __init__.py
        │   └── a.py           # Source code
        └── tests/
            ├── __init__.py
            └── test_sample.py # Tests
```

### Their Command (from README.md)
```bash
py.test foobar --cov-report xml:cov.xml --cov foobar
```

This generates:
- `cov.xml` - The coverage file that Coverage Gutters reads
- Coverage is collected from the `foobar` package

---

## Our Project Structure

```
researcharr/
├── pyproject.toml             # Our pytest config (includes coverage settings)
├── coverage.xml               # Generated coverage file ✓
├── htmlcov/
│   └── index.html             # HTML coverage report ✓
├── researcharr.py             # Main module (source)
├── factory.py                 # Factory module (source)
├── backups.py                 # Backups module (source)
├── webui.py                   # WebUI module (source)
├── api.py                     # API module (source)
├── run.py                     # Run module (source)
├── tests/                     # Test directory
│   ├── test_*.py              # Test files
│   └── conftest.py            # Pytest config
└── .vscode/
    ├── settings.json          # Coverage Gutters config ✓
    └── tasks.json             # Test tasks ✓
```

### Our Command (via pyproject.toml)
```bash
python -m pytest tests/ --cov=. --cov-report=xml
```

Or use the VS Code task: `Ctrl+Shift+P` → "Tasks: Run Test Task"

This generates:
- `coverage.xml` - Coverage file for Coverage Gutters ✓
- `htmlcov/index.html` - HTML report for detailed viewing ✓
- Terminal output with coverage summary ✓

---

## Configuration Comparison

### Their Setup (Manual)
```bash
# Install packages
pip install pytest pytest-cov

# Run with explicit options
py.test foobar --cov-report xml:cov.xml --cov foobar
```

### Our Setup (Pre-configured) ✓
```toml
# pyproject.toml already has:
[tool.pytest.ini_options]
addopts = "--cov=. --cov-report=xml --cov-report=html --cov-report=term-missing"
testpaths = ["tests"]

[tool.coverage.run]
source = ["."]
branch = true
```

**Benefits:**
- No need to remember command-line options
- Consistent coverage across all runs
- VS Code tasks make it one-click
- Multiple report formats (XML + HTML + terminal)

---

## Coverage Gutters Configuration

### Example Project (Minimal)
They rely on Coverage Gutters defaults:
- Looks for `cov.xml` in the workspace
- Shows coverage when extension is activated
- Basic green/red gutters

### Our Project (Enhanced) ✓
```json
// .vscode/settings.json
{
  "coverage-gutters.coverageFileNames": [
    "coverage.xml",      // Primary file
    "cov.xml",           // Fallback
    "lcov.info"          // Alternative format
  ],
  "coverage-gutters.coverageReportFileName": "htmlcov/index.html",
  "coverage-gutters.showGutterCoverage": true,
  "coverage-gutters.showLineCoverage": true,
  "coverage-gutters.showRulerCoverage": true,
  "coverage-gutters.highlightdark": "rgba(20, 200, 20, 0.3)",
  "coverage-gutters.noHighlightDark": "rgba(200, 20, 20, 0.3)",
  "coverage-gutters.partialHighlightDark": "rgba(200, 200, 20, 0.3)"
}
```

**Benefits:**
- Custom colors for better visibility
- Preview HTML reports with one command
- Multiple coverage file support
- Scrollbar overview enabled

---

## Key Differences

| Aspect | Example Project | Our Project |
|--------|----------------|-------------|
| **Coverage file** | `cov.xml` | `coverage.xml` |
| **Configuration** | Command-line args | `pyproject.toml` ✓ |
| **HTML report** | Not included | `htmlcov/index.html` ✓ |
| **VS Code settings** | None | `.vscode/settings.json` ✓ |
| **Tasks** | Manual commands | Pre-configured tasks ✓ |
| **Auto-watch** | Manual | Recommended in docs ✓ |

---

## Similarities (What Makes It Work)

Both projects:
1. ✓ Use `pytest` with `pytest-cov`
2. ✓ Generate XML coverage output
3. ✓ Place coverage file in project root
4. ✓ Use Coverage Gutters extension
5. ✓ Follow standard Python test structure

---

## How to Use (Quick Comparison)

### Example Project Way
```bash
# 1. Install dependencies
pip install pytest pytest-cov

# 2. Run tests with coverage
py.test foobar --cov-report xml:cov.xml --cov foobar

# 3. Open VS Code
code .

# 4. Manually activate Coverage Gutters
# (Click status bar or use command palette)
```

### Our Project Way ✓
```bash
# 1. Dependencies already in requirements.txt
# (pytest, pytest-cov already listed)

# 2. Run tests - ONE of these:
#    - Use VS Code: Ctrl+Shift+P → "Tasks: Run Test Task"
#    - Use terminal: python -m pytest
#    - (Coverage is automatic via pyproject.toml)

# 3. Coverage Gutters auto-configured
#    - Click "Watch" in status bar
#    - Done! Coverage shows automatically
```

---

## Migration Notes (If You Were Using Their Approach)

If you followed the example project's approach, here's what changes:

**Old way:**
```bash
py.test foobar --cov-report xml:cov.xml --cov foobar
```

**New way (our setup):**
```bash
python -m pytest  # That's it! Settings are in pyproject.toml
```

**Coverage file location:**
- Old: `cov.xml`
- New: `coverage.xml` (Coverage Gutters recognizes both)

**No other changes needed!** Coverage Gutters works the same way.

---

## Summary

Our project is **fully aligned** with the vscode-coverage-gutters example, but with enhancements:

✅ **Same core approach:**
- pytest + pytest-cov
- XML coverage output
- Coverage Gutters extension

🚀 **Added improvements:**
- Pre-configured via `pyproject.toml`
- VS Code tasks for one-click testing
- Custom colors and settings
- HTML report integration
- Comprehensive documentation

**Result:** Less typing, more coverage visibility! 🎉

---

## References

- Example: https://github.com/ryanluker/vscode-coverage-gutters/tree/main/example/python
- Extension: https://marketplace.visualstudio.com/items?itemName=ryanluker.vscode-coverage-gutters
- Our config: `.vscode/settings.json`, `pyproject.toml`
- Quick start: `docs/Coverage-Gutters-Quick-Start.md`

# Contributing to Hydro Suite Standalone

Thank you for your interest in contributing to Hydro Suite! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and professional in all interactions. We welcome contributions from everyone.

## Getting Started

### Prerequisites

- QGIS 3.40 or higher
- Python 3.9+ (included with QGIS)
- Git for version control
- Basic familiarity with PyQt5 and QGIS Python APIs

### Setting Up Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork locally:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/hydro-suite-standalone.git
   cd hydro-suite-standalone
   ```

3. **Add the upstream remote:**
   ```bash
   git remote add upstream https://github.com/Joeywoody124/hydro-suite-standalone.git
   ```

4. **Test the installation** in QGIS Python Console:
   ```python
   exec(open(r'path\to\hydro-suite-standalone\launch_hydro_suite.py').read())
   ```

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template if available
3. Include:
   - QGIS version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages or logs

### Suggesting Features

1. Open an issue with the "enhancement" label
2. Describe the feature and its use case
3. Explain why it would benefit users

### Submitting Code Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards below

3. **Test thoroughly** in QGIS

4. **Commit with clear messages:**
   ```bash
   git commit -m "Add: brief description of change"
   ```

5. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request** against the `main` branch

## Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use meaningful variable and function names

### Comments

We prefer inline comments over block comments:

```python
# Good: Inline comments
composite_cn = weighted_sum / total_area  # Calculate area-weighted average

# Avoid: Block comments for simple explanations
```

### Type Hints

Use type hints for function signatures:

```python
def calculate_cn(self, area: float, land_use: str) -> float:
    """Calculate curve number for given area and land use."""
    pass
```

### Docstrings

Use docstrings for all public functions and classes:

```python
def process_layer(self, layer: QgsVectorLayer) -> Dict[str, Any]:
    """
    Process a vector layer and extract relevant data.
    
    Args:
        layer: QGIS vector layer to process
        
    Returns:
        Dictionary with extracted data
        
    Raises:
        ValueError: If layer is invalid
    """
    pass
```

### Tool Structure

New tools should follow the existing pattern:

1. Inherit from `HydroToolInterface`
2. Implement required methods: `create_gui()`, `validate_inputs()`, `run()`
3. Use shared widgets for consistency
4. Include comprehensive error handling

See `DEVELOPER_GUIDE.md` for detailed instructions.

## Pull Request Process

1. Update the README.md if needed
2. Update CHANGELOG.md with your changes
3. Ensure all tests pass
4. Request review from maintainers
5. Address any feedback

### PR Title Format

Use descriptive titles:
- `Add: New TC calculation method`
- `Fix: Layer selection validation bug`
- `Update: Improve error handling in CN calculator`
- `Docs: Add troubleshooting guide`

## Testing

### Manual Testing

Test your changes in QGIS:
1. Launch Hydro Suite
2. Test all affected tools
3. Verify edge cases
4. Check error handling

### Test Data

If your changes require specific test data:
1. Use sample datasets if available
2. Document any test data requirements
3. Do not commit large files

## Documentation

- Update README.md for user-facing changes
- Update DEVELOPER_GUIDE.md for technical changes
- Add inline comments for complex code
- Update CHANGELOG.md

## Questions?

- Open an issue for questions
- Reference existing issues and PRs
- Check documentation first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Hydro Suite!

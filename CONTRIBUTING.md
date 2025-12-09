# Contributing to TenChat NeuroBooster

Thank you for your interest in contributing to TenChat NeuroBooster! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and Clone:**
```bash
git clone https://github.com/yourusername/TenChat_NeuroBooster_v1.git
cd TenChat_NeuroBooster_v1
```

2. **Create Virtual Environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

4. **Setup Environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Add docstrings to all functions and classes
- Keep functions focused and small
- Use meaningful variable names

## Testing

Before submitting a PR:

1. Test all functionality manually
2. Ensure no breaking changes
3. Verify Docker build works:
```bash
docker-compose build
docker-compose up -d
```

## Pull Request Process

1. Create a new branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes
3. Commit with clear messages:
```bash
git commit -m "feat: add new feature X"
git commit -m "fix: resolve issue with Y"
git commit -m "docs: update README for Z"
```

4. Push to your fork:
```bash
git push origin feature/your-feature-name
```

5. Open a Pull Request with:
   - Clear description of changes
   - Any breaking changes noted
   - Screenshots if UI changes
   - Testing steps

## Commit Message Convention

Use conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc)
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Adding tests
- `chore:` - Maintenance tasks

## Areas for Contribution

### High Priority
- Additional TenChat API endpoints
- Better error handling and retry logic
- More AI models support
- Improved human emulation algorithms
- Better proxy rotation strategies

### Medium Priority
- Additional task types (comments, shares, etc)
- Analytics and reporting features
- Webhook notifications
- Export/import functionality
- Multi-language support

### Low Priority
- UI/UX improvements
- Additional themes
- Mobile responsiveness
- Browser extension for cookie export

## Reporting Bugs

When reporting bugs, include:

1. **Environment:**
   - OS (Windows/Linux/Mac)
   - Python version
   - Docker version (if applicable)

2. **Steps to Reproduce:**
   - Clear step-by-step instructions
   - Expected behavior
   - Actual behavior

3. **Logs:**
   - Relevant error messages
   - Stack traces
   - API responses (remove sensitive data)

4. **Screenshots:**
   - If UI-related

## Feature Requests

When requesting features:

1. **Use Case:** Explain why this feature is needed
2. **Proposal:** Describe how it should work
3. **Alternatives:** Any alternative solutions considered
4. **Implementation:** If you have ideas on how to implement

## Code of Conduct

- Be respectful and professional
- Help others learn and grow
- Focus on constructive feedback
- Respect different perspectives
- No harassment or discrimination

## Questions?

- Open an issue for questions
- Check existing issues first
- Provide context and examples

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing! 🚀

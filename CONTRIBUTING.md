# Contributing to ToastyAnalytics

Thank you for your interest in contributing to ToastyAnalytics! We welcome contributions from the community.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Toasty-Analytics.git
   cd Toasty-Analytics
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 💻 Development Setup

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Git

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start infrastructure (PostgreSQL, Redis, etc.)
cd deployment/docker
docker-compose up -d

# Run tests
cd ../..
pytest tests/

# Run the server
uvicorn src.server_v2:app --reload
```

## 📝 Contribution Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use type hints where possible
- Write descriptive commit messages
- Add docstrings to all functions and classes

### Testing
- Write tests for new features
- Ensure all tests pass before submitting PR
- Maintain or improve code coverage

```bash
# Run tests with coverage
pytest --cov=src tests/
```

### Commit Messages
Follow the conventional commits format:
- `feat: Add new grading algorithm`
- `fix: Resolve rate limiting bug`
- `docs: Update deployment guide`
- `test: Add tests for neural grader`
- `refactor: Improve database queries`

## 🔄 Pull Request Process

1. **Update documentation** if you're changing functionality
2. **Add tests** for new features
3. **Run the test suite** and ensure everything passes
4. **Update the README.md** if needed
5. **Submit your PR** with a clear description of changes

### PR Checklist
- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts

## 🐛 Bug Reports

When reporting bugs, please include:
- Python version
- OS and version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs
- Minimal code example (if applicable)

## 💡 Feature Requests

We love new ideas! When suggesting features:
- Explain the use case
- Describe the proposed solution
- Consider backward compatibility
- Discuss potential alternatives

## 🤝 Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inspiring community for all.

### Our Standards
- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior
- Harassment or discriminatory language
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

## 📚 Resources

- [Documentation](docs/README.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Quick Start Guide](docs/QUICK_START.md)

## ❓ Questions?

Feel free to:
- Open an issue for discussion
- Reach out to maintainers
- Check existing issues and PRs

## 🏆 Recognition

Contributors will be acknowledged in our README and release notes.

Thank you for contributing to ToastyAnalytics! 🎉

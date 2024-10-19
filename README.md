# Git-wise

An AI-powered Git commit message generator that helps developers write meaningful and standardized commit messages.

[![PyPI version](https://badge.fury.io/py/git-wise.svg)](https://badge.fury.io/py/git-wise)
[![Tests](https://github.com/yourusername/git-wise/actions/workflows/tests.yml/badge.svg)](https://github.com/yourusername/git-wise/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🤖 AI-powered commit message generation
- 🌍 Multi-language support (English, Chinese, etc.)
- 📏 Customizable commit message length
- 🔄 Automatic commit content analysis
- 🔍 Smart commit splitting suggestions

## Installation

### Using pip (Requires Python 3.8+)
```bash
pip install git-wise
```

### Using Homebrew (macOS)
```bash
brew install git-wise
```

### Using Scoop (Windows)
```bash
scoop install git-wise
```

### Binary Installation
Download the latest binary for your platform from our [releases page](https://github.com/yourusername/git-wise/releases).

## Quick Start

1. Initialize git-wise in your repository:
```bash
git-wise init
```

2. Configure your preferences:
```bash
git-wise config set language en  # or zh for Chinese
git-wise config set message-length short  # or standard, detailed
```

3. Use git-wise after staging your changes:
```bash
git add .
git-wise commit
```

## Usage

### Basic Commands

```bash
# Generate commit message
git-wise commit

# Generate commit message in specific language
git-wise commit --lang zh

# Generate detailed commit message
git-wise commit --length detailed

# Split large commits
git-wise split
```

### Configuration

```bash
# Set OpenAI API key
git-wise config set api-key YOUR_API_KEY

# Set default language
git-wise config set language en

# Set default message length
git-wise config set message-length standard
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/git-wise.git
cd git-wise

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Style

We use Black for code formatting and isort for import sorting:

```bash
# Format code
black .

# Sort imports
isort .
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for providing the GPT API
- The Python community for excellent tools and libraries

## Support

- 📫 For bugs and feature requests, please [create an issue](https://github.com/yourusername/git-wise/issues)
- 💬 For questions and discussions, join our [Discord community](https://discord.gg/your-discord)
- 📧 For professional support, contact support@git-wise.dev

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for all notable changes.

## Security

For security issues, please refer to our [Security Policy](SECURITY.md) and report them privately as described there.
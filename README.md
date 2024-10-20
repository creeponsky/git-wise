# Git-wise

An AI-powered Git commit message generator that helps developers write meaningful and standardized commit messages.

[![PyPI version](https://badge.fury.io/py/git-wise.svg)](https://badge.fury.io/py/git-wise)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Welcome to Git-Wise

Welcome to Git-Wise, a project born from the realization that my commit skills weren't quite up to par while developing another product! 😎 After about 10 hours of development, we now have this version.

Git-Wise uses GPT to analyze your staged files, automatically generate commit messages, and submit them! It's designed to enhance your Git workflow and improve the quality of your commit history.

As the project is still in the development stage, there may be some issues. However, if you encounter any problems or have ideas for improvement, please feel free to reach out and contribute your code!

> Fun fact: Every commit in this repository was crafted with the help of Git-Wise!🫡

### Support the Project 

If you find Git-Wise helpful... 🤔

Unfortunately, I currently don't have any overseas payment methods 🥹🥹🥹

(But your moral support is greatly appreciated! )

<!-- [![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/creeponsky) -->

### Stay Connected

Follow me on Twitter for updates and more:

[![Twitter Follow](https://img.shields.io/twitter/follow/creeponsky?style=social)](https://twitter.com/creeponsky)

Your feedback and contributions are what make open-source projects like Git-Wise thrive. Let's make commit messages great together!


## Features

- 🤖 AI-powered analysis of staged files to generate commit messages (currently using GPT-4O-mini)
- 🌍 Support for generating commits in multiple languages
- 🚀 Automatic commit submission
- 📏 Adjustable commit message detail level

## Installation

```bash
pip install git-wise
```
## Quick Start

1. Initialize git-wise:
```bash
git-wise init
```

2. Generate a commit message:
```bash
git add .
git-wise start
```

## Usage

### Basic Commands

```bash
# Initialize or reconfigure Git-Wise
git-wise init

# Generate commit message
git-wise start

# Generate commit message with specific options
git-wise start --language en --detail brief --interactive

# Check Git-Wise configuration and environment
git-wise doctor

# Show current configuration
git-wise show-config

# Show staged changes
git-wise show-diff

# Update specific configuration settings
git-wise config --default-language
git-wise config --detail-level
git-wise config --api-key
git-wise config --model
git-wise config --interactive
git-wise config --unlimited-chunk
```

### Configuration Options

- Language: Select your preferred language for commit messages
- Detail Level: Choose between brief, minimal, or detailed commit messages
- API Key: Set your OpenAI API key
- Model: Select the AI model to use
- Interactive Mode: Enable or disable interactive commit creation
- Unlimited Chunk: Enable or disable unlimited chunk mode(for large staged changes)

## Examples
### Detail Level

if you choose minimal:
![Minimal commit example](assets/Minimal.png)

if you choose brief:
![Brief commit example](assets/Brief.png)

if you choose detailed:
![Detailed commit example](assets/Detailed.png)


## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/creeponsky/git-wise.git
cd git-wise

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -e "."
```

### Running Tests
find a git repo you need to test, and run the following command:
```bash
cd /path/to/your/git/repo
git-wise init
git-wise start
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
- Visit our [website](https://git-wise.com) (currently under construction, but we'll add content soon! 😎)
- 📫 For bugs and feature requests, please [create an issue](https://github.com/creeponsky/git-wise/issues)
- 📧 For professional support, contact support@git-wise.dev

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for all notable changes.

## Security

For security issues, please refer to our [Security Policy](SECURITY.md) and report them privately as described there.
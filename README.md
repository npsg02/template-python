---
title: Python Project Template
emoji: 🟧
colorFrom: yellow
colorTo: purple
sdk: docker
tags:
- Python
fullwidth: true
license: mit
app_port: 8080
---

# Python Project Template

A modern Python project template with best practices for development, testing, and deployment.

## Features

- Modern Python (3.11+) project structure
- Development tools configuration (pytest, black, isort, mypy, ruff)
- Docker support
- GitHub Actions ready
- Comprehensive documentation structure
- Jupyter notebook support

## Project Structure

```
.
├── docs/               # Documentation files
├── notebooks/         # Jupyter notebooks
├── src/               # Source code
│   ├── common/        # Common utilities and shared code
│   ├── modules/       # Feature modules
│   │   └── api/       # API related code
│   ├── shared/        # Shared resources
│   └── utils/         # Utility functions
└── tests/             # Test files
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/template-python.git
cd template-python
```

2. Create a virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

3. Copy the environment file and adjust as needed:
```bash
cp .env.example .env
```

### Development

This project uses several development tools:

- **pytest**: Testing framework
- **black**: Code formatting
- **isort**: Import sorting
- **mypy**: Static type checking
- **ruff**: Fast Python linter

Run tests:
```bash
pytest
```

Format code:
```bash
black .
isort .
```

Run type checking:
```bash
mypy src tests
```

Run linting:
```bash
ruff check .
```

### Docker

Build the Docker image:
```bash
make build
```

Run the container:
```bash
make run
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
# Web Search Client

A command-line web search client that uses the [Tavily API](https://tavily.com/) to perform web searches and save results locally.

## Features

- 🔍 **Powerful Search**: Leverage Tavily API for accurate web search results
- 💾 **Local Storage**: Save search results as JSON files with timestamps
- 🧹 **Auto-Cleanup**: Automatically manage search result files with configurable retention period
- 🎨 **User-Friendly CLI**: Simple command-line interface with helpful output formatting
- 🛠️ **Flexible Options**: Configure search parameters like depth, domain filters, and more

## Installation

### Prerequisites

- Python 3.12 or later
- [UV](https://github.com/astral-sh/uv) for dependency management (recommended)
- A Tavily API key ([get one here](https://tavily.com/))

### Using UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/web-search-client.git
cd web-search-client

# Create a virtual environment and install
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Using pip

```bash
pip install git+https://github.com/yourusername/web-search-client.git
```

## Configuration

Create a `.env` file in your working directory with your Tavily API key:

```
TAVILY_API_KEY=your-api-key-here
```

Alternatively, you can set the environment variable directly:

```bash
export TAVILY_API_KEY=your-api-key-here
```

## Usage

### Basic Search

```bash
# Basic search
web-search "python programming tutorials"

# Specify the number of results
web-search --max-results 5 "machine learning frameworks"

# More comprehensive search (may take longer)
web-search --depth comprehensive "climate change solutions"
```

### Advanced Options

```bash
# Include specific domains
web-search --include-domain docs.python.org --include-domain python.org "asyncio tutorial"

# Exclude certain domains
web-search --exclude-domain pinterest.com "best wedding cake designs"

# Include raw content in results
web-search --raw "quantum computing advances"

# Set custom retention period for file cleanup
web-search --retention-days 30 "renewable energy technology"
```

### Manual Cleanup

```bash
# Clean up search result files older than the default 14 days
web-search clean

# Clean up files older than a specific number of days
web-search clean --days 7

# Force cleanup without confirmation
web-search clean --force
```

### Help Information

```bash
# Display general help
web-search --help

# Display help for a specific command
web-search search --help
```

## File Storage

Search results are saved in the `search_results` directory as JSON files with timestamps:

```
search_results/
  ├── 20251015-120145_python-programming-tutorials.json
  ├── 20251015-120302_machine-learning-frameworks.json
  └── ...
```

Each file contains:
- The original query
- The timestamp when the search was performed
- The complete search results from Tavily

## Development

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/web-search-client.git
cd web-search-client

# Create a virtual environment and install dev dependencies
uv venv
source .venv/bin/activate
uv pip install -e .
uv add --dev

# Run tests
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


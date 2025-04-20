# Web Search Client

A command-line web search client that uses the [Tavily API](https://tavily.com/) to perform web searches and save results locally.

## Features

- 🔍 **Powerful Search**: Leverage Tavily API for accurate web search results
- 💾 **Local Storage**: Save search results as JSON files with timestamps
- 🧹 **Auto-Cleanup**: Automatically manage search result files with configurable retention period
- 🎨 **User-Friendly CLI**: Simple command-line interface with helpful output formatting
- 🛠️ **Flexible Options**: Configure search parameters like depth, domain filters, and more
- 🔄 **Redis Integration**: Optional Redis-based storage for improved performance and sharing capabilities

## Installation

### Prerequisites

- Python 3.12 or later
- [UV](https://github.com/astral-sh/uv) for dependency management (recommended)
- A Tavily API key ([get one here](https://tavily.com/))
- Redis server (optional, only if you want to use Redis storage)

### Using UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/web-search-client.git
cd web-search-client

# Create a virtual environment and install
uv venv
source .venv/bin/activate

# Basic installation
uv pip install -e .

# With Redis support
uv pip install -e ".[redis]"
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

## Redis Integration

The web search client supports Redis as an alternative storage backend for search results. This is an optional advanced feature that provides several benefits over file-based storage:

- **Performance**: Faster read/write operations for large result sets
- **Sharing**: Multiple clients can access the same result store
- **Data Management**: Better query and filtering capabilities
- **TTL Support**: Native expiration of old results

### Installing Redis Support

To use the Redis integration, you need to install the Redis Python client:

```bash
# Using UV
uv pip install -e ".[redis]"

# Using pip
pip install "web-search-client[redis]"
```

You'll also need access to a Redis server. For local development, you can run Redis using Docker:

```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

### Using Redis Storage

To use Redis as the storage backend, use the `--storage redis` option:

```bash
# Basic search with Redis storage
web-search --storage redis "quantum computing"

# Configure Redis connection
web-search --storage redis --redis-host myredis.example.com --redis-port 6380 "quantum computing"

# Set custom TTL for results
web-search --storage redis --ttl-days 30 "climate change solutions"
```

### Redis Configuration Options

The following options are available for Redis configuration:

- `--storage redis`: Use Redis as the storage backend
- `--redis-host TEXT`: Redis server hostname (default: localhost)
- `--redis-port INTEGER`: Redis server port (default: 6379)
- `--redis-db INTEGER`: Redis database number (default: 0)
- `--redis-password TEXT`: Redis password if authentication is required
- `--redis-prefix TEXT`: Key prefix for Redis keys (default: web-search:)
- `--ttl-days INTEGER`: Number of days to keep results in Redis (default: 14)

### Advanced Redis Operations

The Redis integration also supports listing, retrieving, and deleting specific results:

```bash
# List saved results in Redis
web-search list --storage redis

# Get a specific result
web-search get --storage redis 20250420-120145_quantum-computing

# Delete a specific result
web-search delete --storage redis 20250420-120145_quantum-computing

# Clean up old results
web-search clean --storage redis --days 7
```

These commands will be available in a future update. For now, you can examine the implementation in the `search_client/storage/redis.py` file.

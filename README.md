# 🔍 Tavily CLI

A command-line client that uses the [Tavily API](https://tavily.com/) to perform web searches and save results locally.

## ✨ Features

- 🔎 **Easy Web Searching**: Run web searches directly from your terminal
- 💾 **Result Storage**: Save search results locally as JSON files
- 🗄️ **Redis Integration**: Optional storage in Redis for sharing and persistence
- 🛠️ **Customizable Searches**:
  - 🔢 Limit number of results
  - 🌐 Include/exclude specific domains
  - 🔍 Choose between basic (faster) and advanced (deeper) searches
  - 📄 Include raw content in results
  - ⏱️ Customize retention period for stored results
- 🧹 **Result Management**: Clean up old results based on age

## 📥 Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- [Tavily API key](https://tavily.com/) (sign up for free to get one)

### Clone and Install Locally

```bash
# Clone the repository
git clone https://github.com/alxdr3k/tavily-cli.git
cd tavily-cli

# Initialize project with uv
uv init
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies using uv
uv pip install -e .
```

## ⚙️ Configuration

Create a `.env` file in your project directory with your Tavily API key:

```
TAVILY_API_KEY=your_api_key_here
```

Alternatively, set it as an environment variable:

```bash
export TAVILY_API_KEY=your_api_key_here
```

## 📖 Basic Usage

```bash
# Simple search
tavily "python programming tutorials"

# Limit number of results
tavily --max-results 5 "machine learning frameworks"

# Advanced search (deeper, more thorough results)
tavily --depth advanced "climate change solutions"

# Include specific domains in search results
tavily --include-domain docs.python.org --include-domain python.org "asyncio tutorial"

# Exclude domains from search results
tavily --exclude-domain pinterest.com "best wedding cake designs"

# Include raw content in results
tavily --raw "quantum computing advances"

# Custom retention period for stored results
tavily --retention-days 30 "renewable energy technology"

# Cleanup old results
tavily --clean                   # Default: removes results older than 14 days
tavily --clean --days 7          # Remove results older than 7 days
tavily --clean --force           # Skip confirmation prompt

# Display help information
tavily --help
```

## 🧪 Development Setup

For development work, install the development dependencies:

```bash
# Install development dependencies using uv
uv add pytest pytest-cov pre-commit
```

Run tests:

```bash
pytest
```

## 🗄️ Redis Integration

The Tavily CLI supports Redis as an alternative storage backend for search results. This is an optional advanced feature that provides several benefits over file-based storage:

- **Persistence**: Results can be stored beyond local files
- **Expiration**: Automatic TTL-based cleanup
- **Sharing**: Multiple users can access the same results
- **Performance**: Faster retrieval for frequent searches

### Installing Redis Dependencies

To use Redis with Tavily CLI, install the Redis package:

```bash
uv add redis
```

### Redis Usage Examples

```bash
# Basic Redis storage usage
tavily --storage redis "quantum computing"

# Custom Redis server configuration
tavily --storage redis --redis-host myredis.example.com --redis-port 6380 "quantum computing"

# Custom TTL configuration
tavily --storage redis --ttl-days 30 "climate change solutions"

# List all search results in Redis
tavily --list --storage redis

# Get specific results from Redis by ID
tavily --get 20250420-120145_quantum-computing --storage redis

# Delete specific results from Redis
tavily --delete 20250420-120145_quantum-computing --storage redis

# Clean old results from Redis
tavily --clean --storage redis --days 7
```

### Redis-Specific Options

- `--redis-host TEXT`: Redis server hostname (default: localhost)
- `--redis-port INTEGER`: Redis server port (default: 6379)
- `--redis-db INTEGER`: Redis database ID (default: 0)
- `--redis-password TEXT`: Redis password (if required)
- `--redis-prefix TEXT`: Key prefix for Redis keys (default: tavily:)
- `--ttl-days INTEGER`: Number of days to keep results in Redis (default: 14)

### Troubleshooting Redis Connection

If you're having issues connecting to Redis, test the connection:

```bash
redis-cli ping
```

You should see a response of `PONG`. If using Docker:

```bash
docker exec -it tavily-cli-redis-1 redis-cli ping
```

In verbose mode, the CLI will show connection details:

```
# "Initialized Redis storage backend at localhost:16379 with prefix: tavily:"
```

## 📄 License

MIT

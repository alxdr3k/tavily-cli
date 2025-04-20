# 🔍 Tavily CLI

![GitHub release (latest by date)](https://img.shields.io/github/v/release/alxdr3k/tavily-cli?color=blue&label=latest%20release)
![License](https://img.shields.io/github/license/alxdr3k/tavily-cli)
A command-line client that uses the [Tavily API](https://tavily.com/) to perform web searches and save results locally.

## ✨ Features

- 🔎 **Easy Web Searching**: Run web searches directly from your terminal
- 💾 **Result Storage**: Store search results using Redis
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

The Tavily CLI uses Redis as the primary storage backend for search results. This provides several benefits:

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
tavily "quantum computing"

# Clean old results from Redis
tavily --clean --days 7
```

Redis is the core storage mechanism. You can configure Redis connection parameters using environment variables as described below.

### Redis Configuration via Environment Variables

Redis connection can be configured using the following environment variables:

- `REDIS_HOST`: Redis server hostname (default: localhost)
- `REDIS_PORT`: Redis server port (default: 16379 for local, 6379 when running in Docker)
- `REDIS_PASSWORD`: Redis password for authentication (if required)
- `IN_DOCKER`: When set to "true", uses container port (6379) instead of host port

Example of setting Redis environment variables:

```bash
export REDIS_HOST=myredis.example.com
export REDIS_PORT=6380
export REDIS_PASSWORD=mysecretpassword
```

Note: If Redis connection fails, the application will automatically fall back to an in-memory mock Redis implementation (still using the Redis interface), allowing normal operation without a Redis server.

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

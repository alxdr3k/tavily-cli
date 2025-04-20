# Running web-search-client with Docker

This document provides instructions for using the dockerized version of web-search-client. This setup includes a Docker Compose configuration with the main application and an optional Redis service for storage.

## Overview

The Docker setup consists of:

1. **web-search-client service**: The main Python application that runs the web search CLI.
2. **Redis service**: An optional service for storing search results in Redis instead of the filesystem.

Docker Compose is used to orchestrate these services and manage their configuration and data persistence.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your system
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)
- A valid Tavily API key

## Environment Variables Configuration

The application requires certain environment variables to function properly. Create a `.env` file in the project root with the following variables:

```
TAVILY_API_KEY=your_tavily_api_key_here
STORAGE_BACKEND=file  # or 'redis' if you want to use Redis for storage
```

This file will be automatically picked up by Docker Compose and the variables will be passed to the containers.

## Building and Starting the Docker Services

### Build the Docker image

```bash
docker compose build
```

### Start the services

Start both the web-search-client and Redis services:

```bash
docker compose up -d
```

This will start the services in detached mode (in the background). The main web-search-client service will be idle, waiting for commands.

## Running web-search CLI Commands Through Docker

### Running a search

To run a search command:

```bash
docker compose run --rm web-search-client search "your search query here"
```

The `--rm` flag ensures the container is removed after running the command.

### Other CLI commands

You can run any of the CLI commands by replacing `search` with the desired command:

```bash
# Show help
docker compose run --rm web-search-client --help

# Clean up old search results
docker compose run --rm web-search-client clean
```

### Running commands on an already-running container

If the services are already running, you can execute commands on the existing container:

```bash
docker compose exec web-search-client web-search search "your search query here"
```

## Persisting Search Results

### File storage (default)

When using the default file storage backend, search results are stored in the `./search_results` directory on your host machine. This directory is mounted as a volume in the container, ensuring that search results persist even if the container is removed.

### Redis storage

When using the Redis storage backend, search results are stored in Redis. The Redis data is persisted in a Docker volume named `redis-data`, ensuring that data survives container restarts.

## Switching Between File and Redis Storage Backends

To switch between file and Redis storage backends, modify the `STORAGE_BACKEND` environment variable in your `.env` file:

```
# For file storage (default)
STORAGE_BACKEND=file

# For Redis storage
STORAGE_BACKEND=redis
```

After changing this variable, restart your services:

```bash
docker compose down
docker compose up -d
```

## Development Workflow Tips

### Live code reloading

For development purposes, you might want to make changes to the code and see them reflected immediately. You can mount your local code directory into the container:

```yaml
# In docker-compose.yml, modify the web-search-client service:
volumes:
  - .:/app  # Mount the entire project directory
  - ./search_results:/app/search_results  # Keep the results directory mounted
```

### Running tests

To run the project tests:

```bash
docker compose run --rm web-search-client pytest
```

### Inspecting container logs

To see the logs from the containers:

```bash
# All services
docker compose logs

# Specific service
docker compose logs web-search-client
docker compose logs redis

# Follow logs
docker compose logs -f
```

### Cleanup

To stop and remove the containers but keep the volumes:

```bash
docker compose down
```

To stop and remove containers and volumes (this will delete all stored data):

```bash
docker compose down -v
```

## Troubleshooting

### Connection issues with Redis

If you experience connection issues with Redis:

1. Check that the Redis service is running: `docker compose ps`
2. Ensure the environment variables are correctly set
3. Try restarting the services: `docker compose restart`

### API key issues

If you get API key errors:

1. Make sure your Tavily API key is correctly set in the `.env` file
2. Rebuild and restart the services to ensure the new key is used:
   ```bash
   docker compose down
   docker compose build
   docker compose up -d
   ```


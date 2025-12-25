# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml ./

# Copy the rest of the application
COPY . .

# Sync dependencies using uv
RUN uv sync --frozen

# Expose port (default for uvicorn)
EXPOSE 8000

# Run the application using uv
CMD ["uv", "run", "main.py"]

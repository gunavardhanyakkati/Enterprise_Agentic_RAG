# Use a base image with Python 3.12
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml \
    uv sync --frozen --no-dev

# Copy the source code
COPY src /app/src

# Create a virtual environment
RUN python -m venv .venv

# Add the virtual environment to the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

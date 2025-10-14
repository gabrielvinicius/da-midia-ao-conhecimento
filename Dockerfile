# === Stage 1: Build Stage ===
# Use a full Python image to ensure build tools are available for dependencies.
FROM python:3.11 as builder

# Set the working directory
WORKDIR /app

# Install poetry for dependency management (optional but good practice)
# For now, we stick to pip to keep it simple.
RUN pip install --upgrade pip

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt


# === Stage 2: Final Stage ===
# Use a slim image for a smaller final image size.
FROM python:3.11-slim

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set the working directory
WORKDIR /app

# Copy the installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application source code
COPY . .

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# The CMD is defined in docker-compose.yml, but we can set a default here.
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

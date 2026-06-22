# Stage 1: Build the React frontend
FROM node:18 AS frontend-build
WORKDIR /app
COPY audit-dashboard/package*.json ./audit-dashboard/
WORKDIR /app/audit-dashboard
RUN npm install
COPY audit-dashboard/ .
RUN npm run build

# Stage 2: Run the FastAPI backend
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies (including uvicorn for serving FastAPI)
RUN pip install --no-cache-dir -r requirements.txt uvicorn

# Copy the backend application code
COPY audit-tool/ ./audit-tool/

# Copy the built frontend static files from the first stage
COPY --from=frontend-build /app/audit-dashboard/dist /app/audit-dashboard/dist

# Change the working directory so Python path resolves "app" correctly
WORKDIR /app/audit-tool

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


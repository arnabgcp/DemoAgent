# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY app.py .

# Expose port 8000
EXPOSE 5000

# Command to run the application using uvicorn
# The application needs the GOOGLE_APPLICATION_CREDENTIALS environment variable
# to be set when the container runs, typically by mounting a service account key file.

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
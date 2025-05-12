# Use the official Playwright image as the base image
# This uses Python 3.11 and Playwright 1.51.0
FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

# Set /code as your base working directory
WORKDIR /code

# Copy and install dependencies
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the application code into the container
COPY app /code/app

# Copy the .env file into the container
COPY .env /code/.env

# Expose port 8801 for external access
EXPOSE 8801

# Change the working directory to app
WORKDIR /code/app

# Run the NiceGUI application on port 8801 and bind to 0.0.0.0 with unbuffered output
CMD ["python3", "-u", "main_page.py"]
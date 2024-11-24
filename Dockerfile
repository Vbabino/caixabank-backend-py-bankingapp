# Use the official Python image as a base image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the app on port 3000
EXPOSE 3000

# Command to run the Flask application
CMD ["flask", "run", "--host=0.0.0.0", "--port=3000"]
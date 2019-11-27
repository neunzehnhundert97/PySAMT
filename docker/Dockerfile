# Use an official Python runtime as a parent image
FROM frolvlad/alpine-python3

# Install git
RUN apk add --no-cache git

# Update pip to the newest version
RUN pip3 install --upgrade pip

# Install samt
RUN pip3 install git+https://github.com/neunzehnhundert97/samt

# Set the working directory to /app
WORKDIR /app

# Copy the configuration and the bot iself
ADD config/ /app/config
ADD Bot.py /app/Bot.py

# Run app.py when the container launches
CMD ["python3.7", "Bot.py"]

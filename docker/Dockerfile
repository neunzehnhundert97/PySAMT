# Use an official Python runtime as a parent image
FROM frolvlad/alpine-python3

# Install any needed packages specified in requirements.txt
RUN apk add --no-cache git
RUN pip3 install --upgrade pip
RUN pip3 install git+https://github.com/neunzehnhundert97/marvin-telegram-bot

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app
ADD config /app/config

ADD Echo.py /app/Echo.py

# Run app.py when the container launches
CMD ["python3.7", "Echo.py"]

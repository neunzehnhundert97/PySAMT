# Use an official Python runtime as a parent image
FROM frolvlad/alpine-python3

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
#ADD . /app
ADD config /app/config
ADD marvin-telegram-bot-master /app/marvin-telegram-bot-master

#https://codeload.github.com/neunzehnhundert97/marvin-telegram-bot/zip/master
# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip3 install ./marvin-telegram-bot-master

ADD Echo.py /app/Echo.py

# Run app.py when the container launches
CMD ["python3.6", "Echo.py"]

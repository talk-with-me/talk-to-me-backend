# Use Debian buster as OS environment
FROM python:3.7-buster

# Copy over stuff
COPY requirements.txt /requirements.txt
COPY app.py /app.py
COPY db.py /db.py
COPY lib /lib
COPY tests /tests

# Install dependencies
RUN apt-get update
RUN apt-get install -y python3-pip
RUN pip3 install -r requirements.txt

# RUNIT
ENTRYPOINT ["/tests/start_test.sh"]

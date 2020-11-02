# Use Debian buster as OS environment
FROM debian:10.6

# Copy over stuff
COPY requirements.txt /requirements.txt
COPY app.py /app.py
COPY db.py /db.py
COPY lib /lib

# Install dependencies
RUN apt-get update
RUN apt-get install -y python3.7 python3-pip
RUN pip3 install -r requirements.txt

# RUNIT
CMD ["python3.7", "app.py", "&&"]

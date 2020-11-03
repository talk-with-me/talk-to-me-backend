# Use Debian buster as OS environment
FROM python:3.7-buster

# Copy over stuff
COPY requirements.txt /requirements.txt
COPY app.py /app.py
COPY db.py /db.py
COPY lib /lib

# Install dependencies
RUN apt-get update
RUN apt-get install -y python3-pip nodejs npm
RUN pip3 install -r requirements.txt
RUN npm install jest

# RUNIT
CMD ["python3.7", "app.py", "&&", "nodejs", "test.js"]

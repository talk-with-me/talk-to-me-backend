# Use Debian buster as OS environment
FROM python:3.7-buster

# Copy over stuff
COPY requirements.txt /requirements.txt
COPY app.py /app.py
COPY db.py /db.py
COPY lib /lib

# Install dependencies
RUN pip3 install -r requirements.txt

# RUNIT
CMD ["python3.7", "app.py"]

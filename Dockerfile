# Use Debian buster as OS environment
FROM python:3.7

# Copy over requirements
COPY requirements.txt /requirements.txt

# Install dependencies
RUN pip3 install -r requirements.txt

# build cache deps
COPY . .

# RUNIT
# ENTRYPOINT python3 app.py
ENTRYPOINT gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:8000 --timeout 120 app:app

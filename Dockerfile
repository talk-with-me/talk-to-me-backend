# Use Debian buster as OS environment
FROM python:3.7

# Copy over requirements
COPY requirements.txt /requirements.txt
COPY scripts /scripts

# Install dependencies
RUN pip3 install -r requirements.txt

# setup GPT-2
RUN python scripts/setup-gpt2.py

# build cache
COPY . .

# RUNIT
# ENTRYPOINT python3 app.py
ENTRYPOINT gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:8000 app:app
#!/bin/sh
cd ..; python3.7 app.py & sleep 4; pytest tests; pkill python; echo success

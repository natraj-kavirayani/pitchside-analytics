#!/usr/bin/env bash
# Wait up to 60 seconds for a Streamlit app's health check to pass.
# Usage: wait-for-app.sh PORT LOG_FILE (the log is printed if it never does).
port=$1
log=$2
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:$port/_stcore/health" > /dev/null; then
    echo "App on port $port is up"
    exit 0
  fi
  sleep 1
done
echo "App on port $port did not become healthy within 60 seconds"
cat "$log"
exit 1

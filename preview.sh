#!/bin/sh
# Start the local preview and open the Home page.  Usage:  ./preview.sh
cd "$(dirname "$0")"
quarto preview --no-browser &
PID=$!
trap 'kill $PID 2>/dev/null' INT TERM EXIT
until curl -s -o /dev/null http://localhost:4200/; do sleep 1; done
open http://localhost:4200/ 2>/dev/null || xdg-open http://localhost:4200/ 2>/dev/null
wait $PID

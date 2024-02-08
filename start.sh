#!/bin/bash

cd "$(dirname "$(readlink -f "$0")")"
source venv/bin/activate

while :
do
    python3 main.py
    if [ $? -eq 0 ]; then
        echo "Exit code 0. Exiting..."
        break
    else
        echo "Non-zero exit code. Restarting..."
		sleep 5
    fi
done

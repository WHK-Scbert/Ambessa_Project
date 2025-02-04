#!/bin/bash

# Start n8n in the background and save PID
n8n start & 
N8N_PID=$!

# Start mallanoo_sploit in the background and save PID
cd ./mallanoo_sploit
npm run dev &
MALLANOO_PID=$!

# Start SniperServer/sniperservice in the background and save PID
cd ../MallanooSniper/mallanoo_sniper
npm run dev &
SNIPER_PID=$!

# Function to handle script exit and kill processes
cleanup() {
    echo "Stopping all processes..."
    kill $N8N_PID $MALLANOO_PID $SNIPER_PID 2>/dev/null
    wait
    echo "All processes stopped."
    exit 0
}

# Trap CTRL+C (SIGINT) and call cleanup function
trap cleanup SIGINT

# Wait to keep the script running
wait

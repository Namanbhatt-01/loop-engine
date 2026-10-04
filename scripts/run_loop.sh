#!/usr/bin/env bash
set -e

echo "Starting loop-engine control plane and test runner..."

# 1. Compile Go Control Plane Daemon
echo "Building Go control plane daemon..."
go build -o bin/daemon ./cmd/daemon

# 2. Start Go Daemon in Background
echo "Starting daemon on 127.0.0.1:50051..."
./bin/daemon &
DAEMON_PID=$!

# Ensure daemon cleanup on exit
trap "kill -9 $DAEMON_PID 2>/dev/null || true" EXIT

# Wait for daemon to be ready
sleep 1

# 3. Execute Python Reasoning Engine Loop
echo "Executing reasoning engine..."
python3 python_engine/main.py

echo "Execution completed successfully."

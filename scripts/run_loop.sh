#!/usr/bin/env bash
set -e

echo "---------------------------------------------------------"
echo "🌐 LAUNCHING UNIVERSAL POLYGLOT LOOP ENGINE"
echo "---------------------------------------------------------"

# 1. Compile Go Control Plane Daemon
echo "📦 Compiling Go Control Plane Daemon..."
go build -o bin/daemon ./cmd/daemon

# 2. Start Go Daemon in Background
echo "⚡ Starting Go Control Plane Daemon on 127.0.0.1:50051..."
./bin/daemon &
DAEMON_PID=$!

# Ensure daemon cleanup on exit
trap "kill -9 $DAEMON_PID 2>/dev/null || true" EXIT

# Wait for daemon to be ready
sleep 1

# 3. Execute Python Reasoning Engine Loop
echo "🐍 Running Python Reasoning Engine..."
python3 python_engine/main.py

echo "---------------------------------------------------------"
echo "✅ UNIVERSAL LOOP ENGINE EXECUTION COMPLETE"
echo "---------------------------------------------------------"

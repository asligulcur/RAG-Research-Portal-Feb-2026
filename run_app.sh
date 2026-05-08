#!/bin/bash
# Run the Personal Research Portal Streamlit app

cd "$(dirname "$0")"

# Determine Python executable
if [ -d "venv" ]; then
    PYTHON_EXE="venv/bin/python"
    echo "Using virtual environment Python: $PYTHON_EXE"
else
    PYTHON_EXE="python3"
    echo "Using system Python: $PYTHON_EXE"
fi

# Check if streamlit is available
if ! $PYTHON_EXE -c "import streamlit" 2>/dev/null; then
    echo "Error: streamlit not found. Installing..."
    $PYTHON_EXE -m pip install streamlit
fi

# Find an available port (8501–8510)
PORT=8501
for p in 8501 8502 8503 8504 8505 8506 8507 8508 8509 8510; do
    if ! lsof -Pi :$p -sTCP:LISTEN -t >/dev/null 2>&1; then
        PORT=$p
        break
    fi
done
if [ "$PORT" != "8501" ]; then
    echo "Port 8501 in use. Using port $PORT instead."
fi

# Run Streamlit app using the correct Python
$PYTHON_EXE -m streamlit run src/app/app.py --server.port $PORT

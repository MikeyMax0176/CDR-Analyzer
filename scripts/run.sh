#!/usr/bin/env bash
set -e

# 1. Create .venv if missing
if [ ! -d ".venv" ]; then
    echo "[run.sh] Creating virtual environment in .venv..."
    python3 -m venv .venv
fi

# 2. Activate venv
source .venv/bin/activate

# 3. Install requirements if streamlit missing
if ! .venv/bin/python -c "import streamlit" 2>/dev/null; then
    echo "[run.sh] Installing requirements..."
    pip install -r requirements.txt
fi

# 4. Print sys.executable for confirmation
.venv/bin/python -c "import sys; print('[run.sh] Using Python:', sys.executable)"

# 5. Run the app
exec .venv/bin/python -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501

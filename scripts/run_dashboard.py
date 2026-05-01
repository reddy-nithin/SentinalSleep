"""Streamlit launcher for the SentinelSleep Morning Dashboard.

Usage::

    uv run streamlit run scripts/run_dashboard.py
"""

import sys
from pathlib import Path
import subprocess

def main():
    """Proxy script to ensure correct import paths before handing off to Streamlit."""
    # Ensure src is in path so 'sentinelsleep' can be imported by the app
    root_dir = Path(__file__).resolve().parents[1]
    app_path = root_dir / "src" / "sentinelsleep" / "dashboard" / "app.py"
    
    # If this is run via `python scripts/run_dashboard.py`, we actually want to invoke streamlit
    if "streamlit" not in sys.modules:
        print(f"Launching Streamlit app: {app_path}")
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])
    else:
        # If already running inside streamlit, just execute the app
        with open(app_path) as f:
            # We must pass __name__ == "__main__" so the if __name__ block inside app.py executes
            exec(f.read(), {"__file__": str(app_path), "__name__": "__main__"})

if __name__ == "__main__":
    main()

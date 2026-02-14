"""
Backend runner with correct PYTHONPATH
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Now import and run
import uvicorn

if __name__ == "__main__":
    print("Starting AI Finance Backend...")
    print("Server: http://127.0.0.1:8001")
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)

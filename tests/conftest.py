import sys
import os
from pathlib import Path

# Ensure project root is on sys.path so `backend` is importable
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load .env before any tests
from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

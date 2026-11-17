"""Vercel Serverless Function entrypoint for Helix AI FastAPI application."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure root directory is in sys.path for serverless environment
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.server import app  # noqa: E402

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Use an in-memory DB by default and never touch real exchange APIs.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("MODE", "paper")
os.environ.setdefault("EXCHANGE_ID", "binance")
os.environ.setdefault("SYMBOLS", "BTC/USDT")
os.environ.setdefault("LLM_API_KEY", "")

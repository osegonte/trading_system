import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

def load_json_file(file_path: str, default: Any = None) -> Any:
    """Safely load a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return default or {}
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return default or {}

def save_json_file(file_path: str, data: Any) -> bool:
    """Safely save data to a JSON file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False

def format_currency(amount: float) -> str:
    """Format currency amount."""
    return f"${amount:,.2f}"

def format_percentage(value: float) -> str:
    """Format percentage value."""
    return f"{value:.2f}%"

def get_market_time() -> datetime:
    """Get current market time (EST)."""
    return datetime.now(timezone.utc)

def is_market_open() -> bool:
    """Check if market is currently open."""
    now = get_market_time()
    # Simple check - extend for holidays and exact market hours
    return now.weekday() < 5 and 9 <= now.hour < 16

def ensure_directory_exists(directory: str) -> None:
    """Ensure a directory exists, create if it doesn't."""
    if not os.path.exists(directory):
        os.makedirs(directory)
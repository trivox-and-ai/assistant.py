# assistant/persistence.py

import os
import json
import datetime
from typing import List

from .data_model import Task

TASKS_FILE = "tasks.json"
LOGS_FILE = "logs.json"


def load_tasks() -> List[Task]:
    """Load tasks from JSON file."""
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Task.from_dict(item) for item in data]
    except:
        return []


def save_tasks(tasks: List[Task]):
    """Persist tasks to JSON file."""
    data = [t.to_dict() for t in tasks]
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_logs() -> List[str]:
    """Load log entries from JSON file."""
    if not os.path.exists(LOGS_FILE):
        return []
    try:
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_logs(logs: List[str]):
    """Persist log entries to JSON file."""
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def log_action(logs: List[str], message: str):
    """Add timestamped log entry and persist."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    logs.append(entry)
    save_logs(logs)

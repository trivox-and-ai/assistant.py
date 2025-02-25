# assistant/data_model.py

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, date

@dataclass
class Task:
    """Represents a single task in the todo list."""
    title: str
    description: str = ""
    resolved: bool = False
    future_date: Optional[date] = None

    def is_future_task(self) -> bool:
        """Check if this is a future task based on its date."""
        if not self.future_date:
            return False
        return self.future_date > date.today()

    def to_dict(self):
        """Convert Task to a dictionary for JSON serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "resolved": self.resolved,
            "future_date": self.future_date.strftime("%Y-%m-%d") if self.future_date else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create Task from a dictionary (JSON deserialization)."""
        future_date = None
        if data.get("future_date"):
            try:
                future_date = datetime.strptime(data["future_date"], "%Y-%m-%d").date()
            except ValueError:
                pass  # Invalid date format, keep as None

        return cls(
            title=data["title"],
            description=data["description"],
            resolved=data["resolved"],
            future_date=future_date
        )

    def __repr__(self):
        return f"Task(title={self.title}, resolved={self.resolved})"

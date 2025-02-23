# assistant/data_model.py

from typing import List

class Task:
    """Represents a single task in the todo list."""

    def __init__(
        self,
        title: str,
        description: str = "",
        resolved: bool = False,
    ):
        self.title = title
        self.description = description
        self.resolved = resolved

    def to_dict(self):
        """Convert Task to a dictionary for JSON serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "resolved": self.resolved
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            title=data["title"],
            description=data["description"],
            resolved=data["resolved"]
        )

    def __repr__(self):
        return f"Task(title={self.title}, resolved={self.resolved})"

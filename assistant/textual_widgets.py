# assistant/textual_widgets.py

from textual.widgets import ListItem, Label, Static
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
from typing import Optional
import logging

from .data_model import Task

class TaskItem(ListItem):
    """A ListItem representing a single task row in the ListView."""
    
    DEFAULT_CSS = """
    TaskItem {
        color: #00dd00;
        text-style: bold;
    }
    
    TaskItem > Label {
        color: #00dd00;
        text-style: bold;
    }
    
    TaskItem.-resolved,
    TaskItem.-resolved > Label {
        color: #666666;
    }
    """
    
    def __init__(self, task: Task, index: int):
        # Create the label with initial text
        self._task = task
        self._index = index
        self._label = Label(self.render_text())
        # Call super with the label
        super().__init__(self._label)
        if task.resolved:  # Only add class if resolved
            self.add_class("-resolved")

    def render_text(self) -> str:
        """Return a text representation of this task, with a marker if resolved."""
        marker = "[R]" if self._task.resolved else ""
        return f"{marker} {self._task.title}"

    @property
    def task(self) -> Task:
        return self._task

    @property
    def index(self) -> int:
        return self._index

    def update_content(self):
        """Update the displayed content if the task changes."""
        self._label.update(self.render_text())
        if self._task.resolved:
            self.add_class("-resolved")
        else:
            self.remove_class("-resolved")


class ReviewTaskItem(ListItem):
    """A ListItem representing a task in review mode."""
    
    DEFAULT_CSS = """
    ReviewTaskItem {
        color: #00dd00;
        text-style: bold;
    }
    
    ReviewTaskItem.-reopen {
        color: #00dd00;
        text-style: bold;
    }
    
    ReviewTaskItem.-delete {
        color: #dd0000;
        text-style: bold;
    }
    """
    
    def __init__(self, task: Task, index: int, decision: 'ReviewDecision'):
        # Initialize task and decision before calling super()
        self._task_item = task  # Changed from _task to _task_item to avoid conflict
        self._index = index
        self._decision = decision
        self._label = Label(self.render_text())
        self.logger = logging.getLogger(__name__)  # Add logger initialization
        super().__init__(self._label)
        
        # Add appropriate CSS class based on decision
        if decision.value == "reopen":
            self.add_class("-reopen")
        elif decision.value == "delete":
            self.add_class("-delete")

    def render_text(self) -> str:
        """Return a text representation of this task."""
        markers = {
            "keep": "[R]",
            "reopen": "[+]",
            "delete": "[D]"
        }
        marker = markers[self._decision.value]
        return f"{marker} {self._task_item.title}"  # Changed from _task to _task_item

    @property
    def task(self) -> Task:
        return self._task_item  # Changed from _task to _task_item

    @property
    def index(self) -> int:
        return self._index

    def update_content(self, task: Optional[Task] = None, decision: Optional['ReviewDecision'] = None) -> None:
        """Update the item's content and/or decision state."""
        if task is not None:
            self._task_item = task
        if decision is not None:
            self._decision = decision
        
        # Update the label text
        new_text = self.render_text()
        self._label.update(new_text)
        
        # Update CSS classes
        self.remove_class("-reopen")
        self.remove_class("-delete")
        
        if self._decision.value == "reopen":
            self.add_class("-reopen")
        elif self._decision.value == "delete":
            self.add_class("-delete")

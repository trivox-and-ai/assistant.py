from textual.screen import Screen
from textual.widgets import ListView
from textual import events
from typing import List

from .data_model import Task
from .textual_widgets import ReviewTaskItem

class ReviewScreen(Screen):
    """Screen for reviewing resolved tasks."""
    
    BINDINGS = [
        ("escape", "cancel", "Exit review mode"),
    ]

    def __init__(self, tasks: List[Task]):
        super().__init__()
        self.tasks = [task for task in tasks if task.resolved]
        self.list_view = ListView()

    def compose(self):
        yield self.list_view

    def on_mount(self):
        """Called when screen is mounted."""
        # Populate list view with resolved tasks
        for index, task in enumerate(self.tasks):
            self.list_view.append(ReviewTaskItem(task, index))
        self.list_view.focus()

    def action_cancel(self) -> None:
        """Handle Escape key to exit review mode."""
        self.app.pop_screen()
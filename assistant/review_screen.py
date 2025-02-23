from textual.screen import Screen
from textual.widgets import ListView
from textual import events
from typing import List
from enum import Enum

from .data_model import Task
from .textual_widgets import ReviewTaskItem

class ReviewDecision(Enum):
    KEEP = "keep"      # [R] - default state
    REOPEN = "reopen"  # [+]
    DELETE = "delete"  # [D]

class ReviewScreen(Screen):
    """Screen for reviewing resolved tasks."""
    
    BINDINGS = [
        ("escape", "cancel", "Exit review mode"),
        ("space", "toggle_reopen", "Mark for reopening"),
        ("d", "toggle_delete", "Mark for deletion"),
    ]

    def __init__(self, tasks: List[Task]):
        super().__init__()
        self.tasks = [task for task in tasks if task.resolved]
        self.decisions = {task: ReviewDecision.KEEP for task in self.tasks}
        self.list_view = ListView()

    def compose(self):
        yield self.list_view

    def on_mount(self):
        """Called when screen is mounted."""
        self._refresh_list()
        self.list_view.focus()

    def _refresh_list(self):
        """Refresh the list view with current states."""
        self.list_view.clear()
        for index, task in enumerate(self.tasks):
            decision = self.decisions[task]
            self.list_view.append(ReviewTaskItem(task, index, decision))

    def action_toggle_reopen(self) -> None:
        """Toggle reopen state for the selected task."""
        if self.list_view.index is None:
            return
        task = self.tasks[self.list_view.index]
        current = self.decisions[task]
        self.decisions[task] = (
            ReviewDecision.KEEP if current == ReviewDecision.REOPEN 
            else ReviewDecision.REOPEN
        )
        self._refresh_list()

    def action_toggle_delete(self) -> None:
        """Toggle delete state for the selected task."""
        if self.list_view.index is None:
            return
        task = self.tasks[self.list_view.index]
        current = self.decisions[task]
        self.decisions[task] = (
            ReviewDecision.KEEP if current == ReviewDecision.DELETE 
            else ReviewDecision.DELETE
        )
        self._refresh_list()

    def action_cancel(self) -> None:
        """Handle Escape key to exit review mode."""
        self.app.pop_screen()
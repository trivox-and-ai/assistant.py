from textual.screen import Screen
from textual.widgets import ListView
from textual import events
import logging
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
    
    CSS = """
    ListView {
        width: 100%;
        height: 100%;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "Exit review mode"),
    ]

    def __init__(self, tasks: List[Task]):
        super().__init__()
        self.tasks = [task for task in tasks if task.resolved]
        self.decisions = {task: ReviewDecision.KEEP for task in self.tasks}
        self.list_view = ListView()
        self.logger = logging.getLogger(__name__)

    def compose(self):
        yield self.list_view

    def on_mount(self):
        """Called when screen is mounted."""
        self._refresh_list()
        self.list_view.focus()

    class MoveCursor(events.Message):
        """Message to move cursor to specific position."""
        def __init__(self, target_index: int) -> None:
            super().__init__()
            self.target_index = target_index

    async def on_review_screen_move_cursor(self, message: MoveCursor) -> None:
        """Handle cursor movement message."""
        if self.list_view:
            self.list_view.index = message.target_index
            self.list_view.focus()

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for the review screen."""
        
        if event.key in ("j"):
            if self.list_view:
                self.list_view.index = (
                    min(self.list_view.index + 1, len(self.tasks) - 1) 
                    if self.list_view.index is not None 
                    else 0
                )
                self.list_view.focus()
        elif event.key in ("k"):
            if self.list_view:
                self.list_view.index = (
                    max(0, self.list_view.index - 1) 
                    if self.list_view.index is not None 
                    else 0
                )
                self.list_view.focus()
        elif event.key == "escape":
            self.action_cancel()
        elif event.key == "space":
            self.action_toggle_reopen()
        elif event.key == "d":
            self.action_toggle_delete()
        return True  # Capture all other keys to prevent them from reaching the main app

    def _refresh_list(self):
        """Refresh the list view with current states."""
        current_index = self.list_view.index
        self.list_view.clear()
        for index, task in enumerate(self.tasks):
            decision = self.decisions[task]
            self.list_view.append(ReviewTaskItem(task, index, decision))
        
        if current_index is not None:
            self.post_message(self.MoveCursor(current_index))

    def _update_item(self, index: int) -> None:
        """Update single item in the list view."""
        if index is None or index >= len(self.tasks):
            return
            
        task = self.tasks[index]
        decision = self.decisions[task]
        
        # Get existing item and update it in place
        existing_item = self.list_view.children[index]
        if isinstance(existing_item, ReviewTaskItem):
            existing_item.update_decision(decision)
        
        # Also post message to ensure consistent state
        self.post_message(self.MoveCursor(index))

    def action_toggle_reopen(self) -> None:
        """Toggle reopen state for the selected task."""
        if self.list_view.index is None:
            return
        current_index = self.list_view.index
        task = self.tasks[current_index]
        current = self.decisions[task]
        self.decisions[task] = (
            ReviewDecision.KEEP if current == ReviewDecision.REOPEN 
            else ReviewDecision.REOPEN
        )
        self._update_item(current_index)  # Update only this item

    def action_toggle_delete(self) -> None:
        """Toggle delete state for the selected task."""
        if self.list_view.index is None:
            return
        current_index = self.list_view.index
        task = self.tasks[current_index]
        current = self.decisions[task]
        self.decisions[task] = (
            ReviewDecision.KEEP if current == ReviewDecision.DELETE 
            else ReviewDecision.DELETE
        )
        self._update_item(current_index)  # Update only this item

    def action_cancel(self) -> None:
        """Handle Escape key to exit review mode."""
        self.app.pop_screen()
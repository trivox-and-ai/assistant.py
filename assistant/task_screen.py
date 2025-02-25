# assistant/screens.py

import logging
from typing import Optional
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Input
from textual import events

from .data_model import Task

class TaskScreenResult(events.Message):
    """Message containing the result of TaskScreen operations."""
    def __init__(self, cancelled: bool, title: str = "", description: str = "") -> None:
        super().__init__()
        self.cancelled = cancelled
        self.title = title
        self.description = description

class TaskScreenComplete(events.Message):
    """Message indicating that task screen processing is complete."""
    pass

class TaskScreen(Screen):
    """Screen for adding or editing tasks."""
    BINDINGS = [
        ("enter", "submit", "Submit task"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, task: Optional[Task] = None, focus_description: bool = False, parent_screen: Optional[Screen] = None):
        super().__init__()
        self._task = task
        self._focus_description = focus_description
        self._parent_screen = parent_screen  # Store the parent screen reference

        self.title_input = Input(
            placeholder="Title (required)",
            select_on_focus=False
        )
        self.desc_input = Input(
            placeholder="Description (optional)",
            select_on_focus=False
        )

        if task:
            self.title_input.value = task.title
            self.desc_input.value = task.description

        self.logger = logging.getLogger(__name__)

    def on_mount(self):
        """Called once the screen is mounted."""
        if self._focus_description:
            self.desc_input.focus()
        else:
            self.title_input.focus()

    def compose(self) -> ComposeResult:
        yield Label("Task Details")
        yield Label("Title:")
        yield self.title_input
        yield Label("Description:")
        yield self.desc_input

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for the task screen."""
        if event.key == "enter":
            event.stop()  # Stop event propagation
            event.prevent_default()  # Prevent default handling
            self.action_submit()
            return True
        return False

    def action_submit(self) -> None:
        """Handle Enter key for saving the task."""
        title = self.title_input.value.strip()
        description = self.desc_input.value.strip()

        if not title:
            self.logger.debug("Title is required, submission aborted")
            return  # Title is required

        result = TaskScreenResult(
            cancelled=False,
            title=title,
            description=description
        )
        
        # If we have a parent screen, post directly to it
        if self._parent_screen:
            self._parent_screen.post_message(result)
        else:
            # Fall back to normal behavior for non-review mode
            self.post_message(result)
            
        self.app.pop_screen()

    def action_cancel(self) -> None:
        """Handle Escape key for canceling task add/edit."""
        self.logger.debug("Cancel action triggered")
        result = TaskScreenResult(cancelled=True)
        
        # If we have a parent screen, post directly to it
        if self._parent_screen:
            self._parent_screen.post_message(result)
        else:
            # Fall back to normal behavior for non-review mode
            self.post_message(result)
            
        self.app.pop_screen()

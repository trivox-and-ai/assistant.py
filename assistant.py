import json
import os
import time
import datetime
from typing import List, Optional
import logging
import asyncio

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Static,
    Input,
    Button,
    RichLog,
    ListView,
    ListItem,
    Label
)
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from textual import events

###############################################################################
# Data Model
###############################################################################

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

###############################################################################
# Persistence & Logging Helpers
###############################################################################

TASKS_FILE = "tasks.json"
LOGS_FILE = "logs.json"


def load_tasks() -> List[Task]:
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Task.from_dict(item) for item in data]
    except:
        return []


def save_tasks(tasks: List[Task]):
    data = [t.to_dict() for t in tasks]
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_logs() -> List[str]:
    if not os.path.exists(LOGS_FILE):
        return []
    try:
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_logs(logs: List[str]):
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def log_action(logs: List[str], message: str):
    """Add timestamped log entry."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    logs.append(entry)
    save_logs(logs)

###############################################################################
# Textual Widgets
###############################################################################

class TaskItem(ListItem):
    """A ListItem representing a single task row in the ListView."""
    def __init__(self, task: Task, index: int):
        # Store task data first
        self._task = task
        self._index = index
        # Create the label with initial text
        self._label = Label(self.render_text())
        # Call super with the label
        super().__init__(self._label)

    def render_text(self) -> str:
        """Return a text representation of this task, with highlighting if resolved."""
        marker = "[RESOLVED]" if self._task.resolved else ""
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


class HelpPanel(Static):
    """Shows the help (available commands)."""
    def compose(self) -> ComposeResult:
        lines = [
            "Commands:",
            "  j / ↓ : Move selection down",
            "  k / ↑ : Move selection up",
            "  J: Move selected task DOWN in priority",
            "  K: Move selected task UP in priority",
            "  a: Add new task ABOVE selected",
            "  A: Add new task BELOW selected",
            "  d: Delete selected task",
            "  r: Resolve/Unresolve selected task",
            "  e: Edit selected task (focus Title first)",
            "  E: Edit selected task (focus Description first)",
            "  h: Toggle this help panel",
            "  L: Toggle action log panel",
            "  q: Quit",
        ]
        help_text = "\n".join(lines)
        yield Label(help_text)


###############################################################################
# Main App
###############################################################################

class TaskScreen(Screen):
    """Screen for adding or editing tasks."""
    
    BINDINGS = [
        ("enter", "submit", "Submit task"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, task: Optional[Task] = None, focus_description: bool = False):
        super().__init__()
        self._task = task
        self._focus_description = focus_description  # Store which field should get focus
        
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

        # Initialize logger
        self.logger = logging.getLogger(__name__)

    def on_mount(self):
        """Called once the screen is mounted."""
        # Focus the appropriate input field
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
            self.action_submit()  # Call the submit action
            return True  # Indicate that the event has been handled
        else:
            return False  # Indicate that the event has not been handled

    def action_submit(self) -> None:
        """Handle Enter key for saving the task."""
        title = self.title_input.value.strip()
        description = self.desc_input.value.strip()

        if not title:
            self.logger.debug("Title is required, submission aborted")
            return  # Title is required

        # Instead of directly modifying tasks, send a message with the new values
        self.post_message(TaskScreenResult(
            cancelled=False,
            title=title,
            description=description
        ))
        self.app.pop_screen()

    def action_cancel(self) -> None:
        """Handle Escape key for canceling the addition or editing of a task."""
        self.logger.debug("Cancel action triggered")
        self.post_message(TaskScreenResult(cancelled=True))
        self.app.pop_screen()

class TaskScreenResult(events.Message):
    """Message containing the result of TaskScreen operations."""
    def __init__(self, cancelled: bool, title: str = "", description: str = "") -> None:
        self.cancelled = cancelled
        self.title = title
        self.description = description
        super().__init__()

class TaskScreenComplete(events.Message):
    """Message indicating that task screen processing is complete."""
    pass

class TodoApp(App):
    """Main TUI Application."""

    CSS_PATH = None  # We won't use a separate CSS in this example

    # Reactive state
    tasks = reactive(load_tasks())
    logs = reactive(load_logs())

    # Register screens
    SCREENS = {"add_task": TaskScreen}  # Register the screen

    # Panels
    help_panel: Optional[HelpPanel] = None
    log_panel: Optional[RichLog] = None

    # The main list of tasks
    list_view: Optional[ListView] = None

    def __init__(self):
        super().__init__()
        # Check if --release flag is present
        import sys
        mode = 'a' if '--release' in sys.argv else 'w'
        
        # Set up debug logging to a file
        logging.basicConfig(
            filename='debug.log',
            filemode=mode,  # 'w' for overwrite, 'a' for append
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.logger.debug("TodoApp initialized")
        # Load tasks explicitly
        self.tasks = load_tasks()

        # Add these instance variables for tracking state
        self._editing_task = None  # The task being edited, if any
        self._insert_above = False  # Whether to insert above or below when adding
        self._handling_task_screen = False  # Add flag to track task screen handling

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        # Create a container to hold our widgets
        with Container():
            # Create the ListView and store it
            self.list_view = ListView()
            yield self.list_view

    async def on_mount(self) -> None:
        """Called after the app is fully loaded."""
        # Update the list view
        await self.update_list_view()
        # Set focus
        self.list_view.focus()
        # Save initial state
        save_tasks(self.tasks)
        save_logs(self.logs)

    async def update_list_view(self) -> None:
        """Update the list view with current tasks."""
        if self.list_view is None:
            return

        self.list_view.clear()
        
        for index, task in enumerate(self.tasks):
            item = TaskItem(task, index)
            self.list_view.append(item)

        self.list_view.refresh()
        self.list_view.focus()

    def action_show_help(self):
        """Toggle help panel (h)."""
        if self.help_panel:
            self.help_panel.display = not self.help_panel.display

    def action_toggle_log(self):
        """Toggle the log panel (L)."""
        if self.log_panel:
            self.log_panel.display = not self.log_panel.display

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Fired when user moves selection up/down in the list. We can handle UI changes if needed."""
        pass

    def get_selected_index(self) -> int:
        """Return the currently selected task index or -1 if none."""
        if self.list_view is None or self.list_view.index is None:
            return -1
        return self.list_view.index

    def add_log_entry(self, message: str):
        """Add a log entry to logs list and to the log panel."""
        log_action(self.logs, message)  # saves to disk
        if self.log_panel:
            self.log_panel.write(f"{self.logs[-1]}\n")

    ############################################################################
    # Handling Key Presses (Commands)
    ############################################################################
    async def on_key(self, event: events.Key) -> None:
        """Handle key events for the main application."""
        # Skip handling if we're processing a task screen result
        if self._handling_task_screen:
            return

        # Regular key handling
        if event.key == "A":  # Add task above
            await self.open_task_screen(insert_above=True)
            return
        elif event.key == "a":  # Add task below
            await self.open_task_screen(insert_above=False)
            return
        elif event.key == "j":  # Only handle 'j', let ListView handle 'down' naturally
            if self.list_view is not None:
                try:
                    result = self.list_view.action_cursor_down()
                    if result is not None:
                        await result
                except Exception as e:
                    self.logger.error(f"Error moving cursor down: {e}")
            return
        elif event.key == "k":  # Only handle 'k', let ListView handle 'up' naturally
            if self.list_view is not None:
                try:
                    result = self.list_view.action_cursor_up()
                    if result is not None:
                        await result
                except Exception as e:
                    self.logger.error(f"Error moving cursor up: {e}")
            return

        # Reorder selected task one place DOWN in the internal list
        elif event.key == "J":
            await self.move_task_down()
            return

        # Reorder selected task one place UP
        elif event.key == "K":
            await self.move_task_up()
            return

        # 'd' => delete selected task
        elif event.key == "d":
            await self.delete_selected_task()
            return

        # 'r' => resolve/unresolve
        elif event.key == "r":
            await self.resolve_or_unresolve_task()
            return

        # 'h' => help
        elif event.key == "h":
            self.action_show_help()
            return

        # Multiple commands for editing (focus title first)
        elif event.key in ("e", "o", "enter"):
            selected_index = self.get_selected_index()
            if selected_index is not None:
                task_to_edit = self.tasks[selected_index]
                await self.open_task_screen(task=task_to_edit, focus_description=False)
            return

        # 'E' => edit selected task (focus description)
        elif event.key == "E":
            selected_index = self.get_selected_index()
            if selected_index is not None:
                task_to_edit = self.tasks[selected_index]
                await self.open_task_screen(task=task_to_edit, focus_description=True)
            return

        # 'L' => shift+l => show/hide log
        elif event.key == "L":
            self.action_toggle_log()
            return

        # 'q' => quit
        elif event.key == "q":
            self.exit()
            return

    ############################################################################
    # Command Implementations
    ############################################################################
    async def move_task_up(self):
        """Move selected task up in priority (swap with previous in list)."""
        idx = self.get_selected_index()
        if idx <= 0:
            return  # can't move up
        
        self.tasks[idx], self.tasks[idx - 1] = self.tasks[idx - 1], self.tasks[idx]
        save_tasks(self.tasks)
        await self.update_list_view()
        self.post_message(self.MoveCursor(idx - 1))

    async def move_task_down(self):
        """Move selected task down in priority (swap with next in list)."""
        idx = self.get_selected_index()
        if idx == -1 or idx >= len(self.tasks) - 1:
            return  # can't move down
        
        self.tasks[idx], self.tasks[idx + 1] = self.tasks[idx + 1], self.tasks[idx]
        save_tasks(self.tasks)
        await self.update_list_view()
        self.post_message(self.MoveCursor(idx + 1))

    class MoveCursor(events.Message):
        """Message to move cursor to specific position."""
        def __init__(self, target_index: int) -> None:
            self.target_index = target_index
            super().__init__()

    async def on_todo_app_move_cursor(self, message: MoveCursor) -> None:
        """Handle cursor movement message."""
        self.list_view.index = message.target_index
        self.list_view.focus()

    async def open_task_screen(self, task: Optional[Task] = None, insert_above: bool = False, focus_description: bool = False):
        """Open the task screen for adding or editing a task."""
        self._handling_task_screen = True

        # Store the state
        self._editing_task = task
        self._insert_above = insert_above
        
        if task is None:
            selected_index = self.get_selected_index()  # Get the currently selected index

        screen = TaskScreen(task, focus_description=focus_description)  # Pass focus preference to screen
        await self.push_screen(screen)

    async def on_task_screen_result(self, message: TaskScreenResult) -> None:
        """Handle the result from TaskScreen."""
        try:
            if message.cancelled:
                self._editing_task = None  # Clear the reference
                return

            selected_index = self.get_selected_index()
            if self._editing_task:  # If we were editing an existing task
                self._editing_task.title = message.title
                self._editing_task.description = message.description
                task_title = self._editing_task.title
                target_index = selected_index  # Keep same position for edited task
                self._editing_task = None  # Clear the reference
                action = "Edited"
            else:  # Adding a new task
                new_task = Task(title=message.title, description=message.description)
                # Insert at the appropriate position
                if self._insert_above and selected_index is not None:
                    self.tasks.insert(selected_index, new_task)
                    target_index = selected_index  # Select the new task
                else:
                    insert_idx = selected_index + 1 if selected_index is not None else len(self.tasks)
                    self.tasks.insert(insert_idx, new_task)
                    target_index = insert_idx  # Select the new task
                task_title = new_task.title
                action = "Added"

            # Save changes and update view
            save_tasks(self.tasks)
            await self.update_list_view()
            self.add_log_entry(f"{action} task: '{task_title}'")
            
            # Move cursor to target position and ensure focus
            self.post_message(self.MoveCursor(target_index))

        finally:
            # Post message to reset the flag after all processing is complete
            self.post_message(TaskScreenComplete())

    async def on_task_screen_complete(self, message: TaskScreenComplete) -> None:
        """Handle completion of task screen processing."""
        self._handling_task_screen = False

    async def delete_selected_task(self):
        idx = self.get_selected_index()
        if idx == -1:
            return  # No task selected

        task = self.tasks[idx]
        self.tasks.pop(idx)  # Remove the selected task
        save_tasks(self.tasks)  # Save the updated task list

        # Update the list view
        await self.update_list_view()

        # Determine the new index to select
        if len(self.tasks) > 0:
            # If there are tasks left, select the next one
            new_index = min(idx, len(self.tasks) - 1)  # Select the next task or the last one
            self.post_message(self.MoveCursor(new_index))  # Send a message to move the cursor
        else:
            # If no tasks are left, clear the selection
            self.list_view.index = None

        self.add_log_entry(f"Deleted task: '{task.title}'")

    async def resolve_or_unresolve_task(self):
        idx = self.get_selected_index()
        if idx == -1:
            return
        task = self.tasks[idx]
        task.resolved = not task.resolved
        self.add_log_entry(f"{'Resolved' if task.resolved else 'Unresolved'} task: '{task.title}'")
        save_tasks(self.tasks)
        await self.update_list_view()

    ############################################################################
    # Event Handlers for Add/Edit Panels
    ############################################################################
    async def on_button_pressed(self, event: Button.Pressed):
        # For edit task
        if event.button.name == "save_edit":
            if self.edit_task_panel:
                # Update task details
                self.edit_task_panel.task.title = self.edit_task_panel.title_input.value.strip()
                desc_value = self.edit_task_panel.desc_input.value.strip()
                paragraphs = desc_value.split("\\n")
                self.edit_task_panel.task.description = "\n".join(paragraphs)
                save_tasks(self.tasks)

                # Update the list view
                await self.update_list_view()
                self.add_log_entry(f"Edited task: '{self.edit_task_panel.task.title}'")
                self.remove(self.edit_task_panel)
                self.edit_task_panel = None
            return

        if event.button.name == "cancel_edit":
            if self.edit_task_panel:
                # Revert changes
                self.edit_task_panel.task.title = self.edit_task_panel.old_title
                self.edit_task_panel.task.description = self.edit_task_panel.old_description

                self.remove(self.edit_task_panel)
                self.edit_task_panel = None
            return

    ############################################################################
    # Lifecycle Events
    ############################################################################
    def on_unmount(self) -> None:
        """Called before the app closes; ensure tasks and logs are saved."""
        save_tasks(self.tasks)
        save_logs(self.logs)

    async def on_shutdown_request(self) -> None:
        """Intercept shutdown to ensure data is saved."""
        save_tasks(self.tasks)
        save_logs(self.logs)
        await self.shutdown()

###############################################################################
# Running the App
###############################################################################

if __name__ == "__main__":
    app = TodoApp()
    app.run()

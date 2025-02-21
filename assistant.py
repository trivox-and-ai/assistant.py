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


class EditTaskPanel(Static):
    """A panel for editing an existing task (title/description)."""
    def __init__(self, task: Task, focus_on_desc=False):
        super().__init__()
        self._task = task
        # We'll keep the old values if user cancels
        self.old_title = task.title
        self.old_description = task.description

        self.title_input = Input(value=task.title)
        self.desc_input = Input(value=task.description)
        self.save_button = Button(label="Save", name="save_edit")
        self.cancel_button = Button(label="Cancel", name="cancel_edit")
        self.focus_on_desc = focus_on_desc

    def on_mount(self):
        """Called once the panel is added to the DOM. We can set focus here."""
        if self.focus_on_desc:
            self.desc_input.focus()
        else:
            self.title_input.focus()

    def compose(self) -> ComposeResult:
        yield Label("Edit Task")
        yield Label("Title:")
        yield self.title_input
        yield Label("Description (use '\\n' for multiline):")
        yield self.desc_input
        yield Horizontal(self.save_button, self.cancel_button)

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

class AddTaskScreen(Screen):
    """A full screen mode for adding new tasks."""
    
    BINDINGS = [
        ("enter", "submit", "Submit task"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, above=True):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.above = above
        self.title_input = Input(placeholder="Title (required)")
        self.desc_input = Input(placeholder="Description (optional) -- separate multiple paragraphs with '\\n'")

    def compose(self) -> ComposeResult:
        yield Label("Add New Task (Enter to add, Esc to cancel)")
        yield self.title_input
        yield self.desc_input

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self.action_submit()

    async def action_submit(self) -> None:
        """Handle Enter key."""
        title = self.title_input.value.strip()
        description = self.desc_input.value.strip()

        if not title:
            return  # Title is required

        paragraphs = description.split("\\n")
        full_desc = "\n".join(paragraphs)
        above = self.above

        try:
            selected_idx = self.app.get_selected_index()
            new_task = Task(title=title, description=full_desc)
            
            insert_pos = selected_idx if above else selected_idx + 1
            if selected_idx == -1:
                insert_pos = len(self.app.tasks)  # Append to end if no selection

            self.app.tasks.insert(insert_pos, new_task)
            save_tasks(self.app.tasks)
            await self.app.update_list_view()
            self.app.post_message(TodoApp.MoveCursor(insert_pos))
            self.app.add_log_entry(f"Created task: '{new_task.title}'")
        except Exception as e:
            self.logger.error(f"Error adding task: {e}")
        finally:
            self.app.pop_screen()

    async def action_cancel(self) -> None:
        self.app.pop_screen()

    def on_mount(self):
        self.title_input.focus()

    async def on_screen_resume(self) -> None:
        self.title_input.focus()

class TodoApp(App):
    """Main TUI Application."""

    CSS_PATH = None  # We won't use a separate CSS in this example

    # Reactive state
    tasks = reactive(load_tasks())
    logs = reactive(load_logs())

    # Register screens
    SCREENS = {"add_task": AddTaskScreen}  # Register the screen

    # Panels
    edit_task_panel: Optional[EditTaskPanel] = None
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
        key = event.key

        if key == "j":  # Only handle 'j', let ListView handle 'down' naturally
            if self.list_view is not None:
                try:
                    result = self.list_view.action_cursor_down()
                    if result is not None:
                        await result
                except Exception as e:
                    self.logger.error(f"Error moving cursor down: {e}")
            return

        if key == "k":  # Only handle 'k', let ListView handle 'up' naturally
            if self.list_view is not None:
                try:
                    result = self.list_view.action_cursor_up()
                    if result is not None:
                        await result
                except Exception as e:
                    self.logger.error(f"Error moving cursor up: {e}")
            return

        # Reorder selected task one place DOWN in the internal list
        if key == "J":
            await self.move_task_down()
            return

        # Reorder selected task one place UP
        if key == "K":
            await self.move_task_up()
            return

        # 'A' => add new task BEFORE selected
        if key == "A":
            await self.open_add_task_panel(above=True)
            return

        # 'a' => add new task AFTER selected
        if key == "a":
            await self.open_add_task_panel(above=False)
            return

        # 'd' => delete selected task
        if key == "d":
            await self.delete_selected_task()
            return

        # 'r' => resolve/unresolve
        if key == "r":
            await self.resolve_or_unresolve_task()
            return

        # 'h' => help
        if key == "h":
            self.action_show_help()
            return

        # 'e' => edit selected task
        if key == "e":
            await self.edit_selected_task(focus_on_desc=False)
            return

        # 'E' => shift+e => focus description first
        if key == "E":
            await self.edit_selected_task(focus_on_desc=True)
            return

        # 'L' => shift+l => show/hide log
        if key == "L":
            self.action_toggle_log()
            return

        # 'q' => quit
        if key == "q":
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

    async def open_add_task_panel(self, above=True):
        """Switch to add task screen."""
        screen = AddTaskScreen(above=above)
        await self.push_screen(screen)

    async def delete_selected_task(self):
        idx = self.get_selected_index()
        if idx == -1:
            return
        task = self.tasks[idx]
        self.tasks.pop(idx)
        save_tasks(self.tasks)
        await self.update_list_view()
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

    async def edit_selected_task(self, focus_on_desc=False):
        idx = self.get_selected_index()
        if idx == -1:
            return
        task = self.tasks[idx]
        if self.edit_task_panel:
            self.remove(self.edit_task_panel)

        self.edit_task_panel = EditTaskPanel(task, focus_on_desc=focus_on_desc)
        self.edit_task_panel.styles.border = ("ascii", "yellow")
        self.edit_task_panel.styles.background = "black"
        self.edit_task_panel.styles.padding = (1, 1)
        self.mount(self.edit_task_panel)

    ############################################################################
    # Event Handlers for Add/Edit Panels
    ############################################################################
    async def on_button_pressed(self, event: Button.Pressed):
        # For edit task
        if event.button.name == "save_edit":
            if self.edit_task_panel:
                self.edit_task_panel.task.title = self.edit_task_panel.title_input.value.strip()
                desc_value = self.edit_task_panel.desc_input.value.strip()
                paragraphs = desc_value.split("\\n")
                self.edit_task_panel.task.description = "\n".join(paragraphs)

                save_tasks(self.tasks)
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

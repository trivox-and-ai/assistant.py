# assistant/textual_widgets.py

from textual.widgets import ListItem, Label, Static
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult

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


class ReviewTaskItem(ListItem):
    """A ListItem representing a task in review mode."""
    
    DEFAULT_CSS = """
    ReviewTaskItem {
        color: #00dd00;
        text-style: bold;
    }
    """
    
    def __init__(self, task: Task, index: int):
        self._task = task
        self._index = index
        self._label = Label(self.render_text())
        super().__init__(self._label)

    def render_text(self) -> str:
        """Return a text representation of this task."""
        return f"[R] {self._task.title}"

    @property
    def task(self) -> Task:
        return self._task

    @property
    def index(self) -> int:
        return self._index

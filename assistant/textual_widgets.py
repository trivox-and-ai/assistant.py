# assistant/textual_widgets.py

from textual.widgets import ListItem, Label, Static
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult

from .data_model import Task

class TaskItem(ListItem):
    """A ListItem representing a single task row in the ListView."""
    def __init__(self, task: Task, index: int):
        # Store task data
        self._task = task
        self._index = index
        # Create the label with initial text
        self._label = Label(self.render_text())
        # Call super with the label
        super().__init__(self._label)

    def render_text(self) -> str:
        """Return a text representation of this task, with a marker if resolved."""
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

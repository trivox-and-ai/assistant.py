# assistant/todo_app.py

import sys
import logging
from typing import Optional

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import ListView, RichLog
from textual.containers import Container
from textual.reactive import reactive
from textual import events

from .data_model import Task
from .persistence import (
    load_tasks,
    save_tasks,
    load_logs,
    save_logs,
    log_action
)
from .textual_widgets import TaskItem, HelpPanel
from .screens import TaskScreen, TaskScreenResult, TaskScreenComplete

class TodoApp(App):
    """Main TUI Application."""
    CSS_PATH = None  # Not using a separate CSS file

    # Reactive state
    tasks = reactive(load_tasks())
    logs = reactive(load_logs())

    # Screens
    SCREENS = {"add_task": TaskScreen}

    help_panel: Optional[HelpPanel] = None
    log_panel: Optional[RichLog] = None
    list_view: Optional[ListView] = None

    def __init__(self):
        super().__init__()
        mode = 'a' if '--release' in sys.argv else 'w'
        logging.basicConfig(
            filename='debug.log',
            filemode=mode,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.logger.debug("TodoApp initialized")

        # Load tasks
        self.tasks = load_tasks()

        # Additional instance variables
        self._editing_task = None
        self._insert_above = False
        self._handling_task_screen = False

    def compose(self) -> ComposeResult:
        with Container():
            yield ListView()  # Don't assign to self.list_view here

    async def on_mount(self) -> None:
        """Called once the app is fully loaded."""
        self.list_view = self.query_one(ListView)  # Get reference to ListView here
        await self.update_list_view()
        if self.list_view:
            self.list_view.focus()
        
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
        """Fired when user moves selection up/down in the list."""
        pass

    def get_selected_index(self) -> int:
        """Return the currently selected task index or -1 if none."""
        if self.list_view is None or self.list_view.index is None:
            return -1
        return self.list_view.index

    def add_log_entry(self, message: str):
        """Add a log entry to logs list and to the log panel."""
        log_action(self.logs, message)
        if self.log_panel:
            self.log_panel.write(f"{self.logs[-1]}\n")

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for the main application."""
        if self._handling_task_screen:
            return

        if event.key == "A":  # Add task ABOVE
            await self.open_task_screen(insert_above=True)
            return
        elif event.key == "a":  # Add task BELOW
            await self.open_task_screen(insert_above=False)
            return
        elif event.key == "j":
            if self.list_view is not None:
                await self.list_view.action_cursor_down()
            return
        elif event.key == "k":
            if self.list_view is not None:
                await self.list_view.action_cursor_up()
            return
        elif event.key == "J":
            await self.move_task_down()
            return
        elif event.key == "K":
            await self.move_task_up()
            return
        elif event.key == "d":
            await self.delete_selected_task()
            return
        elif event.key == "r":
            await self.resolve_or_unresolve_task()
            return
        elif event.key == "h":
            self.action_show_help()
            return
        elif event.key in ("e", "o", "enter"):
            selected_index = self.get_selected_index()
            if selected_index >= 0:
                task_to_edit = self.tasks[selected_index]
                await self.open_task_screen(task=task_to_edit, focus_description=False)
            return
        elif event.key == "E":
            selected_index = self.get_selected_index()
            if selected_index >= 0:
                task_to_edit = self.tasks[selected_index]
                await self.open_task_screen(task=task_to_edit, focus_description=True)
            return
        elif event.key == "L":
            self.action_toggle_log()
            return
        elif event.key == "q":
            self.exit()
            return

    async def move_task_up(self):
        idx = self.get_selected_index()
        if idx <= 0:
            return
        self.tasks[idx], self.tasks[idx - 1] = self.tasks[idx - 1], self.tasks[idx]
        save_tasks(self.tasks)
        await self.update_list_view()
        self.post_message(self.MoveCursor(idx - 1))

    async def move_task_down(self):
        idx = self.get_selected_index()
        if idx == -1 or idx >= len(self.tasks) - 1:
            return
        self.tasks[idx], self.tasks[idx + 1] = self.tasks[idx + 1], self.tasks[idx]
        save_tasks(self.tasks)
        await self.update_list_view()
        self.post_message(self.MoveCursor(idx + 1))

    class MoveCursor(events.Message):
        """Message to move cursor to specific position."""
        def __init__(self, target_index: int) -> None:
            super().__init__()
            self.target_index = target_index

    async def on_todo_app_move_cursor(self, message: MoveCursor) -> None:
        if self.list_view:
            self.list_view.index = message.target_index
            self.list_view.focus()

    async def open_task_screen(self, 
                               task: Optional[Task] = None, 
                               insert_above: bool = False, 
                               focus_description: bool = False):
        """Open the task screen for adding or editing a task."""
        self._handling_task_screen = True
        self._editing_task = task
        self._insert_above = insert_above

        screen = TaskScreen(task, focus_description=focus_description)
        await self.push_screen(screen)

    async def on_task_screen_result(self, message: TaskScreenResult) -> None:
        try:
            if message.cancelled:
                self._editing_task = None
                return

            selected_index = self.get_selected_index()
            if self._editing_task:  # editing existing
                self._editing_task.title = message.title
                self._editing_task.description = message.description
                task_title = self._editing_task.title
                target_index = selected_index
                self._editing_task = None
                action = "Edited"
            else:
                new_task = Task(title=message.title, description=message.description)
                if self._insert_above and selected_index >= 0:
                    self.tasks.insert(selected_index, new_task)
                    target_index = selected_index
                else:
                    insert_idx = (selected_index + 1) if selected_index >= 0 else len(self.tasks)
                    self.tasks.insert(insert_idx, new_task)
                    target_index = insert_idx
                task_title = new_task.title
                action = "Added"

            save_tasks(self.tasks)
            await self.update_list_view()
            self.add_log_entry(f"{action} task: '{task_title}'")
            self.post_message(self.MoveCursor(target_index))

        finally:
            self.post_message(TaskScreenComplete())

    async def on_task_screen_complete(self, message: TaskScreenComplete) -> None:
        self._handling_task_screen = False

    async def delete_selected_task(self):
        idx = self.get_selected_index()
        if idx == -1:
            return
        task = self.tasks[idx]
        self.tasks.pop(idx)
        save_tasks(self.tasks)
        await self.update_list_view()

        if len(self.tasks) > 0:
            new_index = min(idx, len(self.tasks) - 1)
            self.post_message(self.MoveCursor(new_index))
        else:
            if self.list_view:
                self.list_view.index = None

        self.add_log_entry(f"Deleted task: '{task.title}'")

    async def resolve_or_unresolve_task(self):
        idx = self.get_selected_index()
        if idx == -1:
            return
        task = self.tasks[idx]
        task.resolved = not task.resolved
        self.add_log_entry(
            f"{'Resolved' if task.resolved else 'Unresolved'} task: '{task.title}'"
        )
        save_tasks(self.tasks)
        await self.update_list_view()

    def on_unmount(self) -> None:
        """Called before the app closes; ensure tasks/logs are saved."""
        save_tasks(self.tasks)
        save_logs(self.logs)

    async def on_shutdown_request(self) -> None:
        """Intercept shutdown to ensure data is saved."""
        save_tasks(self.tasks)
        save_logs(self.logs)
        await self.shutdown()

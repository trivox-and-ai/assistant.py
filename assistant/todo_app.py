# assistant/todo_app.py

import sys
import logging
import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import ListView, RichLog, Label
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
from .textual_widgets import TaskItem
from .task_screen import TaskScreen, TaskScreenResult, TaskScreenComplete
from .review_screen import ReviewScreen, ReviewDecision

class TodoApp(App):
    """Main TUI Application."""
    CSS = """
    Screen {
        color: #00dd00;
        text-style: bold;
    }
    
    ListView {
        width: 100%;
        height: 100%;
    }

    #header {
        dock: top;
        background: black;
        color: #00dd00;
        text-style: bold;
        padding: 0 1 1 1;
        width: 100%;
        height: 2;
    }
    """

    # Reactive state
    tasks = reactive(load_tasks())
    logs = reactive(load_logs())

    # Screens
    SCREENS = {
        "add_task": TaskScreen,
    }

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
        self._handling_review_screen = False

    def compose(self) -> ComposeResult:
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        yield Label(f"Alex Assistant - Main Menu ({current_date})", id="header")
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
        if self._handling_task_screen or self._handling_review_screen:
            return

        if event.key == "A":  # Add task ABOVE
            await self.open_task_screen(insert_above=True)
            return
        elif event.key == "a":  # Add task BELOW
            await self.open_task_screen(insert_above=False)
            return
        elif event.key == "j":
            if self.list_view is not None:
                self.list_view.action_cursor_down()
            return
        elif event.key == "k":
            if self.list_view is not None:
                self.list_view.action_cursor_up()
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
        elif event.key in ("q", "escape"):
            self.exit()
            return
        elif event.key == "R":
            screen = ReviewScreen(self.tasks)
            await self.push_screen(screen)
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
        """Handle the result from TaskScreen."""
        if self._handling_review_screen:
            return

        try:
            if message.cancelled:
                self._editing_task = None
                return

            selected_index = self.get_selected_index()
            if self._editing_task:  # editing existing
                self._editing_task.title = message.title
                self._editing_task.description = message.description
                self._editing_task.future_date = message.future_date
                task_title = self._editing_task.title
                target_index = selected_index
                self._editing_task = None
                action = "Edited"
            else:
                new_task = Task(
                    title=message.title, 
                    description=message.description,
                    future_date=message.future_date
                )
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
        
        if task.resolved:
            # Remove task from current position
            self.tasks.pop(idx)
            # Add it to the end
            self.tasks.append(task)
            
            # Calculate new cursor position
            # If we're at the last item, move cursor up
            new_index = min(idx, len(self.tasks) - 2) if len(self.tasks) > 1 else 0
        else:
            # Remove task from current position
            self.tasks.pop(idx)
            # Add it to the beginning
            self.tasks.insert(0, task)
            # Focus on the unresolved task at the top
            new_index = 0
            
        self.add_log_entry(
            f"{'Resolved' if task.resolved else 'Unresolved'} task: '{task.title}'"
        )
        
        save_tasks(self.tasks)
        await self.update_list_view()
        
        # Move cursor via message
        self.post_message(self.MoveCursor(new_index))

    def on_unmount(self) -> None:
        """Called before the app closes; ensure tasks/logs are saved."""
        save_tasks(self.tasks)
        save_logs(self.logs)

    async def on_shutdown_request(self) -> None:
        """Intercept shutdown to ensure data is saved."""
        save_tasks(self.tasks)
        save_logs(self.logs)
        await self.shutdown()

    async def push_screen(self, screen: Screen, *args, **kwargs) -> None:
        """Override push_screen to track which screen we're handling."""
        if isinstance(screen, TaskScreen):
            self._handling_task_screen = True
        elif isinstance(screen, ReviewScreen):
            self._handling_review_screen = True
        await super().push_screen(screen, *args, **kwargs)

    def pop_screen(self) -> None:
        """Override pop_screen to reset screen handling flags and refresh view if needed."""
        screen = self.screen
        if isinstance(screen, TaskScreen):
            self._handling_task_screen = False
        elif isinstance(screen, ReviewScreen):
            self._handling_review_screen = False
            # Refresh the entire list view when returning from review mode
            self.call_after_refresh(self.update_list_view)
        super().pop_screen()

    async def on_todo_app_screen_handling_state(self, message: "TodoApp.ScreenHandlingState") -> None:
        """Handle screen state changes."""
        self.logger.debug(f"Before state change: handling_review={self._handling_review_screen}, handling_task={self._handling_task_screen}")
        if message.screen_type == "task":
            self._handling_task_screen = message.is_handling
        elif message.screen_type == "review":
            self._handling_review_screen = message.is_handling
        self.logger.debug(f"After state change: screen_type={message.screen_type}, is_handling={message.is_handling}, handling_review={self._handling_review_screen}, handling_task={self._handling_task_screen}")

    async def on_review_screen_review_complete(self, message: ReviewScreen.ReviewComplete) -> None:
        """Handle the completion of review with decisions."""
        for task, decision in message.decisions.items():
            if decision == ReviewDecision.DELETE:
                # Remove task from list
                self.tasks.remove(task)
                self.add_log_entry(f"Deleted task: '{task.title}'")
            elif decision == ReviewDecision.REOPEN:
                # Unresolve and move to top
                task.resolved = False
                self.tasks.remove(task)
                self.tasks.insert(0, task)
                self.add_log_entry(f"Reopened task: '{task.title}'")
            # KEEP decision requires no action
        
        save_tasks(self.tasks)
        await self.update_list_view()
        
        # Focus first item if any tasks remain
        if self.tasks and self.list_view:
            self.post_message(self.MoveCursor(0))


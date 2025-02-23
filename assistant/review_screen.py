from textual.screen import Screen
from textual import events

class ReviewScreen(Screen):
    """Screen for reviewing resolved tasks."""
    
    BINDINGS = [
        ("escape", "cancel", "Exit review mode"),
    ]

    def __init__(self):
        super().__init__()

    def action_cancel(self) -> None:
        """Handle Escape key to exit review mode."""
        self.app.pop_screen()
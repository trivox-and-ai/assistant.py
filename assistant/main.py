# assistant/main.py

from .todo_app import TodoApp

def main():
    app = TodoApp()
    app.run()

if __name__ == "__main__":
    main()

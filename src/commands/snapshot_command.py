from PySide6.QtGui import QUndoCommand

class SnapshotCommand(QUndoCommand):
    def __init__(self, main_window, old_state, new_state, description="Thay đổi"):
        super().__init__(description)
        self.main_window = main_window
        self.old_state = old_state
        self.new_state = new_state

    def undo(self):
        if self.old_state:
            self.main_window._restore_state(self.old_state)

    def redo(self):
        if self.new_state:
            self.main_window._restore_state(self.new_state)
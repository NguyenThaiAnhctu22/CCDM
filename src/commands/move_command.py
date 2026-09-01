from PySide6.QtGui import QUndoCommand

class MoveEntityCommand(QUndoCommand):
    def __init__(self, entity_item, old_pos, new_pos, description="Di chuyển Entity"):
        super().__init__(description)
        self.entity_item = entity_item
        self.old_pos = old_pos
        self.new_pos = new_pos

    def undo(self):
        self.entity_item.setPos(self.old_pos)
        self.entity_item.entity.x = self.old_pos.x()
        self.entity_item.entity.y = self.old_pos.y()
        if hasattr(self.entity_item, 'scene') and self.entity_item.scene():
            views = self.entity_item.scene().views()
            if views and hasattr(views[0], 'update_all_relationships'):
                views[0].update_all_relationships()

    def redo(self):
        self.entity_item.setPos(self.new_pos)
        self.entity_item.entity.x = self.new_pos.x()
        self.entity_item.entity.y = self.new_pos.y()
        if hasattr(self.entity_item, 'scene') and self.entity_item.scene():
            views = self.entity_item.scene().views()
            if views and hasattr(views[0], 'update_all_relationships'):
                views[0].update_all_relationships()
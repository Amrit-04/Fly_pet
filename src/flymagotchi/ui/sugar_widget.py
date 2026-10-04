"""Interactive draggable sugar cube widget for the desktop overlay."""

from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QMouseEvent
from PyQt6.QtWidgets import QWidget

from flymagotchi.ui.sugar import SugarRenderer


class SugarWidget(QWidget):
    """Draggable sugar cube widget with drag-drop position updates."""

    position_changed = pyqtSignal(float, float)

    def __init__(self, x: float = 960, y: float = 540, size: int = 32):
        super().__init__()
        self.pos = QPointF(x, y)
        self.size = size
        self.dragging = False
        self.drag_offset = QPointF(0, 0)
        self.renderer = SugarRenderer()

        self.setGeometry(int(x - size // 2), int(y - size // 2), size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_position(self, x: float, y: float) -> None:
        """Programmatically update sugar position."""
        self.pos = QPointF(x, y)
        self.setGeometry(
            int(x - self.size // 2),
            int(y - self.size // 2),
            self.size,
            self.size,
        )
        self.position_changed.emit(x, y)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_offset = QPointF(event.pos()) - QPointF(self.size / 2, self.size / 2)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update position while dragging."""
        if self.dragging:
            new_pos = QPointF(event.globalPos()) - self.drag_offset
            self.set_position(new_pos.x(), new_pos.y())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def paintEvent(self, event) -> None:
        """Render the sugar cube."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        self.renderer.render(painter, self.size / 2, self.size / 2)
        painter.end()

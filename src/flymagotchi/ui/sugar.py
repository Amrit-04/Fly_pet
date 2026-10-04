"""Procedural sugar cube renderer.

Draws an isometric crystalline sugar cube with soft drop shadow.
"""

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF


class SugarRenderer:
    """Renders the sugar cube item that the user places on the desktop."""

    def __init__(self, size_px: int = 32) -> None:
        self.size = size_px
        self.top_color = QColor(255, 255, 255, 240)
        self.left_color = QColor(220, 225, 235, 230)
        self.right_color = QColor(190, 200, 215, 230)
        self.outline_color = QColor(150, 160, 180, 160)
        self.shadow_color = QColor(0, 0, 0, 45)

    def render(self, painter: QPainter, x: float, y: float) -> None:
        """Render isometric sugar cube centered at (x, y)."""
        painter.save()
        painter.translate(x, y)

        s = self.size / 32.0

        # Drop shadow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.shadow_color))
        painter.drawEllipse(QRectF(-12 * s, 4 * s, 24 * s, 10 * s))

        painter.setPen(QPen(self.outline_color, 1.0))

        # Top face (diamond)
        top_poly = QPolygonF([
            QPointF(0, -10 * s),
            QPointF(12 * s, -4 * s),
            QPointF(0, 2 * s),
            QPointF(-12 * s, -4 * s),
        ])
        painter.setBrush(QBrush(self.top_color))
        painter.drawPolygon(top_poly)

        # Left face
        left_poly = QPolygonF([
            QPointF(-12 * s, -4 * s),
            QPointF(0, 2 * s),
            QPointF(0, 14 * s),
            QPointF(-12 * s, 8 * s),
        ])
        painter.setBrush(QBrush(self.left_color))
        painter.drawPolygon(left_poly)

        # Right face
        right_poly = QPolygonF([
            QPointF(0, 2 * s),
            QPointF(12 * s, -4 * s),
            QPointF(12 * s, 8 * s),
            QPointF(0, 14 * s),
        ])
        painter.setBrush(QBrush(self.right_color))
        painter.drawPolygon(right_poly)

        painter.restore()

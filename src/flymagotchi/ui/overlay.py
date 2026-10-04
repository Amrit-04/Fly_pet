"""Platform-aware transparent desktop overlay.

Provides a click-through, always-on-top frameless window for the fly pet.
Adapts transparency flags based on the host operating system.
"""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QWidget

from flymagotchi.ui.fly import FlyRenderer
from flymagotchi.ui.sugar import SugarRenderer


class FlyOverlay(QWidget):
    """Transparent, frameless overlay hosting the fly and sugar cube."""

    def __init__(self, width: int = 1920, height: int = 1080):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.resize(width, height)

        self.fly_renderer = FlyRenderer()
        self.sugar_renderer = SugarRenderer()

        self.fly_state = None
        self.sugar_pos = None
        self.population_rates = None

    def update_scene(
        self,
        fly_state,
        sugar_pos,
        population_rates=None,
    ) -> None:
        """Update the rendered state of the scene before repaint."""
        self.fly_state = fly_state
        self.sugar_pos = sugar_pos
        self.population_rates = population_rates
        self.update()

    def paintEvent(self, event) -> None:
        """Draw transparent background with the sugar cube and fly."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Clear background (transparent)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        # Draw sugar cube if present
        if self.sugar_pos is not None:
            self.sugar_renderer.render(painter, self.sugar_pos[0], self.sugar_pos[1])

        # Draw fly
        if self.fly_state is not None:
            self.fly_renderer.render(painter, self.fly_state, 0.016)

        painter.end()

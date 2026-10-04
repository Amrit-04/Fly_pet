"""Procedural, ultra-lightweight pixel art fly renderer.

Draws an authentic Drosophila melanogaster in pixel style using QPainter primitives.
Zero PNG/asset loading required. Consumes virtually zero memory and CPU.
"""

from typing import Optional
import math
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF

from flymagotchi.simulation.controller import FlyState
from flymagotchi.brain.decoder import BehaviorState


class FlyRenderer:
    """Renders the fruit fly with animated wings and proboscis extension."""

    def __init__(self, size_px: int = 32) -> None:
        self.size = size_px
        self.wing_phase = 0.0

        # Colors (Drosophila wild-type palette)
        self.body_color = QColor(160, 82, 45)       # Amber / brownish thorax
        self.abdomen_color = QColor(90, 50, 20)     # Striped darker brown abdomen
        self.stripe_color = QColor(40, 20, 10)      # Dark tergite stripes
        self.eye_color = QColor(190, 20, 20)        # Bright red compound eye
        self.wing_color = QColor(220, 240, 255, 140)# Translucent chitinous wings
        self.leg_color = QColor(50, 30, 15)         # Dark legs
        self.proboscis_color = QColor(200, 120, 70) # Flesh / pinkish proboscis

    def render(self, painter: QPainter, fly: FlyState, dt_s: float) -> None:
        """Draw the fly centered at (fly.x, fly.y) rotated to fly.heading_rad."""
        painter.save()

        # Update wing flap cycle when moving
        if fly.velocity_px_s > 5.0:
            self.wing_phase = (self.wing_phase + dt_s * 30.0) % (2 * math.pi)
        else:
            self.wing_phase = 0.0

        # Translate to fly origin & rotate
        painter.translate(fly.x, fly.y)
        painter.rotate(math.degrees(fly.heading_rad))

        s = self.size / 32.0  # Scale factor

        # 1. Draw Legs (6 legs)
        painter.setPen(QPen(self.leg_color, max(1.5, 1.5 * s)))
        # Front legs
        painter.drawLine(QPointF(2 * s, -4 * s), QPointF(10 * s, -12 * s))
        painter.drawLine(QPointF(2 * s, 4 * s), QPointF(10 * s, 12 * s))
        # Middle legs
        painter.drawLine(QPointF(-2 * s, -5 * s), QPointF(-2 * s, -14 * s))
        painter.drawLine(QPointF(-2 * s, 5 * s), QPointF(-2 * s, 14 * s))
        # Hind legs
        painter.drawLine(QPointF(-6 * s, -4 * s), QPointF(-12 * s, -13 * s))
        painter.drawLine(QPointF(-6 * s, 4 * s), QPointF(-12 * s, 13 * s))

        # 2. Draw Wings
        wing_wiggle = math.sin(self.wing_phase) * 6.0
        painter.setPen(QPen(QColor(180, 210, 240, 180), 1))
        painter.setBrush(QBrush(self.wing_color))

        # Left Wing
        painter.save()
        painter.translate(-2 * s, -3 * s)
        painter.rotate(-20 + wing_wiggle)
        painter.drawEllipse(QRectF(-14 * s, -4 * s, 14 * s, 7 * s))
        painter.restore()

        # Right Wing
        painter.save()
        painter.translate(-2 * s, 3 * s)
        painter.rotate(20 - wing_wiggle)
        painter.drawEllipse(QRectF(-14 * s, -3 * s, 14 * s, 7 * s))
        painter.restore()

        # 3. Draw Abdomen (segmented)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.abdomen_color))
        painter.drawEllipse(QRectF(-14 * s, -4.5 * s, 10 * s, 9 * s))

        # Abdominal stripes
        painter.setPen(QPen(self.stripe_color, 1.5 * s))
        painter.drawLine(QPointF(-11 * s, -4 * s), QPointF(-11 * s, 4 * s))
        painter.drawLine(QPointF(-8 * s, -4.5 * s), QPointF(-8 * s, 4.5 * s))
        painter.drawLine(QPointF(-5 * s, -4 * s), QPointF(-5 * s, 4 * s))

        # 4. Draw Thorax
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.body_color))
        painter.drawEllipse(QRectF(-5 * s, -4 * s, 8 * s, 8 * s))

        # 5. Draw Head
        painter.drawEllipse(QRectF(3 * s, -3 * s, 5 * s, 6 * s))

        # 6. Draw Compound Eyes (Left & Right)
        painter.setBrush(QBrush(self.eye_color))
        painter.drawEllipse(QRectF(4 * s, -4.5 * s, 3.5 * s, 3.5 * s))
        painter.drawEllipse(QRectF(4 * s, 1.0 * s, 3.5 * s, 3.5 * s))

        # 7. Proboscis (Extends during feeding / PER)
        if fly.proboscis_extended or fly.is_feeding:
            painter.setPen(QPen(self.proboscis_color, 2.0 * s))
            painter.drawLine(QPointF(8 * s, 0), QPointF(14 * s, 0))
            # Labellum tip
            painter.setBrush(QBrush(self.eye_color))
            painter.drawEllipse(QRectF(13 * s, -1.5 * s, 3 * s, 3 * s))

        painter.restore()

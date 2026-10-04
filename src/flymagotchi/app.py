"""Main application entry point for Fly-Magotchi.

Wires the transparent overlay (fly), the draggable sugar widget, and the
simulation controller together behind a QTimer that drives GUI frames.
"""

import sys
import time

from PyQt6.QtCore import QTimer, QPointF
from PyQt6.QtWidgets import QApplication

from flymagotchi.brain.circuit import Circuit
from flymagotchi.config import DEFAULT_CONFIG
from flymagotchi.simulation.controller import SimulationController
from flymagotchi.ui.overlay import FlyOverlay
from flymagotchi.ui.sugar_widget import SugarWidget


def load_circuit() -> Circuit:
    """Load the packaged circuit artifact, falling back to the screen center."""
    circuit_dir = DEFAULT_CONFIG.circuit_dir
    if not circuit_dir.exists():
        print(
            f"Circuit artifact not found at {circuit_dir}.\n"
            "Build it first with:  python tools/build_mock_circuit.py",
            file=sys.stderr,
        )
        raise FileNotFoundError(circuit_dir)
    return Circuit.load(circuit_dir)


def main() -> int:
    """Launch the Fly-Magotchi desktop application."""
    try:
        circuit = load_circuit()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Failed to load circuit: {exc}", file=sys.stderr)
        return 1

    app = QApplication(sys.argv)

    overlay = FlyOverlay()
    overlay.show()

    sugar = SugarWidget(size=DEFAULT_CONFIG.ui.sugar_size_px)
    sugar.show()

    controller = SimulationController(circuit=circuit, config=DEFAULT_CONFIG)
    controller.set_sugar_position((sugar.pos.x(), sugar.pos.y()))
    sugar.position_changed.connect(controller.set_sugar_position)

    frame_interval_ms = max(1, int(1000 / DEFAULT_CONFIG.ui.fps))
    last_tick = time.perf_counter()

    def on_tick() -> None:
        nonlocal last_tick
        now = time.perf_counter()
        dt_s = min(now - last_tick, 0.1)  # clamp to avoid huge catch-up bursts
        last_tick = now

        fly_state, rates = controller.step_frame(dt_s)

        # Fly lives in global desktop coordinates; the overlay covers the
        # primary screen so the two share one coordinate space.
        overlay.update_scene(fly_state, controller.sugar_pos, rates)

    timer = QTimer()
    timer.timeout.connect(on_tick)
    timer.start(frame_interval_ms)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
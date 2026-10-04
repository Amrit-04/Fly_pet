"""Centralized configuration for Fly-Magotchi.

All parameters for LIF dynamics, biological connectome, simulation rates,
sensory stimulation, and behavioral decoding are defined here.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class LIFParams:
    """LIF biological parameters from Shiu et al., Nature 2024."""
    # Membrane potentials in mV
    v_rest: float = -52.0
    v_reset: float = -52.0
    v_threshold: float = -45.0

    # Time constants in ms
    tau_membrane: float = 20.0  # ms
    tau_synapse: float = 5.0    # ms

    # Absolute refractory period in ms
    refractory_period: float = 2.2  # ms

    # Axonal / synaptic transmission delay in ms
    synaptic_delay: float = 1.8  # ms

    # Unitary synaptic conductance / weight scale in mV per anatomical synapse
    w_syn: float = 0.275  # mV / synapse count


@dataclass(frozen=True)
class SimulationParams:
    """Numerical simulation parameters."""
    dt: float = 0.1  # Biological timestep in ms (10,000 steps/sec)
    steps_per_frame: int = 330  # Steps per GUI frame (~33ms at 30 FPS = 330 steps of 0.1ms)
    random_seed: Optional[int] = 42


@dataclass(frozen=True)
class SensoryParams:
    """Sensory stimulation parameters."""
    # Maximum Poisson spike rate in Hz when immediately on sugar
    max_poisson_rate_hz: float = 150.0

    # Distance in desktop pixels within which sugar is detected
    detection_radius_px: float = 250.0

    # Proximity threshold in pixels considered "arrived at sugar"
    arrival_radius_px: float = 40.0

    # Baseline spontaneous sensory rate in Hz
    baseline_rate_hz: float = 2.0


@dataclass(frozen=True)
class DecoderParams:
    """Behavioral decoder parameters mapping population firing rates to action."""
    # Minimum window in ms for rate calculation
    rate_window_ms: float = 50.0

    # Firing rate threshold (Hz) in feeding motor neurons (MN9/MN11) to trigger feeding
    feeding_threshold_hz: float = 25.0

    # Firing rate threshold (Hz) in stop/MDN neurons to suppress locomotion
    stop_threshold_hz: float = 20.0

    # Firing rate threshold (Hz) in forward descending neurons (DNa) to drive walking
    walk_threshold_hz: float = 15.0

    # Kinematic speeds in pixels/sec
    walk_speed_px_s: float = 85.0
    approach_speed_px_s: float = 110.0


@dataclass(frozen=True)
class UIParams:
    """UI and overlay parameters."""
    window_title: str = "Fly-Magotchi"
    fps: int = 30
    fly_size_px: int = 32
    sugar_size_px: int = 32
    enable_debug_panel: bool = False
    window_stays_on_top: bool = True
    transparent_background: bool = True


@dataclass
class Config:
    """Root configuration holding all sub-configurations."""
    lif: LIFParams = field(default_factory=LIFParams)
    simulation: SimulationParams = field(default_factory=SimulationParams)
    sensory: SensoryParams = field(default_factory=SensoryParams)
    decoder: DecoderParams = field(default_factory=DecoderParams)
    ui: UIParams = field(default_factory=UIParams)

    # Paths
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    data_dir: Path = field(init=False)
    circuit_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.data_dir = self.project_root / "data"
        self.circuit_dir = self.data_dir / "circuit"


# Global default configuration instance
DEFAULT_CONFIG = Config()

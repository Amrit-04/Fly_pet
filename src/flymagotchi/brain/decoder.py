"""Behavioral decoder mapping neural population activity to virtual fly motion."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
import numpy as np

from flymagotchi.brain.circuit import Circuit
from flymagotchi.config import DecoderParams, SensoryParams, DEFAULT_CONFIG


class BehaviorState(Enum):
    """Discrete behavior states of the virtual fly."""
    IDLE = auto()          # Wandering / baseline
    SEARCH = auto()        # Actively approaching a target
    FEEDING = auto()       # Proboscis extended, consuming sugar
    STOPPED = auto()       # Locomotion halted


@dataclass
class SensoryModel:
    """Virtual sensory input model based on sugar proximity."""
    params: SensoryParams = DEFAULT_CONFIG.sensory
    rng: Optional[np.random.Generator] = None

    def __post_init__(self) -> None:
        if self.rng is None:
            self.rng = np.random.default_rng(42)

    def compute_poisson_rate(self, distance_px: float) -> float:
        """Compute Poisson spike rate for sensory neurons based on distance.

        rate = baseline + (max_rate - baseline) * sigmoid(1 - distance/radius)
        """
        if distance_px >= self.params.detection_radius_px:
            return self.params.baseline_rate_hz

        # Sigmoidal proximity function
        proximity = 1.0 - (distance_px / self.params.detection_radius_px)
        return self.params.baseline_rate_hz + (self.params.max_poisson_rate_hz - self.params.baseline_rate_hz) * proximity

    def generate_sensory_spikes(
        self,
        distance_px: float,
        num_sensory_neurons: int,
        dt_s: float,
        duration_s: float,
    ) -> np.ndarray:
        """Generate Poisson spike trains for sensory neurons.

        Args:
            distance_px: Distance to sugar cube in pixels.
            num_sensory_neurons: Number of sensory neuron units to stimulate.
            dt_s: Time step in seconds.
            duration_s: Duration in seconds.

        Returns:
            Spike trains array [num_sensory_neurons, duration_s/dt_s]
        """
        num_steps = int(duration_s / dt_s)
        rate = self.compute_poisson_rate(distance_px)
        prob_per_step = rate * dt_s

        # Clamp probability to [0, 1]
        prob_per_step = np.clip(prob_per_step, 0.0, 1.0)

        # Generate Poisson-like spikes (Bernoulli approximation for small dt)
        spike_trains = self.rng.random((num_sensory_neurons, num_steps)) < prob_per_step
        return spike_trains.astype(np.float32)


@dataclass
class PopulationRates:
    """Running population firing rates from neural activity."""
    feeding_rate_hz: float = 0.0
    stop_rate_hz: float = 0.0
    walk_rate_hz: float = 0.0
    approach_rate_hz: float = 0.0


@dataclass
class DecodedBehavior:
    """Output of the behavioral decoder."""
    state: BehaviorState
    velocity_px_s: float = 0.0
    angular_velocity_rad_s: float = 0.0
    proboscis_extended: bool = False


class BehaviorDecoder:
    """Decodes population neural activity into behavior commands."""

    def __init__(
        self,
        circuit: Circuit,
        decoder_params: DecoderParams = DEFAULT_CONFIG.decoder,
    ) -> None:
        self.circuit = circuit
        self.params = decoder_params

        # Get indices for key functional groups
        self._sensory_indices = self.circuit.get_sensory_indices()
        self._motor_indices = self.circuit.get_motor_indices()
        self._descending_indices = self.circuit.get_descending_indices()

        # Identify specific neuron groups for population decoding
        self._mn_feeding_indices = self.circuit.get_indices_by_group("mn_feeding")
        self._dn_stop_indices = self.circuit.get_indices_by_group("dn_stop")
        self._dn_walk_indices = self.circuit.get_indices_by_group("dn_walk")
        self._dn_approach_indices = self.circuit.get_indices_by_group("dn_approach")

        # Running spike counts for rate estimation
        self.spike_window: List[np.ndarray] = []

    def update_rates(self, spikes: np.ndarray) -> PopulationRates:
        """Update running population firing rate estimates.

        Args:
            spikes: Boolean array [N] from current timestep.

        Returns:
            PopulationRates with estimated rates in Hz.
        """
        # Add current spikes to window
        self.spike_window.append(spikes.astype(np.float32))

        # Trim window to desired duration
        window_steps = int(self.params.rate_window_ms / 1000.0 / 0.0001)  # At dt=0.1ms
        while len(self.spike_window) > window_steps:
            self.spike_window.pop(0)

        # Compute rates per neuron
        if len(self.spike_window) == 0:
            return PopulationRates()

        spike_counts = np.sum(self.spike_window, axis=0)
        rate_dt = 0.0001  # 0.1 ms in seconds
        rates = spike_counts / (len(self.spike_window) * rate_dt)

        # Population rates (mean of group)
        feeding_rate = np.mean(rates[self._mn_feeding_indices]) if self._mn_feeding_indices else 0.0
        stop_rate = np.mean(rates[self._dn_stop_indices]) if self._dn_stop_indices else 0.0
        walk_rate = np.mean(rates[self._dn_walk_indices]) if self._dn_walk_indices else 0.0
        approach_rate = np.mean(rates[self._dn_approach_indices]) if self._dn_approach_indices else 0.0

        return PopulationRates(
            feeding_rate_hz=feeding_rate,
            stop_rate_hz=stop_rate,
            walk_rate_hz=walk_rate,
            approach_rate_hz=approach_rate,
        )

    def decode(self, rates: PopulationRates) -> DecodedBehavior:
        """Map population rates to behavior commands.

        Priority order (to handle conflicting signals):
        1. Feeding state (highest priority - stop & extend proboscis)
        2. Stop locomotion (if stop threshold exceeded)
        3. Approach / walk (if walk threshold exceeded)

        The biological circuit should naturally suppress locomotion during feeding,
        so this should reflect the real neural dynamics rather than hard-coded
        behavior overrides.
        """
        # Priority: feeding > stop > walk/approach
        if rates.feeding_rate_hz >= self.params.feeding_threshold_hz:
            return DecodedBehavior(
                state=BehaviorState.FEEDING,
                velocity_px_s=0.0,
                angular_velocity_rad_s=0.0,
                proboscis_extended=True,
            )

        if rates.stop_rate_hz >= self.params.stop_threshold_hz:
            return DecodedBehavior(
                state=BehaviorState.STOPPED,
                velocity_px_s=0.0,
                angular_velocity_rad_s=0.0,
                proboscis_extended=False,
            )

        if rates.walk_rate_hz >= self.params.walk_threshold_hz or rates.approach_rate_hz >= self.params.walk_threshold_hz:
            # Combined approach + walk: approach has higher speed
            if rates.approach_rate_hz >= self.params.walk_threshold_hz:
                vel = self.params.approach_speed_px_s
                state = BehaviorState.SEARCH
            else:
                vel = self.params.walk_speed_px_s
                state = BehaviorState.IDLE

            return DecodedBehavior(
                state=state,
                velocity_px_s=vel,
                angular_velocity_rad_s=0.0,  # Could be modulated by DNp01 asymmetry
                proboscis_extended=False,
            )

        # Default: wandering / idle
        return DecodedBehavior(
            state=BehaviorState.IDLE,
            velocity_px_s=0.0,
            angular_velocity_rad_s=0.0,
            proboscis_extended=False,
        )

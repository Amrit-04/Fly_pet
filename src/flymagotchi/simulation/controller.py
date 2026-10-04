"""Simulation controller for Fly-Magotchi.

Decouples the fast biological neural simulation timestep (dt = 0.1 ms, 10,000 Hz)
from the desktop graphical rendering frame rate (~30-60 FPS).
Ensures ultra-low CPU utilization by batching neural updates, caching distance metrics,
and minimizing allocations per frame.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional
import math
import numpy as np

from flymagotchi.brain.circuit import Circuit
from flymagotchi.brain.lif import LIFSimulator
from flymagotchi.brain.decoder import BehaviorDecoder, BehaviorState, DecodedBehavior, SensoryModel, PopulationRates
from flymagotchi.config import Config, DEFAULT_CONFIG


@dataclass
class FlyState:
    """Current 2D physical and kinematic state of the virtual fly."""
    x: float = 400.0
    y: float = 300.0
    heading_rad: float = 0.0
    velocity_px_s: float = 0.0
    behavior: BehaviorState = BehaviorState.IDLE
    proboscis_extended: bool = False
    is_feeding: bool = False


class SimulationController:
    """Manages the lifecycle of neural integration, sensory transduction, and kinematic updates.

    Designed for <5% CPU overhead:
    - Preallocates input buffers and reuses memory across GUI ticks.
    - Uses sparse sensory generation: only recalculates Poisson stimulus if fly/sugar
      position has changed by > 2 pixels.
    - Decouples GUI frame delta (e.g., 33ms) into a fixed batch of neural steps (e.g. 100-330 steps).
    """

    def __init__(
        self,
        circuit: Circuit,
        config: Config = DEFAULT_CONFIG,
    ) -> None:
        self.circuit = circuit
        self.config = config

        # Neural components
        self.lif = LIFSimulator(circuit=self.circuit, params=self.config.lif, dt=self.config.simulation.dt)
        self.decoder = BehaviorDecoder(circuit=self.circuit, decoder_params=self.config.decoder)
        self.sensory = SensoryModel(params=self.config.sensory)

        # Simulation parameters
        self.dt_ms = self.config.simulation.dt
        self.steps_per_frame = self.config.simulation.steps_per_frame

        # Preallocated buffers
        self.num_neurons = self.circuit.num_neurons
        self.sensory_indices = self.circuit.get_sensory_indices()
        self.num_sensory = len(self.sensory_indices)

        # Batch sensory buffer: [steps_per_frame, num_neurons]
        self._batch_inputs = np.zeros((self.steps_per_frame, self.num_neurons), dtype=np.float32)

        # Kinematic state
        self.fly = FlyState()
        self.sugar_pos: Optional[Tuple[float, float]] = None
        self._last_distance: float = -1.0
        self._cached_sensory_rate: float = self.config.sensory.baseline_rate_hz

        # Wandering dynamics generator
        self.rng = np.random.default_rng(self.config.simulation.random_seed)
        self._wander_heading_timer = 0.0

    def set_sugar_position(self, pos: Optional[Tuple[float, float]]) -> None:
        """Update or remove current sugar cube target on desktop."""
        self.sugar_pos = pos

    def step_frame(self, dt_frame_s: float) -> Tuple[FlyState, PopulationRates]:
        """Execute one complete GUI frame update.

        1. Transduce sensory stimulus based on distance to sugar.
        2. Advance LIF neural circuit by `steps_per_frame` (0.1ms biological dt each).
        3. Decode population rates into behavioral state.
        4. Update physical coordinates (kinematics, bounding box, heading).

        Args:
            dt_frame_s: Wall-clock duration elapsed since previous frame (e.g. 0.033s).

        Returns:
            Tuple of (FlyState, PopulationRates) for GUI rendering and diagnostics.
        """
        # 1. Sensory Transduction (Lightweight & Distance-cached)
        distance = self._compute_distance_to_sugar()

        # Check if distance shifted enough to warrant new rate calculation (>2px delta)
        if abs(distance - self._last_distance) > 2.0 or self._last_distance < 0:
            self._cached_sensory_rate = self.sensory.compute_poisson_rate(distance)
            self._last_distance = distance

        # Fill preallocated sensory input buffer
        self._batch_inputs.fill(0.0)
        prob_per_step = self._cached_sensory_rate * (self.dt_ms / 1000.0)

        if prob_per_step > 0.0 and self.num_sensory > 0:
            # Poisson arrival approximation across sensory neurons
            random_draws = self.rng.random((self.steps_per_frame, self.num_sensory))
            spikes = random_draws < prob_per_step
            # Inject 15.0 mV excitatory potential on spike arrival
            self._batch_inputs[:, self.sensory_indices] = spikes.astype(np.float32) * 15.0

        # 2. Advance LIF Simulation (Vectorized batch execution)
        spike_raster, _ = self.lif.run_steps(self.steps_per_frame, self._batch_inputs)

        # 3. Behavioral Decoding
        # Sample spike population rates from the terminal window of the frame
        last_spikes = spike_raster[-1]
        rates = self.decoder.update_rates(last_spikes)
        behavior = self.decoder.decode(rates)

        # 4. Update Kinematics based on Decoded Action
        self._update_kinematics(behavior, dt_frame_s, distance)

        return self.fly, rates

    def _compute_distance_to_sugar(self) -> float:
        """Compute Euclidean distance from fly center to sugar cube."""
        if self.sugar_pos is None:
            return 9999.0
        dx = self.sugar_pos[0] - self.fly.x
        dy = self.sugar_pos[1] - self.fly.y
        return math.hypot(dx, dy)

    def _update_kinematics(self, behavior: DecodedBehavior, dt_frame_s: float, distance_to_sugar: float) -> None:
        """Integrate 2D position and orientation according to decoded behavioral state."""
        self.fly.behavior = behavior.state
        self.fly.proboscis_extended = behavior.proboscis_extended

        if behavior.state == BehaviorState.FEEDING:
            # Fly ceases forward walking; stops and consumes food
            self.fly.velocity_px_s = 0.0
            self.fly.is_feeding = True
            return

        self.fly.is_feeding = False

        if behavior.state == BehaviorState.STOPPED:
            self.fly.velocity_px_s = 0.0
            return

        if behavior.state == BehaviorState.SEARCH:
            # Steer directly towards sugar location
            self.fly.velocity_px_s = behavior.velocity_px_s
            if self.sugar_pos is not None:
                dx = self.sugar_pos[0] - self.fly.x
                dy = self.sugar_pos[1] - self.fly.y
                target_heading = math.atan2(dy, dx)

                # Smooth angular turn towards target
                angle_diff = (target_heading - self.fly.heading_rad + math.pi) % (2 * math.pi) - math.pi
                turn_rate = 5.0 * dt_frame_s
                self.fly.heading_rad += math.copysign(min(abs(angle_diff), turn_rate), angle_diff)

        elif behavior.state == BehaviorState.IDLE:
            # Baseline wandering motion
            self.fly.velocity_px_s = self.config.decoder.walk_speed_px_s * 0.5

            # Periodic heading perturbation (Brownian walk)
            self._wander_heading_timer -= dt_frame_s
            if self._wander_heading_timer <= 0:
                self.fly.heading_rad += self.rng.uniform(-0.6, 0.6)
                self._wander_heading_timer = self.rng.uniform(0.5, 2.0)

        # Apply displacement
        vx = self.fly.velocity_px_s * math.cos(self.fly.heading_rad)
        vy = self.fly.velocity_px_s * math.sin(self.fly.heading_rad)
        self.fly.x += vx * dt_frame_s
        self.fly.y += vy * dt_frame_s

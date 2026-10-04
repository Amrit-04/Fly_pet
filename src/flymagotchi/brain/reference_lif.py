"""Reference Leaky Integrate-and-Fire (LIF) simulator.

Prioritizes mathematical clarity, biological correctness, and readability.
Serves as the ground-truth reference for validating the optimized LIF engine.
Follows Shiu et al., Nature 2024 parameters.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from flymagotchi.brain.circuit import Circuit
from flymagotchi.config import LIFParams, DEFAULT_CONFIG


@dataclass
class ReferenceNeuronState:
    """State of a single LIF neuron in the reference implementation."""
    v: float                          # Membrane potential in mV
    synaptic_current: float = 0.0     # Synaptic input in mV
    refractory_steps_left: int = 0    # Steps remaining in refractory period
    spike_history: List[int] = field(default_factory=list)  # Step indices when spiked


class ReferenceLIFSimulator:
    """Explicit, step-by-step reference LIF simulator."""

    def __init__(
        self,
        circuit: Circuit,
        params: LIFParams = DEFAULT_CONFIG.lif,
        dt: float = 0.1,  # ms
    ) -> None:
        self.circuit = circuit
        self.params = params
        self.dt = dt
        self.num_neurons = circuit.num_neurons

        # Exponential decay factors
        self.alpha_m = float(np.exp(-self.dt / self.params.tau_membrane))
        self.alpha_s = float(np.exp(-self.dt / self.params.tau_synapse))
        self.refractory_steps = max(1, int(round(self.params.refractory_period / self.dt)))

        # Delay queue for incoming synaptic events:
        # dict mapping arrival_step -> list of (target_neuron_idx, weight_mV)
        self.synaptic_delay_queue: Dict[int, List[Tuple[int, float]]] = {}

        # Precompute edge lookup by source: source_idx -> list of (target_idx, weight, delay_steps)
        self.adjacency: Dict[int, List[Tuple[int, float, int]]] = {i: [] for i in range(self.num_neurons)}
        for src, tgt, w, d_ms in zip(
            self.circuit.source_indices,
            self.circuit.target_indices,
            self.circuit.weights,
            self.circuit.delays_ms,
        ):
            delay_steps = max(1, int(round(float(d_ms) / self.dt)))
            self.adjacency[int(src)].append((int(tgt), float(w), delay_steps))

        self.current_step = 0
        self.neuron_states = [
            ReferenceNeuronState(v=self.params.v_rest)
            for _ in range(self.num_neurons)
        ]

    def reset(self) -> None:
        """Reset all neurons to resting potential and clear history."""
        self.current_step = 0
        self.synaptic_delay_queue.clear()
        for state in self.neuron_states:
            state.v = self.params.v_rest
            state.synaptic_current = 0.0
            state.refractory_steps_left = 0
            state.spike_history.clear()

    def step(self, external_inputs: Optional[np.ndarray] = None) -> np.ndarray:
        """Simulate a single biological timestep (dt).

        Args:
            external_inputs: Optional float array [N] of external currents/potentials in mV.

        Returns:
            Boolean array [N] indicating which neurons spiked at this step.
        """
        spikes = np.zeros(self.num_neurons, dtype=bool)

        # 1. Decay synaptic current and apply arriving delayed synaptic inputs
        arriving_events = self.synaptic_delay_queue.pop(self.current_step, [])
        arriving_inputs = [0.0] * self.num_neurons
        for tgt_idx, weight in arriving_events:
            arriving_inputs[tgt_idx] += weight

        for i, state in enumerate(self.neuron_states):
            # Synaptic current exponential decay + incoming spikes
            state.synaptic_current = (state.synaptic_current * self.alpha_s) + arriving_inputs[i]

        # 2. Update membrane potential
        for i, state in enumerate(self.neuron_states):
            ext_i = float(external_inputs[i]) if external_inputs is not None else 0.0

            if state.refractory_steps_left > 0:
                state.v = self.params.v_reset
                state.refractory_steps_left -= 1
            else:
                # Membrane potential integration
                v_leak = self.params.v_rest + (state.v - self.params.v_rest) * self.alpha_m
                # Synaptic integration: (dt / tau_membrane) * synaptic_current
                v_syn = state.synaptic_current * (self.dt / self.params.tau_membrane)
                state.v = v_leak + v_syn + ext_i

                # 3. Threshold check & Spike generation
                if state.v >= self.params.v_threshold:
                    spikes[i] = True
                    state.v = self.params.v_reset
                    state.refractory_steps_left = self.refractory_steps
                    state.spike_history.append(self.current_step)

                    # Propagate spikes along outgoing edges with axonal delay
                    for tgt_idx, weight, delay_steps in self.adjacency[i]:
                        arrival_step = self.current_step + delay_steps
                        self.synaptic_delay_queue.setdefault(arrival_step, []).append((tgt_idx, weight))

        self.current_step += 1
        return spikes

    def run(self, num_steps: int, external_inputs: Optional[np.ndarray] = None) -> np.ndarray:
        """Run simulation for num_steps and return full spike raster [num_steps, N]."""
        raster = np.zeros((num_steps, self.num_neurons), dtype=bool)
        for t in range(num_steps):
            ext = external_inputs[t] if external_inputs is not None and external_inputs.ndim == 2 else external_inputs
            raster[t] = self.step(ext)
        return raster

"""Vectorized Leaky Integrate-and-Fire (LIF) simulator.

Optimized NumPy implementation designed for high real-time simulation factors
without GPU or external dependencies.
Maintains exact numerical agreement with the ReferenceLIFSimulator.
"""

from typing import Optional, Tuple
import numpy as np

from flymagotchi.brain.circuit import Circuit
from flymagotchi.config import LIFParams, DEFAULT_CONFIG


class LIFSimulator:
    """High-performance, preallocated NumPy LIF simulator."""

    def __init__(
        self,
        circuit: Circuit,
        params: LIFParams = DEFAULT_CONFIG.lif,
        dt: float = 0.1,  # ms
    ) -> None:
        self.circuit = circuit
        self.params = params
        self.dt = float(dt)
        self.num_neurons = circuit.num_neurons

        # Constants (float32 for speed & memory efficiency)
        self.v_rest = np.float32(self.params.v_rest)
        self.v_reset = np.float32(self.params.v_reset)
        self.v_threshold = np.float32(self.params.v_threshold)
        self.alpha_m = np.float32(np.exp(-self.dt / self.params.tau_membrane))
        self.alpha_s = np.float32(np.exp(-self.dt / self.params.tau_synapse))
        self.dt_over_tau_m = np.float32(self.dt / self.params.tau_membrane)
        self.refractory_steps = max(1, int(round(self.params.refractory_period / self.dt)))

        # Preallocate neuron state vectors
        self.v = np.full(self.num_neurons, self.v_rest, dtype=np.float32)
        self.synaptic_current = np.zeros(self.num_neurons, dtype=np.float32)
        self.refractory_timer = np.zeros(self.num_neurons, dtype=np.int32)
        self.spikes = np.zeros(self.num_neurons, dtype=bool)

        # Precompute sparse connectivity grouped by source neuron
        # For each source neuron i: target_indices, weights, delay_steps
        self.out_targets = []
        self.out_weights = []
        self.out_delays = []

        max_delay = 1
        for i in range(self.num_neurons):
            mask = self.circuit.source_indices == i
            tgts = self.circuit.target_indices[mask].astype(np.int32)
            w = self.circuit.weights[mask].astype(np.float32)
            d_ms = self.circuit.delays_ms[mask]
            d_steps = np.maximum(1, np.round(d_ms / self.dt)).astype(np.int32)

            self.out_targets.append(tgts)
            self.out_weights.append(w)
            self.out_delays.append(d_steps)

            if len(d_steps) > 0:
                max_delay = max(max_delay, int(np.max(d_steps)))

        # Ring buffer for synaptic delay delivery: [buffer_len, num_neurons]
        self.buffer_len = max_delay + 2
        self.delay_buffer = np.zeros((self.buffer_len, self.num_neurons), dtype=np.float32)
        self.ring_idx = 0
        self.current_step = 0

    def reset(self) -> None:
        """Reset all state variables to resting conditions."""
        self.v.fill(self.v_rest)
        self.synaptic_current.fill(0.0)
        self.refractory_timer.fill(0)
        self.spikes.fill(False)
        self.delay_buffer.fill(0.0)
        self.ring_idx = 0
        self.current_step = 0

    def step(self, external_inputs: Optional[np.ndarray] = None) -> np.ndarray:
        """Execute one simulation timestep dt.

        Args:
            external_inputs: Optional float32 array [N] of input potentials in mV.

        Returns:
            Boolean array [N] indicating spike occurrences at this step.
        """
        # 1. Fetch arriving synaptic inputs from delay ring buffer
        arriving_inputs = self.delay_buffer[self.ring_idx]

        # 2. Update synaptic current: exponential decay + arriving inputs
        self.synaptic_current = (self.synaptic_current * self.alpha_s) + arriving_inputs

        # Clear processed ring buffer slot for reuse
        arriving_inputs.fill(0.0)

        # 3. Update membrane potential
        # Vectorized leak towards v_rest: v_leak = v_rest + (v - v_rest) * alpha_m
        v_leak = self.v_rest + (self.v - self.v_rest) * self.alpha_m
        v_syn = self.synaptic_current * self.dt_over_tau_m

        if external_inputs is not None:
            self.v = v_leak + v_syn + external_inputs
        else:
            self.v = v_leak + v_syn

        # 4. Handle refractory states (clamp refractory neurons to v_reset)
        in_refractory = self.refractory_timer > 0
        if np.any(in_refractory):
            self.v[in_refractory] = self.v_reset
            self.refractory_timer[in_refractory] -= 1

        # 5. Detect threshold crossings (spikes)
        # Exclude currently refractory neurons
        new_spikes = (self.v >= self.v_threshold) & (~in_refractory)
        self.spikes = new_spikes

        # 6. Apply reset and initiate refractory period for spiking neurons
        if np.any(new_spikes):
            self.v[new_spikes] = self.v_reset
            self.refractory_timer[new_spikes] = self.refractory_steps

            # 7. Propagate spikes to downstream targets via delay ring buffer
            spiking_indices = np.where(new_spikes)[0]
            for src_idx in spiking_indices:
                tgts = self.out_targets[src_idx]
                if len(tgts) == 0:
                    continue
                w = self.out_weights[src_idx]
                delays = self.out_delays[src_idx]

                # Distribute into ring buffer slots
                # target_slot = (ring_idx + delay_step) % buffer_len
                for tgt, weight, delay_step in zip(tgts, w, delays):
                    slot = (self.ring_idx + delay_step) % self.buffer_len
                    self.delay_buffer[slot, tgt] += weight

        # Advance ring buffer index and step counter
        self.ring_idx = (self.ring_idx + 1) % self.buffer_len
        self.current_step += 1

        return self.spikes

    def run_steps(
        self,
        num_steps: int,
        external_inputs: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Run batch simulation for num_steps.

        Args:
            num_steps: Number of integration steps to run.
            external_inputs: Optional 2D array [num_steps, N] or 1D array [N].

        Returns:
            Tuple of (spike_raster [num_steps, N], membrane_potentials [num_steps, N])
        """
        spike_raster = np.zeros((num_steps, self.num_neurons), dtype=bool)
        v_trace = np.zeros((num_steps, self.num_neurons), dtype=np.float32)

        has_2d_input = external_inputs is not None and external_inputs.ndim == 2

        for t in range(num_steps):
            ext_t = external_inputs[t] if has_2d_input else external_inputs
            spikes_t = self.step(ext_t)
            spike_raster[t] = spikes_t
            v_trace[t] = self.v

        return spike_raster, v_trace

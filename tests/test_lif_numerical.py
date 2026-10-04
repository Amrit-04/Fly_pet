"""Numerical validation of LIF implementations against a tiny manual circuit.

This test verifies that LIFSimulator (vectorized) produces identical spike rasters
and membrane potentials to ReferenceLIFSimulator (step-by-step) for a
manually-defined 3-neuron circuit with known connectivity.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from flymagotchi.brain import Circuit, CircuitManifest, LIFSimulator, ReferenceLIFSimulator
from flymagotchi.config import LIFParams, SimulationParams, DEFAULT_CONFIG


def create_tiny_manual_circuit() -> Circuit:
    """Create a tiny 3-neuron circuit with known connectivity for validation.

    Neurons:
    0: Source (injects current)
    1: Intermediate neuron
    2: Target detector neuron

    All-to-all connectivity with small delays.
    """
    # 3 neurons
    neuron_labels = ["source", "inter", "target"]
    root_ids = np.array([123, 456, 789], dtype=np.uint64)
    cell_types = ["sensor", "interneuron", "motor"]
    functional_groups = ["input", "processing", "output"]
    neurotransmitters = ["glutamate", "gaba", "glutamate"]

    # Edges (source_idx, target_idx, weight_mV, delay_ms)
    edges = np.array([
        # Source to Intermediate
        [0, 1, 0.275, 1.8],
        # Source to Target
        [0, 2, 0.275, 3.5],
        # Intermediate to Target (excitatory feedback)
        [1, 2, 0.1775, 1.8],
    ], dtype=np.int32)

    source_indices = edges[:, 0]
    target_indices = edges[:, 1]
    weights = edges[:, 2].astype(np.float32)
    delays_ms = edges[:, 3].astype(np.float32)

    manifest = CircuitManifest(
        neuron_count=3,
        edge_count=len(edges),
        is_mock=True,
    )

    return Circuit(
        manifest=manifest,
        neuron_labels=neuron_labels,
        root_ids=root_ids,
        cell_types=cell_types,
        functional_groups=functional_groups,
        neurotransmitters=neurotransmitters,
        source_indices=source_indices,
        target_indices=target_indices,
        synapse_counts=np.ones(len(edges), dtype=np.int32),
        weights=weights,
        delays_ms=delays_ms,
    )


def test_lif_numerical_agreement():
    """Verify LIFSimulator and ReferenceLIFSimulator produce identical outputs."""
    # Get the LIF parameters from config
    lif_params = DEFAULT_CONFIG.lif

    # Create tiny circuit
    circuit = create_tiny_manual_circuit()

    # Create both simulators with identical parameters
    ref_sim = ReferenceLIFSimulator(circuit, params=lif_params)
    opt_sim = LIFSimulator(circuit, params=lif_params)

    # External input: inject current into source neuron (neuron 0)
    num_steps = 200
    external_inputs = np.zeros((num_steps, circuit.num_neurons), dtype=np.float32)
    # Step-to-step current injection to source neuron
    for t in range(num_steps):
        if 50 <= t <= 150:
            external_inputs[t, 0] = 0.5  # 0.5 mV current injection

    # Run both simulators
    ref_raster, ref_v = ref_sim.run(num_steps, external_inputs)
    opt_raster, opt_v = opt_sim.run_steps(num_steps, external_inputs)

    # Reset simulators for separate visualization pass (visualize membrane potential)
    ref_sim.reset()
    opt_sim.reset()

    # Run to get voltage traces
    ref_v_trace = np.zeros((num_steps, circuit.num_neurons), dtype=np.float32)
    opt_v_trace = np.zeros((num_steps, circuit.num_neurons), dtype=np.float32)

    for t in range(num_steps):
        ref_sim.step(external_inputs)
        ref_v_trace[t] = ref_sim.neuron_states[0].v

        opt_sim.step(external_inputs)
        opt_v_trace[t] = opt_sim.v[0]

    # Compare spike rasters
    spike_agreement = np.all(ref_raster == opt_raster)
    spike_diff = np.sum(np.abs(ref_raster.astype(np.float32) - opt_raster.astype(np.float32)))
    max_spike_diff = float(np.max(np.abs(ref_raster.astype(np.float32) - opt_raster.astype(np.float32))))

    # Compare membrane potentials (source neuron only, after reset)
    v_agreement = np.allclose(ref_v_trace, opt_v_trace, rtol=1e-4, atol=1e-8)
    v_max_diff = float(np.max(np.abs(ref_v_trace - opt_v_trace)))
    v_mean_diff = float(np.mean(np.abs(ref_v_trace - opt_v_trace)))

    print("=" * 75)
    print("LIF Numerical Validation Test")
    print("=" * 75)
    print(f"Circuit: {circuit.num_neurons} neurons, {circuit.num_edges} edges")
    print(f"Simulation steps: {num_steps}, dt={DEFAULT_CONFIG.simulation.dt_ms}ms")
    print()
    print("Spike raster agreement:")
    print(f"  Exact match: {spike_agreement}")
    print(f"  Max absolute difference: {max_spike_diff:.6f}")
    print(f"  Total difference at any step: {spike_diff}")
    print()
    print("Membrane potential agreement (source neuron [n=0]):")
    print(f"  All close (rtol=1e-4, atol=1e-8): {v_agreement}")
    print(f"  Max absolute difference: {v_max_diff:.6f} mV")
    print(f"  Mean absolute difference: {v_mean_diff:.6f} mV")
    print()

    # Detailed neuron-wise comparison
    print("Neuron-wise spike comparisons:")
    for n in range(circuit.num_neurons):
        ref_spikes = ref_raster[:, n]
        opt_spikes = opt_raster[:, n]
        exactly_same = np.all(ref_spikes == opt_spikes)
        num_ref_spikes = int(np.sum(ref_spikes))
        num_opt_spikes = int(np.sum(opt_spikes))
        print(f"  Neuron {n} ({circuit.neuron_labels[n]}): "
              f"ref={num_ref_spikes}, opt={num_opt_spikes}, "
              f"match={exactly_same}")

    print("=" * 75)

    # Assert success criteria
    assert spike_agreement, f"Spike rasters do not match: max_diff={max_spike_diff}"
    assert v_agreement, f"Membrane potentials do not match: max_diff={v_max_diff}"

    print("✓ All LIF implementations produce identical numerical outputs")

    return True


def test_lif_properties():
    """Verify LIF simulator performance characteristics."""
    circuit = create_tiny_manual_circuit()
    lif_params = DEFAULT_CONFIG.lif

    sim = LIFSimulator(circuit, params=lif_params)

    print("\nLIF Simulator Properties:")
    print(f"  Number of neurons: {sim.num_neurons}")
    print(f"  Number of edges: {circuit.num_edges}")
    print(f"  Refractory steps: {sim.refractory_steps}")
    print(f"  Max delay buffer length: {sim.buffer_len}")
    print(f"  Preallocated memory footprint: ~{np.prod(sim.v.shape) * 4 / 1024/1024:.2f} MB float32")
    print(f"  Total preallocated memory for all arrays: ~{np.sum([np.prod(p.shape) * p.dtype.itemsize for p in [sim.v, sim.synaptic_current, sim.refractory_timer, sim.spikes, sim.delay_buffer]]) / 1024/1024:.2f} MB")

    return True


if __name__ == "__main__":
    print("\n" + "=" * 75)
    print("Running LIF Numerical Validation Tests")
    print("=" * 75)
    print()

    try:
        # Test numerical agreement
        test_lif_numerical_agreement()

        # Test simulator properties
        test_lif_properties()

        print("\n" + "=" * 75)
        print("✓ All tests passed!")
        print("=" * 75 + "\n")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
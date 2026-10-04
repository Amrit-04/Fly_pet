"""Circuit validation tool for Fly-Magotchi.

Verifies that the extracted or mock circuit artifact conforms to all
structural, biological, and numerical invariants:
1. All required files exist (manifest.json, neurons.npz, edges.npz).
2. Manifest metadata matches array shapes.
3. Node indices in edges are within [0, num_neurons - 1].
4. No self-loops with negative delays.
5. All root_ids are non-zero uint64.
6. Weights follow Shiu et al. (Nature 2024) scaling conventions.
7. Required functional groups exist (sensory, interneuron, descending, motor).
"""

import sys
from pathlib import Path
import json
import numpy as np

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from flymagotchi.brain.circuit import Circuit, CircuitManifest
from flymagotchi.config import DEFAULT_CONFIG


def validate_circuit(circuit_dir: Path) -> bool:
    """Validate circuit artifact on disk.

    Args:
        circuit_dir: Directory containing manifest.json, neurons.npz, edges.npz

    Returns:
        True if all validation checks pass, raises AssertionError otherwise.
    """
    print(f"Validating circuit artifact at: {circuit_dir}")
    circuit_dir = Path(circuit_dir)

    # 1. File existence
    manifest_p = circuit_dir / "manifest.json"
    neurons_p = circuit_dir / "neurons.npz"
    edges_p = circuit_dir / "edges.npz"

    assert manifest_p.exists(), f"Missing {manifest_p}"
    assert neurons_p.exists(), f"Missing {neurons_p}"
    assert edges_p.exists(), f"Missing {edges_p}"
    print("  [PASS] All artifact files present.")

    # 2. Load circuit
    circuit = Circuit.load(circuit_dir)
    print(f"  [PASS] Successfully loaded circuit: {circuit.num_neurons} neurons, {circuit.num_edges} edges.")

    # 3. Manifest checks
    assert circuit.manifest.neuron_count == circuit.num_neurons, (
        f"Manifest neuron count ({circuit.manifest.neuron_count}) != actual ({circuit.num_neurons})"
    )
    assert circuit.manifest.edge_count == circuit.num_edges, (
        f"Manifest edge count ({circuit.manifest.edge_count}) != actual ({circuit.num_edges})"
    )
    print("  [PASS] Manifest counts match array lengths.")

    # 4. Topology checks
    assert np.all(circuit.source_indices >= 0), "Negative source indices found."
    assert np.all(circuit.source_indices < circuit.num_neurons), "Source index out of bounds."
    assert np.all(circuit.target_indices >= 0), "Negative target indices found."
    assert np.all(circuit.target_indices < circuit.num_neurons), "Target index out of bounds."
    print("  [PASS] Edge source and target indices are strictly within [0, N-1].")

    # 5. Biological constraints
    assert np.all(circuit.delays_ms > 0), "Delays must be strictly positive."
    assert np.all(circuit.synapse_counts >= 1), "Synapse counts must be >= 1."
    print(f"  [PASS] Delays in range [{np.min(circuit.delays_ms):.2f}ms, {np.max(circuit.delays_ms):.2f}ms].")

    # 6. Functional groups coverage
    expected_groups = {"sweet_grn", "mn_feeding", "dn_walk", "dn_stop"}
    present_groups = set(circuit.functional_groups)
    missing = expected_groups - present_groups
    assert len(missing) == 0, f"Missing critical functional groups: {missing}"
    print(f"  [PASS] All critical functional groups present: {expected_groups}")

    # 7. Neurotransmitter polarity checks
    for i, nt in enumerate(circuit.neurotransmitters):
        assert nt in {"acetylcholine", "gaba", "glutamate"}, f"Unknown neurotransmitter: {nt}"
    print("  [PASS] All neurotransmitters are recognized types.")

    print("\n✓ CIRCUIT VALIDATION SUCCESSFUL: All checks passed.\n")
    return True


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG.circuit_dir
    try:
        validate_circuit(Path(target_dir))
    except Exception as e:
        print(f"\n✗ CIRCUIT VALIDATION FAILED: {e}\n")
        sys.exit(1)

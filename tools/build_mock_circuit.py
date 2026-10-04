"""Build a functional mock connectome artifact for Fly-Magotchi out-of-the-box execution.

Creates a synthetic yet structurally authentic Drosophila gustatory/feeding/locomotion
subgraph matching the biological cell types and functional groups expected by the engine.

Does not require external FlyWire API credentials.
Generates:
  - data/circuit/manifest.json
  - data/circuit/neurons.npz
  - data/circuit/edges.npz
"""

import json
import sys
from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flymagotchi.brain.circuit import Circuit, CircuitManifest
from flymagotchi.config import DEFAULT_CONFIG


def generate_mock_circuit(num_neurons: int = 40, seed: int = 42) -> Circuit:
    """Generate a mock Drosophila circuit with realistic functional groups.

    Structure:
    - 10 Sweet Gustatory Receptor Neurons (GRNs / sensory)
    - 10 SEZ Feeding Interneurons (interneuron)
    - 10 Descending Neurons (DNs: walk, stop, approach)
    - 10 Motor Neurons (mn_feeding, mn_locomotion)

    Synaptic connections mimic the known feedforward/feedback motifs of the
    Drosophila feeding & locomotion control network.
    """
    rng = np.random.default_rng(seed)

    # 1. Define Neurons
    neuron_labels = []
    root_ids = []
    cell_types = []
    functional_groups = []
    neurotransmitters = []

    # Sensory neurons (0-9)
    for i in range(10):
        neuron_labels.append(f"GRN_sweet_{i+1}")
        root_ids.append(720575940600000000 + i)
        cell_types.append("sensory")
        functional_groups.append("sweet_grn")
        neurotransmitters.append("acetylcholine")

    # SEZ Interneurons (10-19)
    for i in range(10):
        label = f"SEZ_inter_{i+1}" if i < 8 else f"Fdg_inter_{i+1}"
        neuron_labels.append(label)
        root_ids.append(720575940610000000 + i)
        cell_types.append("interneuron")
        functional_groups.append("sez_fdg" if i >= 5 else "interneuron")
        neurotransmitters.append("acetylcholine" if i % 2 == 0 else "gaba")

    # Descending Neurons (20-29)
    # 20-23: DN_walk, 24-26: DN_stop, 27-29: DN_approach
    for i in range(10):
        if i < 4:
            grp = "dn_walk"
            lbl = f"DNa_walk_{i+1}"
        elif i < 7:
            grp = "dn_stop"
            lbl = f"MDN_stop_{i+1}"
        else:
            grp = "dn_approach"
            lbl = f"DNp_approach_{i+1}"

        neuron_labels.append(lbl)
        root_ids.append(720575940620000000 + i)
        cell_types.append("descending")
        functional_groups.append(grp)
        neurotransmitters.append("acetylcholine" if grp != "dn_stop" else "gaba")

    # Motor Neurons (30-39)
    # 30-34: MN_feeding (proboscis extension MN9/MN11), 35-39: MN_locomotion
    for i in range(10):
        if i < 5:
            grp = "mn_feeding"
            lbl = f"MN_proboscis_{i+9}"
        else:
            grp = "mn_locomotion"
            lbl = f"MN_leg_{i+1}"

        neuron_labels.append(lbl)
        root_ids.append(720575940630000000 + i)
        cell_types.append("motor")
        functional_groups.append(grp)
        neurotransmitters.append("glutamate")

    # 2. Build Synaptic Edges
    sources = []
    targets = []
    syn_counts = []
    weights = []
    delays = []

    # Connection rules (sparse, pathway-biased connectivity):
    # a. Sensory -> SEZ Interneurons (strong feedforward excitation)
    for src in range(10):
        # Each sensory neuron connects to 3-5 interneurons
        tgt_nodes = rng.choice(np.arange(10, 20), size=rng.integers(3, 6), replace=False)
        for tgt in tgt_nodes:
            count = rng.integers(5, 25)
            w = count * DEFAULT_CONFIG.lif.w_syn  # excitatory positive weight
            d = rng.uniform(1.2, 2.5)
            sources.append(src)
            targets.append(tgt)
            syn_counts.append(count)
            weights.append(w)
            delays.append(d)

    # b. SEZ Interneurons -> Descending Neurons
    for src in range(10, 20):
        # Connect to DNs (both walk/approach and stop)
        tgt_nodes = rng.choice(np.arange(20, 30), size=rng.integers(3, 7), replace=False)
        for tgt in tgt_nodes:
            count = rng.integers(5, 20)
            is_gaba = neurotransmitters[src] == "gaba"
            w = -count * DEFAULT_CONFIG.lif.w_syn if is_gaba else count * DEFAULT_CONFIG.lif.w_syn
            d = rng.uniform(1.5, 3.0)
            sources.append(src)
            targets.append(tgt)
            syn_counts.append(count)
            weights.append(w)
            delays.append(d)

    # c. SEZ Interneurons -> Feeding Motor Neurons (direct drive for proboscis)
    for src in range(15, 20):  # Fdg interneurons
        for tgt in range(30, 35):  # mn_feeding
            count = rng.integers(8, 30)
            w = count * DEFAULT_CONFIG.lif.w_syn
            d = rng.uniform(1.0, 2.0)
            sources.append(src)
            targets.append(tgt)
            syn_counts.append(count)
            weights.append(w)
            delays.append(d)

    # d. Descending Neurons -> Motor Neurons
    # DN_walk -> MN_locomotion
    for src in range(20, 24):
        for tgt in range(35, 40):
            count = rng.integers(5, 18)
            w = count * DEFAULT_CONFIG.lif.w_syn
            d = rng.uniform(1.8, 3.5)
            sources.append(src)
            targets.append(tgt)
            syn_counts.append(count)
            weights.append(w)
            delays.append(d)

    # DN_stop -> MN_locomotion (inhibition)
    for src in range(24, 27):
        for tgt in range(35, 40):
            count = rng.integers(10, 25)
            w = -count * DEFAULT_CONFIG.lif.w_syn  # Inhibitory
            d = rng.uniform(1.5, 2.8)
            sources.append(src)
            targets.append(tgt)
            syn_counts.append(count)
            weights.append(w)
            delays.append(d)

    # DN_approach -> MN_locomotion
    for src in range(27, 30):
        for tgt in range(35, 40):
            count = rng.integers(8, 22)
            w = count * DEFAULT_CONFIG.lif.w_syn
            d = rng.uniform(1.5, 3.0)
            sources.append(src)
            targets.append(tgt)
            syn_counts.append(count)
            weights.append(w)
            delays.append(d)

    # e. Feeding Motor Neurons -> Stop DNs (recurrent inhibition of walking during feeding)
    for src in range(30, 35):
        for tgt in range(24, 27):  # stop DNs or walk DNs
            count = rng.integers(5, 15)
            w = -count * DEFAULT_CONFIG.lif.w_syn  # Inhibitory feedback
            d = rng.uniform(1.0, 2.5)
            sources.append(src)
            targets.append(tgt)
            syn_counts.append(count)
            weights.append(w)
            delays.append(d)

    manifest = CircuitManifest(
        dataset="MOCK_BANC",
        version="v888_mock",
        description="Functional synthetic Drosophila connectome for out-of-the-box testing",
        neuron_count=len(neuron_labels),
        edge_count=len(sources),
        synapse_threshold=5,
        is_mock=True,
    )

    return Circuit(
        manifest=manifest,
        neuron_labels=neuron_labels,
        root_ids=np.array(root_ids, dtype=np.uint64),
        cell_types=cell_types,
        functional_groups=functional_groups,
        neurotransmitters=neurotransmitters,
        source_indices=np.array(sources, dtype=np.int32),
        target_indices=np.array(targets, dtype=np.int32),
        synapse_counts=np.array(syn_counts, dtype=np.int32),
        weights=np.array(weights, dtype=np.float32),
        delays_ms=np.array(delays, dtype=np.float32),
    )


def main():
    """Build and save mock circuit artifact to data/circuit/."""
    output_dir = DEFAULT_CONFIG.circuit_dir
    print(f"Generating mock Drosophila circuit...")
    circuit = generate_mock_circuit(num_neurons=40, seed=42)

    print(f"Saving compact circuit artifact to: {output_dir}")
    circuit.save(output_dir)

    print(f"✓ Mock circuit successfully built and saved!")
    print(f"  Neurons: {circuit.num_neurons}")
    print(f"  Edges: {circuit.num_edges}")
    print(f"  Functional groups: {set(circuit.functional_groups)}")
    print(f"  Is Mock: {circuit.manifest.is_mock}")


if __name__ == "__main__":
    main()
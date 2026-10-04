"""Circuit representation and biological neuron metadata."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


@dataclass
class CircuitManifest:
    """Metadata describing the biological dataset and extraction."""
    dataset: str = "BANC"
    version: str = "v888"
    description: str = "FlyWire gustatory and locomotion control subgraph"
    extraction_date: str = "2026-10-04"
    neuron_count: int = 0
    edge_count: int = 0
    synapse_threshold: int = 5
    is_mock: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset,
            "version": self.version,
            "description": self.description,
            "extraction_date": self.extraction_date,
            "neuron_count": self.neuron_count,
            "edge_count": self.edge_count,
            "synapse_threshold": self.synapse_threshold,
            "is_mock": self.is_mock,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CircuitManifest":
        return cls(
            dataset=d.get("dataset", "BANC"),
            version=d.get("version", "v888"),
            description=d.get("description", ""),
            extraction_date=d.get("extraction_date", ""),
            neuron_count=int(d.get("neuron_count", 0)),
            edge_count=int(d.get("edge_count", 0)),
            synapse_threshold=int(d.get("synapse_threshold", 5)),
            is_mock=bool(d.get("is_mock", False)),
        )


@dataclass
class Circuit:
    """Sparse biological circuit holding neuron identities and synaptic weights."""
    manifest: CircuitManifest
    # Neuron metadata
    neuron_labels: List[str]                  # Biological name / label
    root_ids: np.ndarray                      # FlyWire 64-bit root IDs (uint64)
    cell_types: List[str]                     # e.g., 'sensory', 'interneuron', 'descending', 'motor'
    functional_groups: List[str]              # e.g., 'sweet_grn', 'sez_fdg', 'dn_locomotion', 'mn_feeding'
    neurotransmitters: List[str]              # 'acetylcholine', 'gaba', 'glutamate'

    # Sparse edge list
    # source_idx -> target_idx with signed weight and delay
    source_indices: np.ndarray                # int32 array [E]
    target_indices: np.ndarray                # int32 array [E]
    synapse_counts: np.ndarray                # int32 array [E]
    weights: np.ndarray                       # float32 array [E] (signed mV)
    delays_ms: np.ndarray                     # float32 array [E]

    # Quick lookup indices
    _label_to_idx: Dict[str, int] = field(init=False, repr=False)
    _group_to_indices: Dict[str, List[int]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._label_to_idx = {label: i for i, label in enumerate(self.neuron_labels)}
        self._group_to_indices = {}
        for i, group in enumerate(self.functional_groups):
            self._group_to_indices.setdefault(group, []).append(i)

        # Enforce dtypes
        self.root_ids = np.asarray(self.root_ids, dtype=np.uint64)
        self.source_indices = np.asarray(self.source_indices, dtype=np.int32)
        self.target_indices = np.asarray(self.target_indices, dtype=np.int32)
        self.synapse_counts = np.asarray(self.synapse_counts, dtype=np.int32)
        self.weights = np.asarray(self.weights, dtype=np.float32)
        self.delays_ms = np.asarray(self.delays_ms, dtype=np.float32)

        self.manifest.neuron_count = len(self.neuron_labels)
        self.manifest.edge_count = len(self.source_indices)

    @property
    def num_neurons(self) -> int:
        return len(self.neuron_labels)

    @property
    def num_edges(self) -> int:
        return len(self.source_indices)

    def get_indices_by_group(self, group: str) -> List[int]:
        """Return neuron indices belonging to a functional group."""
        return self._group_to_indices.get(group, [])

    def get_index_by_label(self, label: str) -> Optional[int]:
        """Return neuron index for a biological label."""
        return self._label_to_idx.get(label)

    def get_sensory_indices(self) -> List[int]:
        """Return all sensory neuron indices."""
        return [i for i, ct in enumerate(self.cell_types) if ct == "sensory"]

    def get_motor_indices(self) -> List[int]:
        """Return all motor neuron indices."""
        return [i for i, ct in enumerate(self.cell_types) if ct == "motor"]

    def get_descending_indices(self) -> List[int]:
        """Return all descending neuron indices."""
        return [i for i, ct in enumerate(self.cell_types) if ct == "descending"]

    def save(self, output_dir: Path) -> None:
        """Save compact circuit artifact to disk."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save manifest
        with open(output_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(self.manifest.to_dict(), f, indent=2)

        # Save neurons metadata
        np.savez_compressed(
            output_dir / "neurons.npz",
            neuron_labels=np.array(self.neuron_labels, dtype=object),
            root_ids=self.root_ids,
            cell_types=np.array(self.cell_types, dtype=object),
            functional_groups=np.array(self.functional_groups, dtype=object),
            neurotransmitters=np.array(self.neurotransmitters, dtype=object),
        )

        # Save edges
        np.savez_compressed(
            output_dir / "edges.npz",
            source_indices=self.source_indices,
            target_indices=self.target_indices,
            synapse_counts=self.synapse_counts,
            weights=self.weights,
            delays_ms=self.delays_ms,
        )

    @classmethod
    def load(cls, circuit_dir: Path) -> "Circuit":
        """Load compact circuit artifact from disk."""
        circuit_dir = Path(circuit_dir)
        manifest_file = circuit_dir / "manifest.json"
        neurons_file = circuit_dir / "neurons.npz"
        edges_file = circuit_dir / "edges.npz"

        if not (manifest_file.exists() and neurons_file.exists() and edges_file.exists()):
            raise FileNotFoundError(f"Circuit artifact files missing in {circuit_dir}")

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_dict = json.load(f)
        manifest = CircuitManifest.from_dict(manifest_dict)

        neurons_data = np.load(neurons_file, allow_pickle=True)
        edges_data = np.load(edges_file, allow_pickle=True)

        return cls(
            manifest=manifest,
            neuron_labels=list(neurons_data["neuron_labels"]),
            root_ids=neurons_data["root_ids"],
            cell_types=list(neurons_data["cell_types"]),
            functional_groups=list(neurons_data["functional_groups"]),
            neurotransmitters=list(neurons_data["neurotransmitters"]),
            source_indices=edges_data["source_indices"],
            target_indices=edges_data["target_indices"],
            synapse_counts=edges_data["synapse_counts"],
            weights=edges_data["weights"],
            delays_ms=edges_data["delays_ms"],
        )

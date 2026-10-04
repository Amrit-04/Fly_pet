# Fly-Magotchi: Project Status & Initial Audit

**Date:** 2026-10-04  
**Audit Phase:** Phase 0 (Initial Repository Assessment)

---

## 1. Current State

The repository `/home/amritz/projects/Fly_pet` was initialized from an empty directory. No prior code, data, tests, or packaging files were present.

- **Existing code:** None (clean slate).
- **Existing FlyWire data:** None locally.
- **Python / Runtime environment:** Linux 7.0.0-34-generic, Python 3 environment. Target deployment is cross-platform with Windows desktop prioritized and Linux desktop support.
- **Git status:** Being initialized with proper `.gitignore` to avoid committing raw connectome data.

---

## 2. Scientific & Architectural Plan

### Scientific Foundation
- **Connectome Dataset:** FlyWire / FAFB v783 and BANC (Female Adult Brain + Nerve Cord) v888.
- **Biological Circuit Target:** Gustatory / Feeding / Locomotion circuit:
  - **Sensory:** Sugar-sensitive gustatory receptor neurons (GRNs, e.g., labellar / tarsal Gr5a/Gr64f sweet GRNs).
  - **Interneurons / Central Processing:** Subesophageal zone (SEZ) feeding interneurons (e.g., Fdg - Feeding De-inhibitory Gustatory interneurons, IN1, CLEARED/CLAMP, PAM dopaminergic pathways), descending locomotion-modulating neurons (DNs like DNp01/MDN/DNa01/DNa02).
  - **Motor Output:** Proboscis extension / pumping motor neurons (e.g., MN9 / feeding motor units) and locomotion control (forward walking command vs. pause/feeding arrest).
- **LIF Reference Parameters (Shiu et al. Nature 2024 / Phil Shiu Drosophila Brain Model):**
  - $V_{\text{rest}} = -52\text{ mV}$
  - $V_{\text{reset}} = -52\text{ mV}$
  - $V_{\text{threshold}} = -45\text{ mV}$
  - $\tau_{\text{membrane}} = 20\text{ ms}$
  - $\tau_{\text{synapse}} = 5\text{ ms}$
  - $t_{\text{refractory}} = 2.2\text{ ms}$
  - $t_{\text{delay}} = 1.8\text{ ms}$
  - $W_{\text{syn}} = 0.275\text{ mV}$ per signed anatomical synapse

### Scientific Truth & Behavior Architecture
- Biological reality: Sugar stimulation activates sweet GRNs and SEZ interneurons, triggering proboscis extension (feeding motor program) while *inhibiting* forward locomotion (stopping to feed).
- Locomotion / Foraging: Wandering/exploration is driven by central walking pattern generator / spontaneous activity; approaching sugar is mediated by sensory gradient decoding; arriving at sugar triggers feeding and halts forward locomotion.
- Connectome vs. Application logic distinction:
  - Connectome: Exact FlyWire neuron IDs, synapse counts, signed neurotransmitter weights, LIF membrane potential and spike dynamics.
  - Behavior Decoder: Translates population firing rates into motor behaviors (Wander, Approach, Stop, Feed).

---

## 3. Known Problems & Challenges to Address
1. **Connectome Data Availability:** Need authentic FlyWire root IDs, synapse counts, and connectivity matrices for the gustatory-locomotion axis without requiring a live CAVEclient or network connection at runtime. We will generate reproducible extraction scripts and package a validated compact biological artifact (`data/circuit/`).
2. **Numerical Precision & Performance:** LIF integration with delays requires efficient ring-buffer / sparse matrix updates in NumPy ($dt = 0.1\text{ ms}$) running decoupled from PyQt6 GUI (~30-60 FPS).
3. **Cross-Platform Transparent Overlay:** Windows and Linux desktop transparency flags (`WA_TranslucentBackground`, `WindowStaysOnTopHint`, `FramelessWindowHint`, `WindowTransparentForInput`) require a clean platform adapter.

---

## 4. Execution Order (Phased Delivery)

1. **Phase 1 & 2: Data Provenance & Biological Circuit Discovery**
   - Create `DATA_SOURCES.md`, `CITATIONS.md`, `.gitignore`, `pyproject.toml`, `requirements.txt`.
   - Formulate exact FlyWire neurons, annotations, root IDs, synapse counts, and neurotransmitters.
2. **Phase 3: Circuit Extraction & Compact Artifact**
   - Create compact sparse circuit format (`neurons.npz`, `edges.npz`, `manifest.json`).
   - Provide build tool `tools/build_circuit.py` and validator `tools/validate_circuit.py`.
3. **Phase 4: Reference LIF Engine**
   - Implement `flymagotchi/brain/reference_lif.py` with analytical test cases.
4. **Phase 5: Optimized LIF Engine**
   - Implement vectorized NumPy engine `flymagotchi/brain/lif.py` supporting delays, refractoriness, synaptic decay, and sparse weights.
   - Benchmark and verify against reference implementation.
5. **Phase 6: Neural Experiments & Controls**
   - Non-GUI experiments (`experiments/sugar.py`, `experiments/controls.py`).
   - Ablation / shuffled connectome controls verifying biological specificity.
6. **Phase 7: Behavioral Decoder & Sensory Model**
   - Population rate decoders (`flymagotchi/brain/decoder.py`).
   - Poisson sensory stimulation for sugar proximity.
7. **Phase 8 & 9: UI & Desktop Overlay**
   - Platform-aware PyQt6 transparent window (`flymagotchi/ui/overlay.py`, `flymagotchi/ui/fly.py`, `flymagotchi/ui/sugar.py`).
   - Interactive draggable sugar cube, animated pixel fly.
   - Simulation controller (`flymagotchi/simulation/controller.py`) decoupling UI and neural timesteps.
8. **Phase 10: Performance Optimization & Benchmarks**
   - Benchmark script reporting real-time factor, dt, peak memory.
9. **Phase 11: Test Suite & Hardening**
   - Comprehensive pytest suite covering LIF, circuit loading, decoder, numerical validation, UI mocks.
10. **Phase 12, 13 & 14: Packaging, Documentation & Audit**
    - PyInstaller specification, complete `README.md`, final release audit.

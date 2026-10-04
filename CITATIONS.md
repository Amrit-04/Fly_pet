# CITATIONS

## Primary Computational Neurobiology & Drosophila Connectome References

1. **Shiu, P. K., et al.** (2024). *A Drosophila computational brain model reveals sensorimotor processing.* **Nature**, 634, 210–219. [https://doi.org/10.1038/s41586-024-07763-9](https://doi.org/10.1038/s41586-024-07763-9)
   - Primary reference for the Leaky Integrate-and-Fire (LIF) parameters:
     - Resting potential: $V_{\text{rest}} = -52\text{ mV}$
     - Reset potential: $V_{\text{reset}} = -52\text{ mV}$
     - Firing threshold: $V_{\text{th}} = -45\text{ mV}$
     - Membrane time constant: $\tau_m = 20\text{ ms}$
     - Synaptic decay time constant: $\tau_s = 5\text{ ms}$
     - Refractory period: $t_{\text{ref}} = 2.2\text{ ms}$
     - Axonal / synaptic delay: $t_{\text{delay}} = 1.8\text{ ms}$
     - Synaptic unitary weight: $W_{\text{syn}} = 0.275\text{ mV}$ per anatomical synapse count
     - Neurotransmitter assignment: Acetylcholine (ACh) is excitatory (+1); GABA is inhibitory (-1); Glutamate (Glu) in Drosophila CNS is predominantly inhibitory (-1 via GluCl$\alpha$ channels).

2. **Dorkenwald, S., et al. (FlyWire Consortium)** (2024). *Neuronal wiring diagram of an adult brain.* **Nature**, 634, 124–138. [https://doi.org/10.1038/s41586-024-07558-9](https://doi.org/10.1038/s41586-024-07558-9)
   - Whole-brain connectome release (FAFB v783 / FlyWire) providing complete connectivity and neurotransmitter predictions.

3. **Schlegel, P., et al.** (2024). *Whole-brain annotation and multi-connectome cell typing of Drosophila.* **Nature**, 634, 139–152. [https://doi.org/10.1038/s41586-024-07686-5](https://doi.org/10.1038/s41586-024-07686-5)
   - Systematic cell type nomenclature, hierarchical grouping, and neurotransmitter classifications across FlyWire.

4. **FlyWire BANC Consortium** (2024–2026). *Brain and Nerve Cord (BANC) Connectome.*
   - Dataset snapshot: v888. Unified connectome spanning brain and ventral nerve cord (VNC), detailing descending neurons (DNs) and motor neurons (MNs).

5. **Miroschnikow, A., et al.** (2020 / 2026). *Organization of gustatory and feeding circuits in Drosophila.* **Cell** & **Current Biology**.
   - Subesophageal zone (SEZ) gustatory processing: Sweet gustatory receptor neurons (GRNs) expressing Gr5a/Gr64f activate Feeding De-inhibitory Gustatory (Fdg) neurons and Ingestion Neuron 1 (IN1).
   - Motor program: Proboscis Extension Response (PER) mediated by rostrum protractor motor neuron (MN9) and haustellum extensor motor neuron (MN11).
   - Locomotor suppression: Sugar detection suppresses forward locomotion (via descending inhibitory pathways / stop neurons such as MDN or DNp01 arrest) to facilitate ingestion.

6. **Bidaye, S. S., et al.** (2014 / 2020). *Two brain pathways initiate and coordinate backward and forward walking in Drosophila.* **Science**, 344(6179), 97–101.
   - Characterization of Moonwalker Descending Neurons (MDN) and descending neurons regulating forward walking (DNa01, DNa02).

# Novelty comparison matrix (evidence level stated for every cell)

Evidence codes: **FT** = read in full or in part (full text, preprint or accepted manuscript); **AB** = abstract or abstract fragment only; **MD** = bibliographic record only.
Cell codes: **N\*** = not found in the text read (FT only; partial reads cannot prove absence); **NS** = not stated in the abstract (AB; says nothing about the paper body); **Y** = present; **P** = present in a different form (stated in the note); **?** = unknown.
Our study: (a) route-scored client selection (top-k / coverage-aware / uniform) measured for PDR, delay **and** participation fairness; (b) packet-level update delivery (independent draw vs packet-coupled with retransmissions); (c) median-based surrogate imputation of missing updates; (d) median/MAD filter + server momentum vs sign-flip; (e) participation-fairness metric (Gini, never-selected); (f) Gaussian noise with diagnostic (not certified) ε; (g) pre-registered negative results / filter behaviour vs number of genuine updates.
Sources: `literature/group{A,B}_report.md` (Phase 9B) and `literature/group{1,2,3}_fulltext_report.md` (Phase 9C). Quotes in those reports passed through a fetch tool that returns digests; spot-check against the PDFs before quoting.

| Source | Evid. | (a) route/network-aware selection | (b) packet-level delivery | (c) imputation of missing updates | (d) median/MAD or robust agg. | (e) fairness metric | (f) DP | (g) neg. results / sparse-update study | Closeness | Distinction |
|---|---|---|---|---|---|---|---|---|---|---|
| latif2026multimodel | FT (77%) | N* (static client-to-edge, local-loss model choice) | N* | N* | P (cosine-distance clustering; Krum/TM only baselines) | N* | N* | N* | MEDIUM | 50 clients and filtering, but no delivery/selection modelling |
| almeida2025modular | FT | N* | N* | N* | ? | N* | ? | N* | MEDIUM | same dataset (UNSW-NB15), benign worker failures; no delivery model |
| mughal2024adaptive | FT | P (static network-quality node selection) | N* | N* | N* | N* | N* | N* | LOW-MED | selection without delivery model or fairness |
| alanazi2026edgeguard | FT | P (task scheduling onto nodes; random client sampling) | N* | N* | N* (Byzantine-resilient aggregation = future work) | N* | N* | N* | LOW-MED | scheduling, not route-scored selection |
| zhang2026adaptive | FT | N* (FL trains a routing predictor, all nodes participate) | N* | N* | N* | N* | N* | N* | LOW | FL *for* routing, opposite dependence |
| soomro2026securedyn | FT (57%) | N* | N* | N* | P (GMM/Mahalanobis auditing, unnamed robust function) | N* | N* | N* | LOW | 20 clients, all participate |
| peng2025fdids | FT (40%) | N* | N* | N* (missing rows deleted) | N* (FedAvg/FedProx) | P (best/worst client accuracy; no formal metric) | N* | N* | LOW | KD under non-IID |
| rahmati2025cybersecurity | FT (arXiv v1 only) | N* | N* (HE latency only) | N* | N* | N* | P (Gaussian DP noise in preprint; guarantee not verified) | N* | LOW | Byzantine = future work |
| albogami2025deepfl | FT (64%) | N* (random subset) | N* | N* | N* | N* | N* | N* | LOW | generic FL edge security |
| zhu2026bpflh | FT (accepted ms., keyword-searched) | N* | N* | N* | P (Bray-Curtis filtering; Median/Trimmed-Median/Krum baselines) | N* | N* (HE) | N* | LOW | non-IID Byzantine filter |
| liu2024iiot | FT | N* | N* | N* | N* | N* | N* | N* | LOW | edge-FL framework |
| haripriya2025fault | AB | NS | NS | NS | NS | NS | NS | NS | LOW-MED | fault tolerance + latency via edge servers |
| chen2025hierarchical | AB | NS | NS | NS | NS ("paralysis ratio" robustness) | NS | NS | NS | LOW-MED | hierarchical multicenter fault tolerance |
| shah2026trisafe | AB | NS | NS | NS | P (Byzantine attacks on IDS data) | NS | P (DP + secure aggregation) | NS | LOW-MED | overlaps elements (d), (f) in kind, not mechanism |
| s2dfl2026 | AB | NS | NS | NS | P (statistical filtering + reputation) | NS | P (local DP; ε=5.0 example; certification not checked) | NS | MEDIUM | new algorithm, not a measurement study |
| abdallah2026routing | AB (verbatim abstract) | NS | NS | NS | NS | NS | NS | NS | LOW-MED | FL used to learn routing |
| bhardwaj2024routing | AB | NS | NS | NS | NS | NS | NS | NS | LOW-MED | FL for routing optimisation |
| liu2026reliability | AB (fragment) | NS | NS | NS | NS | NS | NS | NS | LOW-MED | "reliability" = edge-node trust vs collusion/poisoning |
| tang2026fedcst | AB (fragment) | NS | NS | NS | NS | NS | NS | NS | LOW | clustered IIoT data |
| albanbay2025ids | AB | NS | NS | NS | NS | NS | NS | NS | LOW-MED | same dataset (CICIoT2023), up to 150 simulated devices |
| alghadi2025dos | AB | NS | NS | NS | NS | NS | NS | NS | LOW | IoTID20, feature selection |
| zhang2026malicious | AB | NS | NS | NS | P (cosine + Shapley aggregation) | NS | NS | NS | LOW | non-IID Byzantine aggregation |
| liu2026anonymous | AB | NS | NS | NS | P (limits malicious influence) | NS | NS | NS | LOW | anonymity + secure aggregation |
| shu2026trustworthy | AB | NS | NS | NS | P (Median/Multi-Krum under 2PC) | NS | NS | NS | LOW-MED | secure-computation robust rules |
| aburukba2025scheduling | AB | NS | NS | NS | NS | NS | NS | NS | LOW | fault-aware VM scheduling (fault tolerance of the scheduler) |
| zhou2024qos | AB | NS | NS | NS | NS | NS | NS | NS | LOW | edge-cloud FL for QoS |
| geng2024smpc | AB | NS | NS | NS | NS | NS | P (SMPC + blockchain, no DP) | NS | LOW | SMPC privacy |
| lan2025ckks | AB (digest only) | NS | NS | NS | NS | NS | P (CKKS homomorphic encryption) | NS | LOW | HE privacy |
Dropped from the bibliography in Phase 9C (not needed or not supportable): carillo2026incremental, zhang2026endpca, wang2026desa, wang2024trust, bayat2025qlearning, padmavathi2025trust, li2023privacy (metadata-only, mask/noise mechanism unverified), cho2020clientselection (superseded by cho2022biased).

## Verdict
* **No source examined contradicts the gap statement**, but only 14 of 35 were read beyond the abstract and none of the abstract-level sources can be said to *lack* a feature. The statement stays scoped ("within the sources examined"; no priority claim; no systematic search).
* **Closest neighbours**: almeida2025modular and latif2026multimodel (read in part), s2dfl2026 and shah2026trisafe (abstract level; overlap in robustness/privacy in kind).
* **What is distinguishable**: the *joint* measurement of delivery reliability and participation fairness under route-scored selection, single-factor effects of the delivery model / imputation / weighting / momentum, filter behaviour versus the number of genuine updates, and a pre-registered negative guard result, all under one hash-locked protocol. **Not** distinguishable as novel: median/MAD filtering, server momentum, Gaussian perturbation, top-k selection, imputation by median.

# Abstract-level references: which manuscript statements need more than the abstract? (Phase 9D)

Scope: the 17 application-level references cited from `sections/related_work.tex` that were read at abstract (or fragment) level only. No further publisher downloads were attempted. Rule applied: a statement may stay only if the abstract (or other accessible verified evidence) supports it; otherwise it is rewritten as an explicit "(abstract level)" observation or removed. No statement asserts that an unobserved mechanism is **absent** from an original paper. The 44-entry bibliography is unchanged by this audit.

| # | Source (access) | Manuscript statement (current text) | Needs more than the abstract? | Decision |
|---|---|---|---|---|
| 1 | albanbay2025ids (abstract) | cited with alghadi among "studies apply FL to IoT intrusion detection"; "their abstracts describe a model and data-scale study and a feature-selection and model comparison and mention neither a delivery model nor a selection policy" | The first clause no. The second only reports what the abstracts contain | **Kept**, explicitly worded as an abstract observation |
| 2 | alghadi2025dos (abstract) | same | same | **Kept** (same wording) |
| 3 | zhang2026malicious (abstract) | "Byzantine-robust schemes address heterogeneous data (the first at abstract level)" | No: "heterogeneous data" is in the abstract | **Kept**, tagged |
| 4 | liu2026anonymous (abstract) | "combine robustness with secure aggregation or secure two-party computation (abstract level)" | No | **Kept**, tagged; digest figures ("50% fog nodes", ">20% efficiency") not used |
| 5 | shu2026trustworthy (abstract) | same sentence; later: Byzantine attacks on IDS data with DP and secure aggregation reported in `shah2026trisafe` | `shu`: robust rules under secure two-party computation is in the abstract; no more is claimed | **Kept**, tagged |
| 6 | s2dfl2026 (abstract) | "pairing local-DP noise with statistical filtering and client reputation (abstract level)" | No; privacy certification is **not** asserted either way | **Kept**, tagged |
| 7 | chen2025hierarchical (abstract) | "hierarchical multicenter FL with fault-tolerance mechanisms … (abstract level)" | No | **Kept**, tagged |
| 8 | haripriya2025fault (abstract) | "FL with edge servers and a pre-trained model for fault tolerance and latency … (abstract level)" | No | **Kept**, tagged |
| 9 | aburukba2025scheduling (abstract) | "FL-trained regression models for fault-aware scheduling of IoT requests onto virtual machines … fault tolerance concerns the scheduler, not FL training (abstract level)" | The qualifier is an interpretation of the abstract | **Kept**; wording follows the abstract (fault-aware scheduling, fault prediction) |
| 10 | liu2026reliability (fragment) | "multi-server secure FL with configurable edge-node reliability against collusion and poisoning (abstract fragments only)" | Yes in principle (only a paraphrase was seen) | **Kept as hedged observation**; not used for any comparison |
| 11 | tang2026fedcst (fragment) | "FL under clustered data in a three-tier IIoT architecture (abstract fragments only)" | same | **Kept as hedged observation** |
| 12 | abdallah2026routing (verbatim abstract) | "FL has been used to learn routing policies (… the first and third at abstract level)"; "whether and how these studies model the delivery of the FL updates themselves is not stated in the parts we read" | The earlier sentence "the dependence runs from the network to the learner's output" implied knowledge of the paper body | **Rewritten** (Phase 9D) as the explicit "not stated in the parts we read" |
| 13 | bhardwaj2024routing (abstract) | same as #12 | same | **Rewritten** (same) |
| 14 | zhou2024qos (abstract) | "edge–cloud and resource-aware FL architectures target quality of service and resource constraints (the first at abstract level)" | No | **Kept**, tagged (Phase 9D) |
| 15 | geng2024smpc (abstract) | "secure multi-party computation (with a blockchain in …) (abstract level)" | No | **Kept**, tagged |
| 16 | lan2025ckks (digest only) | "homomorphic encryption (the last two at abstract level)" | Yes: only a search-tool digest was available | **Kept as the minimal topic statement** (HE as a privacy layer, taken from the title); no internals claimed |
| 17 | shah2026trisafe (abstract) | "report Byzantine attacks on IDS data together with DP and secure aggregation (abstract level) and therefore overlap with our robustness and privacy elements in kind, though not in mechanism" | "Not in mechanism" is a statement about the body | **Rewritten** (Phase 9D): "overlap … in kind; whether the mechanisms differ cannot be judged from the abstract" |

Gap statement: restated as "Within the sources examined (11 read in full or in part, 17 at abstract level) we did not find …", with "absence from an abstract is not proof of absence from the paper" and "no systematic literature search". The novelty matrix (`Phase9C_Submission_Readiness/NOVELTY_COMPARISON_MATRIX.md`) uses **NS** (not stated in the abstract) for these 17, never "absent".

Claims explicitly **not made**: that any abstract-level source lacks delivery modelling, selection policy, imputation, fairness metrics or negative results; that any of them is exhausted by what its abstract says; priority or exhaustive coverage.

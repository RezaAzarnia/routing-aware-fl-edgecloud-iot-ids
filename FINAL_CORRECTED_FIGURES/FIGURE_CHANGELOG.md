# FIGURE_CHANGELOG — Figure 1 and Figure 3 corrections (2026-11-08)

The originals were **not** changed. Everything here is new and lives in `FINAL_CORRECTED_FIGURES/`.
No experiment was rerun, and no result, manifest, table or manuscript text was modified. Nothing was committed or pushed.

| File | Purpose |
| --- | --- |
| `fig1.png` | Corrected Figure 1 (3344 × 2014 px, 2× the original grid) — drop-in for `images/fig1.png` |
| `make_fig1_corrections.py` | Reproducible source of every Figure 1 edit (see “Why no fig1.svg”) |
| `fig1_BEFORE_AFTER.png` | Original (top) vs corrected (bottom) |
| `fig3.pdf` | Corrected Figure 3, vector (fonts embedded as TrueType) |
| `fig3.png` | Corrected Figure 3, 400 dpi — drop-in for `images/fig3.png` |
| `make_fig3_attack_robustness.py` | Corrected plotting script (derived from `scripts/supp_final/figures_final.py`, panel F1) |
| `fig3_data.csv` | The 240 plotted values with dataset, metric, arm, seed, run_id, source |
| `fig3_BEFORE_AFTER.png` | Figure 3 as in the submitted `main.pdf` (left) vs corrected (right) |

---

## 1. Figure 1 — implementation checks

The following were checked against the code before editing:

| Claim in the figure | Code evidence |
| --- | --- |
| Reference pipeline: surrogates first, then MAD over real + imputed updates | `src_v2/experiment.py` round loop: with `surrogate_handling: reference` (as in every `atk_ref_*` and `reference` config), `recover_failed_update` appends surrogates to `updates`, then `_safe_aggregate(updates, …)` runs `distance_filter` on the combined list. `post_filter_real_only` is the opposite-order control. |
| Surrogate needs ≥ 2 real updates | `experiment.py`: `len(updates) >= 2`; `src/recovery.py` raises if fewer than 2. Surrogate = `coordinate_median` of the received real updates. |
| MAD rule | `src/aggregation.py::distance_filter_indices`: coordinate-median centre, L2 distances, threshold = median + k·(1.4826·MAD + 1e-12), argmin fallback. |
| Clipping and cap only in the central-Gaussian branch | `experiment.py`: `clip_update` and `capped_normalized_weights` are called only when `privacy.mode == "central_client"`. The non-private branch uses the filter's sample-size-weighted mean of retained, unclipped updates. |
| a_i = 1/|K_t| for 1–10 retained updates | `src/privacy.py::capped_normalized_weights`: cap = max(0.1, 1/n). For n ≤ 10, every weight is ≤ 1/n and the weights sum to 1, so all weights equal exactly 1/n whenever the raw-weight sum is positive. |
| No valid positive-weight contribution → skip | `experiment.py`: `no_valid_contribution` → aggregate = None, no noise, `server.apply_update` not called, so w and v are unchanged. A round with no received update skips the aggregation block entirely. |
| Noise scale | `experiment.py`: std = σ_DP · C · max a_i · φ, i.e. z ~ N(0, σ_DP² (Δ₂^(t))² I) with Δ₂ = φ C max a_i (Eq. 10–11). |
| Momentum | `src/server.py::apply_update`: v ← μ v + ũ, w ← w + η_s v. |
| Path score | `routing.alpha_latency / beta_stability / gamma_security = 0.4 / 0.3 / 0.3` in the resolved configs (Eq. 1, Table 3). |

## 2. Figure 1 — changes (item numbers match comments in `make_fig1_corrections.py`)

| # | Location | Before | After |
| --- | --- | --- | --- |
| F1-01 | Stage 1, path score | S_i = α·1/d_i + β·s_i + γ·κ_i ; α+β+γ=1 | R_{i,p} = λ_L L̂_{i,p} + λ_S Ŝ_{i,p} + λ_Q Q̂_{i,p} ; λ_L+λ_S+λ_Q = 1 (0.4/0.3/0.3) |
| F1-02 | Stage 1, indicator symbols | d_i, s_i, κ_i | L̂_{i,p}, Ŝ_{i,p}, Q̂_{i,p} |
| F1-03 | Stage 1, Client Availability | a_i | (symbol removed; a_i is the aggregation weight) |
| F1-04 | Top-right arrow | Client Updates Return {ũ_i^(t)} | Client Updates Return {Δw_i^(t)} |
| F1-05 | Stage 2 | Model Updates (Parameters / Gradients) | Model Updates (model differences Δw_i^(t)) |
| F1-06 | Stage 3 header | Failure Recovery & Robust Update Filtering (Server) | Surrogate Imputation & Robust Update Filtering (Server) |
| F1-07 | **Stage 3 order** | Received → Failure detection → Robust filtering (MAD) → Surrogate | Received → Failure detection → **Surrogate imputation → Robust filtering (MAD)** (original boxes, icons and arrows moved) |
| F1-08 | Surrogate box | “Surrogate Recovery” / “Coordinate-wise median imputation for missing updates” | “Surrogate Imputation” / “Coordinate-wise median surrogate for missing updates (when at least two real updates are available)” (decorative squares icon removed to fit the text) |
| F1-09 | MAD box body | Filter outlier real updates around a robust center | Filter outliers among real and imputed updates |
| F1-10 | Stage 4 header | Privacy-Aware Aggregation & Global Model Update (Server) | Server-Side Aggregation & Global Model Update |
| F1-11 | Clipping box | — | “Gaussian branch” tag (same style as the existing “Optional” tag) |
| F1-12 | Aggregation box | Capped Weighted Aggregation ; ũ^(t) = Σ a_i·clip(Δw_i^(t)) | Capped Aggregation (central-Gaussian branch) ; u^(t) = Σ_{i∈K_t} a_i Δw̄_i^(t), a_i = 1/|K_t| |
| F1-13 | Gaussian box | ũ = ũ + z, z ~ N(0, σ²_DP I) | ũ^(t) = u^(t) + z^(t), z^(t) ~ N(0, σ²_DP (Δ₂^(t))² I) |
| F1-14 | Legend, Model Update | Parameters / gradients | Model differences Δw |
| F1-15 | Legend, Security & Privacy | Server-side clipping + optional differential privacy | Clipping + optional Gaussian perturbation |
| F1-16 | Banner | …robust filtering, failure recovery, and server-side privacy to enable resilient… | …surrogate imputation, robust filtering, and optional server-side Gaussian perturbation for federated intrusion detection. |
| F1-17 | **New bottom row** | — | Central-Gaussian branch (optional): clipping → capped weights (a_i = 1/|K_t| when 1–10 updates are retained) → Gaussian noise; ε̂ is an accounting diagnostic, not certified DP. Non-private reference: sample-size-weighted mean of retained, unclipped updates (no clipping, cap or noise; ũ = u). No valid positive-weight update: aggregation skipped; w and v unchanged; no noise. |

### Why no `fig1.svg`

The repository has no vector or editable source for Figure 1. Only the 1672 × 941 raster exists, in `manuscript/images/` and in `main paper/images/`. An SVG built around that raster would not be a real vector file, and redrawing the whole figure as vector was ruled out by the brief.

The editable source delivered instead is `make_fig1_corrections.py`. It rebuilds `fig1.png` from the original in one step, and every label is a plain string in the script. Equations are typeset with matplotlib mathtext (STIX).

## 3. Figure 3 — verification and changes

**Data source:** `Supplementary_Experiments_Package/SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv`. The arm/condition mapping is the same as in `scripts/supp_final/figures_final.py`.

**Integrity check (built into the script):** all 240 plotted values (2 datasets × 2 metrics × 2 pipelines × 6 conditions × 5 seeds) are compared with the previously published `figures/FIG1_attack_robustness_data.csv`. The values, run IDs, conditions and seeds are identical, and the script aborts on any difference.

**Configuration checks** (`resolved_config.yaml`, seed 12):
- The `atk_fedavg_*` and `atk_ref_*` configs differ only in `aggregation.method` (fedavg vs distance_filter) and `failure.recovery_enabled` (false vs true).
- Both use `selection_policy: top_k`, routing enabled, `path_policy: default` and `privacy.mode: none`.
- The requested legend texts therefore match the code.

**Changes:**
- New legend labels: “FedAvg (top-k/routed; no filtering or imputation)” and “Non-private MAD + median imputation (top-k/routed)”, plus a “Mean of 5 seeds (12–16)” key.
- The shared legend sits outside and above the panels.
- Methods are distinguished by colour and by shape (circles = FedAvg, squares = MAD + imputation).
- Fixed y-limits: selected checkpoint 0.50–1.00 and last round 0.20–1.00. The script asserts that every point lies inside them; the lowest values are 0.5758 and 0.2076.
- Points at the axis limits are not clipped.
- Light separators between attack conditions.
- Footnote: “Non-adaptive attacks on the non-private reference pipeline; not a direct test of the Gaussian-perturbed configuration.” It also defines SF/BSF/LF and states the SF 20% provenance.
- Size: 7.2 × 5.6 in. Base font 9 pt, which stays at about 8.4 pt or more at the manuscript width of 0.93\textwidth.

All 6 conditions, both datasets, both evaluation points, all seeds and all means are kept.

## 4. Discrepancies found (reported, not corrected in the manuscript)

1. **The repository's `manuscript/` folder is an older version.** In `manuscript/main.tex` (repo), `fig3.png` is a participation/routing bar chart. In the manuscript you submitted (`main.tex`/`main.pdf` with Figure 3 = attack robustness), `fig3.png` is the attack-robustness plot. The corrected `fig3.png` is meant for the submitted manuscript. **Do not copy it over `manuscript/images/fig3.png` in the repo**, because that file is a different figure.
2. **SF 20% points come from different runs.** They are the locked Phase 6C runs (`reference`, `scenario_fedavg_topk`), not SUPP_V1 runs. The setting is the same (top-k, routed, non-private, 20% sign-flip exposure), which is why the original script used them too. This is now stated in the figure footnote.
3. **Figure 1 caption is now out of date.** It currently reads: “Stage 3 illustrates the real-only filtering variant, in which MAD filtering precedes surrogate recovery; the original reference configuration reverses this order.” Proposed replacement (not applied): *“Stage 3 shows the reference implementation: median surrogates are built from the received real updates and MAD filtering is applied to real and imputed updates; the real-only post-filter control reverses this order. Stage 4 clipping, capping and noise apply only to the central-Gaussian branch.”*
4. **Zero-raw-weight surrogates still receive weight.** In the Gaussian branch with a positive raw-weight sum, `capped_normalized_weights` gives every retained update, including a zero-raw-weight surrogate, exactly 1/|K_t|. The manuscript sentence “no zero-weight surrogate gains positive weight” is correct only for the zero-sum (abstention) case. Figure 1 states the implemented behaviour.
5. **Using the vector version of Figure 3.** `main.tex` includes `fig3.png`, so the PNG is the drop-in file. To use the vector version, change `\includegraphics{fig3.png}` to `fig3.pdf`.

## 5. Final checks performed

- Figure 1 was viewed at full size and at print width (≈ 6.9 in); all labels and equations are legible.
- In Figure 1, the moved boxes have clean edges, no leftover arrow pieces, and backgrounds sampled from the original box interiors.
- Neither figure has a legend, title, arrow or label overlapping another element.
- `fig3.pdf` fonts are embedded (pdffonts: DejaVuSans / DejaVuSans-Bold, CID TrueType, embedded).

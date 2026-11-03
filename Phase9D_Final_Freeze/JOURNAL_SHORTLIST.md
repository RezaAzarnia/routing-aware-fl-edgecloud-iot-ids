# Journal shortlist (candidates only; no choice is made on the authors' behalf, no acceptance is implied)

Basis: the *actual* contribution is a **reproducible simulation-measurement study** (delivery reliability vs participation fairness, single-factor ablations, MAD behaviour vs sparse updates, pre-registered negative result, hash-locked protocol) with validation-only evidence. It is not a new algorithm and, unless the final test is run, makes no test-set or deployment claim. Evidence of topical fit below = the venue appears in our verified bibliography (a venue that already publishes comparable FL-for-IoT/edge work). Impact factors, quartiles, scope statements, article-processing charges and current policies were **not** checked here (no verified source in this session): the authors must confirm each on the journal's own site before choosing.

| Tier | Candidate | Why it could fit | Evidence it publishes related work (bibliography key) | Risk / caution |
|---|---|---|---|---|
| A: network-systems measurement | Computer Networks (Elsevier) | simulation + network model + FL; measurement/negative results are in scope for network studies | `tang2026fedcst`, `liu2026reliability` | reviewers may want testbed or real traces |
| A | Ad Hoc Networks (Elsevier) | edge/IoT networking with FL | `zhou2024qos` | same |
| A | IEEE Transactions on Network and Service Management | FL-IDS and network management | `soomro2026securedyn` | strong-algorithm bias; a measurement-only paper needs a clear reliability/operations angle |
| A | Future Generation Computer Systems (Elsevier) | edge–cloud systems; was the macro `\journal{}` of the earlier manuscript source (not confirmed as the authors' intent) | (no bibliography entry after Phase 9C) | scope on "novel system" may disfavour a measurement study |
| A | Internet of Things (Elsevier) | IoT FL and privacy | `lan2025ckks` | |
| B: open-access, broad scope | Sensors (MDPI) | many cited FL-IoT-IDS papers | `latif2026multimodel`, `peng2025fdids`, `almeida2025modular`, `alanazi2026edgeguard`, `liu2024iiot` | quality/selectivity varies; check APC |
| B | Journal of Sensor and Actuator Networks (MDPI) | IoT IDS | `albanbay2025ids` | |
| B | IEEE Access | broad, accepts reproducibility/negative-result style work | `haripriya2025fault`, `shah2026trisafe` | check APC and review depth |
| B | Scientific Reports | multi-disciplinary FL-edge papers | `mughal2024adaptive`, `zhang2026adaptive` | expects strong statistical reporting |
| C: security-focused | Cyber Security and Applications (Elsevier) | IDS/security | `alghadi2025dos` | expects security novelty |
| C | IEEE Internet of Things Journal | IoT FL robustness | `shu2026trustworthy` | high bar for algorithmic novelty; simulation-only and no final test would be a weak fit |
Not on the list unless the authors add evidence: venues requiring a deployed testbed, real traffic, or a formal privacy/robustness guarantee.

## Fit by decision
* If the **final test is run** and reported: Tier A and security-focused venues become more realistic; the "measurement + negative results" framing remains the core.
* If **validation-only**: prefer venues that accept measurement/reproducibility contributions (Tier A/B), state the limitation in the title or abstract framing, and expect reviewers to ask for test-set evidence.
Journals' author guidelines may also require: structured abstract, highlights, graphical abstract, data/code availability statement, CRediT, declaration of generative-AI use, suggested reviewers (see `AUTHOR_INFORMATION_REQUIRED.md`).

# Group A literature review (14 entries)

Method note. Access was limited: MDPI, ScienceDirect, IEEE Xplore, PMC web pages and the Palermo repository returned 403/blocked/empty. Full text was obtained only via (i) Europe PMC full-text XML (Latif, Peng, Albogami; the tool read the first 100,000 characters of each, so late sections such as conclusions were not read), (ii) arXiv HTML/PDF (Soomro preprint, first 100,000 of 175,068 characters; Rahmati arXiv v1, extracted with PyMuPDF and keyword-searched, not read end to end), (iii) the University of Greenwich author accepted manuscript of BPFLH (PDF text extracted with PyMuPDF; keyword-searched plus targeted reading of the threat model and experimental setup, not read end to end). Everything marked ABSTRACT_ONLY rests on abstracts reconstructed from OpenAlex or repository pages. Metadata for all IEEE items was checked against Crossref records only (IEEE landing pages could not be read). Findings from partly read full texts are limited to what was seen ("not found in the text read" is not proof of absence).

Scope caveat: related_work.tex cites only 10 of the 14 keys. NOT cited in related_work.tex: carillo2026incremental, zhang2026endpca, s2dfl2026, albogami2025deepfl (they may be cited elsewhere in the manuscript; I did not check other files).

## Summary table

| Key | Access | Source used | Metadata matches bib? | Route-aware selection | Packet delivery model | Imputation of missing updates | Median/MAD or robust agg. | Participation fairness | DP (certified?) | Closeness |
|---|---|---|---|---|---|---|---|---|---|---|
| soomro2026securedyn | FULL_TEXT (arXiv preprint v1, ~57% read; journal version not read) | arxiv.org/html/2601.06466v1; Crossref | Yes (TNSM 23, 1742-1765) | No (20 clients, all appear to participate) | No | No | GMM/Mahalanobis auditing; "robust aggregation function" unnamed | No | No; contrasts itself with DP | LOW |
| carillo2026incremental | ABSTRACT_ONLY | OpenAlex abstract; Crossref | Yes (early access, no vol/pages, as in bib note) | not stated | not stated | not stated | not stated | not stated | not stated | LOW (provisional) |
| latif2026multimodel | FULL_TEXT (Europe PMC XML, ~77% read) | europepmc REST fullTextXML PMC13210706 | Yes (Sensors 26(10) 3198) | No (static client-to-edge assignment; clients choose models by local loss) | No | No | Cosine-distance hierarchical clustering with threshold; Krum/Trimmed Mean only baselines; no median/MAD | No | No (encryption only) | MEDIUM |
| albanbay2025ids | ABSTRACT_ONLY | Crossref abstract; web search snippets | Yes (JSAN 14(4) 78, July 2025) | not stated | not stated | not stated | not stated | not stated | not stated | LOW (provisional) |
| alghadi2025dos | METADATA_ONLY | Crossref | Yes (CSA vol 3, 100098, Dec 2025) | unknown | unknown | unknown | unknown | unknown | unknown | LOW (unknown) |
| peng2025fdids | FULL_TEXT (Europe PMC XML, ~40% read) | PMC12300861 | Yes (Sensors 25(14) 4309) | No (all clients participate, m=K) | No (synchronous) | No (missing data rows deleted) | No (FedAvg + FedProx) | No formal metric (reports best/worst client accuracy) | No | LOW |
| rahmati2025cybersecurity | FULL_TEXT of arXiv v1 preprint only (sole author Rahmati); journal version (Rahmati and Pagano) ABSTRACT_ONLY | arxiv.org/pdf/2502.10599; Crossref abstract | Yes (Informatics 12(3) 62; Crossref: Rahmati and Pagano) | No | No (latency of HE only) | No | No (Byzantine/poisoning listed as future work) | No | Preprint states Gaussian DP noise added to gradients; guarantee not verified; journal abstract mentions HE only | LOW |
| albogami2025deepfl | FULL_TEXT (Europe PMC XML, ~64% read) | PMC11791079 | Yes (Sci Rep 15, 4041) | No (server picks random subset) | No | No | No (FedAvg) | No | No | LOW |
| zhang2026endpca | ABSTRACT_ONLY | OpenAlex; Crossref | Yes (TIFS 21, 1438-1453) | not stated | not stated | not stated | Ensemble of weak BRARs with entropy-weight trust score | not stated | not stated | LOW (provisional) |
| zhang2026malicious | ABSTRACT_ONLY | pure.bit.edu.cn; OpenAlex; Crossref | Yes (TNSE 13, 6027-6040) | not stated | not stated | not stated | HadAGG: cosine similarity + Shapley values, gradient projection | not stated (Shapley contribution scoring is not participation fairness) | not stated | LOW (provisional) |
| zhu2026bpflh | FULL_TEXT (author accepted manuscript, keyword-searched) | gala.gre.ac.uk AAM PDF; Crossref | Yes (TDSC 23(3) 6103-6118) | No (not found) | No (not found) | No (not found) | Bray-Curtis dissimilarity filtering; Median/Trimmed-Median/Krum/FLTrust as baselines; its scoring also uses a median and std. dev. of scores | Not found | Not its mechanism (CKKS HE); DP only mentioned in related work | LOW |
| liu2026anonymous | ABSTRACT_ONLY | OpenAlex; Crossref | Yes (TDSC 23(3) 5214-5225) | not stated | not stated | not stated | "baffle" mechanism limiting influence of malicious updates | not stated | not stated (single-masking, shuffling) | LOW (provisional) |
| shu2026trustworthy | ABSTRACT_ONLY | OpenAlex; Crossref | Yes (IoT-J 13(7) 12673-12686) | not stated | not stated | not stated | Multi-Krum, Median, mean-based rules run under secure two-party computation | not stated | not stated (cryptographic) | LOW (provisional) |
| s2dfl2026 | ABSTRACT_ONLY | OpenAlex (Gold OA but no full text retrieved); Crossref | Yes (OJCS 7, 914-923) | not stated | not stated | not stated | ASF-Agg: per-round statistical filtering plus reputation | not stated | Local DP (S-ALDP), eps=5.0 example; certification not verified | LOW (provisional) |

Access counts: FULL_TEXT 6 (soomro, latif, peng, rahmati [preprint only], albogami, zhu); ABSTRACT_ONLY 7 (carillo, albanbay, endpca, zhang-malicious, liu, shu, s2dfl); METADATA_ONLY 1 (alghadi).

## Per-entry notes

### soomro2026securedyn (FULL_TEXT, arXiv preprint)
URL: https://arxiv.org/html/2601.06466v1 (TNSM version 23:1742-1765 confirmed through Crossref and a Nottingham repository record; journal text not read, so details may differ).
Does: IoT IDS with poisoning detection via "dynamic temporal gradient auditing" (incremental Gaussian mixture, Mahalanobis distance and its trajectory change; accept/down-weight/reject), "privacy protection against inference and eavesdropping attacks through secure aggregation" (transformed additive ElGamal; the paper also mentions CKKS elsewhere, an internal inconsistency), personalized classifier with logit-adjusted loss. Threat model: honest-but-curious server, malicious clients up to 50%, no collusion. Data: mini N-BaIoT split over 20 clients (50 rounds, 4 local epochs, attack ratios 10-50%; Dirichlet eta=0.1, benign/attack-only, IID) plus TON_IoT. No route-aware selection, packet-level delivery, imputation, or fairness found. Contrasts itself with DP ("Unlike differential privacy, which introduces noise ... this encryption mechanism preserves the exact model updates"); no DP guarantee.
Sentence checks: "temporal gradient auditing with secure aggregation against poisoning" SUPPORTED. "focus on the detector, poisoning defence or privacy layer, not on delivery path/selection" SUPPORTED (all clients participate each round, as far as the text read shows).
Closeness LOW: shares the IDS + poisoning + privacy setting; no network/selection/delivery layer.

### carillo2026incremental (ABSTRACT_ONLY)
URL: OpenAlex record for doi 10.1109/tnsm.2026.3675031; Crossref. Hybrid OA (CC BY-NC-ND) but no PDF retrieved. Abstract: federated class-incremental learning for IoT NIDS, three IoT datasets, 0-day attacks, few-sample generalization, compared with centralized baselines. Nothing on selection, delivery, robustness or DP was stated in the abstract. Not cited in related_work.tex. Closeness LOW (provisional).

### latif2026multimodel (FULL_TEXT)
URL: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13210706/fullTextXML (read to the end of Sec. 4.8; conclusion unread).
Does: AMM-HFL, client/edge/cloud tiers, 50 clients, 5 edge servers (10 each); multiple global models, client-side model selection by lowest local loss; edge cosine-distance hierarchical clustering (threshold 0.4) isolates anomalous updates; cloud similarity merge; X25519/ChaCha20-Poly1305 transport encryption. Threat model: poisoning by Gaussian-noise gradients and label-manipulation backdoors, 5/15/30% malicious, plus model replacement and Sybil colluding clients. Dataset IDSIoT2024, IID and extreme non-IID, 50 rounds, MLP. Baselines FedAvg, Krum, Trimmed Mean. Per-tier latency is reported, but no packet-loss model, no imputation, no fairness metric, no DP, no median/MAD.
Sentence check: "hierarchical multi-model aggregation" SUPPORTED. Delivery/selection statement SUPPORTED (selection is by loss, assignment static).
Closeness MEDIUM (honest label): same client count (50) and IDS-under-poisoning framing with statistical update filtering; different mechanism, no delivery/selection/fairness.

### albanbay2025ids (ABSTRACT_ONLY)
URL: Crossref abstract, https://api.crossref.org/works/10.3390/jsan14040078 (MDPI blocked). Compares DNN, CNN, CNN+BiLSTM on CICIoT2023 with up to 150 simulated devices; accuracy, convergence speed, latency, model size across data scales; Raspberry Pi 5 tests. Sentence "studies apply FL to IoT intrusion detection": SUPPORTED. The statement about focus (detector vs. delivery/selection) is CANNOT_CHECK beyond the abstract, which mentions none of selection/delivery/fairness. Closeness LOW, but it shares CICIoT2023 and a device-count scaling theme; its internals were not read.

### alghadi2025dos (METADATA_ONLY)
Crossref only (https://api.crossref.org/works/10.1016/j.csa.2025.100098); no abstract retrieved; ScienceDirect blocked. The title supports "FL for DoS detection in IoT with ensemble feature selection and deep learning". Sentence "studies apply FL to IoT intrusion detection": PARTLY/title-level SUPPORTED. Focus statement: CANNOT_CHECK. I describe no internals.

### peng2025fdids (FULL_TEXT)
URL: Europe PMC PMC12300861 (about 100k of 250k characters read, so N-BaIoT results and comparisons were unread). FedProx proximal term + knowledge distillation (T=3, lambda=0.5, beta=0.1), mutual-information feature selection, five-layer DNN, 9 clients, 40 rounds, Dirichlet theta 1 and 0.1, Edge-IIoT and N-BaIoT. Quote: "both the central server and the clients ... are considered trusted parties"; Algorithm 1 "m=K (all clients participate)". No poisoning, no packet loss, no imputation (rows with missing values deleted), no robust aggregation, no DP.
Sentence checks: "knowledge distillation for non-IID data" SUPPORTED; listed among FL-IDS studies SUPPORTED; focus statement SUPPORTED. LOW closeness.
Note: related_work.tex line 5 lists peng2025fdids in a group described as "Surveys and studies"; it is a study, fine.

### rahmati2025cybersecurity (FULL_TEXT arXiv v1; journal ABSTRACT_ONLY)
URLs: https://arxiv.org/pdf/2502.10599 (v1, 14 Feb 2025, sole author Milad Rahmati; the journal version has Pagano as second author, so the texts may differ); Crossref abstract for the journal version. Preprint: GRU/RNN anomaly detection, homomorphic-encryption aggregation, simulated 1,000 heterogeneous devices, CICIDS2017 plus synthetic traffic, convergence "within 20 rounds for networks with up to 2,000 devices"; DP section: Gaussian noise added to gradients, a figure on DP noise impact; poisoning/Byzantine failures appear only as future work. No route-aware selection, packet delivery, imputation, robust aggregation or fairness found in keyword search. Whether DP carries a certified epsilon was not verified. Journal abstract (Crossref) mentions HE and GRU, >98% accuracy, 20% less energy and 30% less communication overhead; those figures were not checked in text.
Sentence check: "FL applied to IoT intrusion detection": SUPPORTED at the level of threat (DDoS) detection. Focus statement: SUPPORTED for the preprint. Closeness LOW; note it includes Gaussian-noise DP, which resembles our optional noise arm only superficially.

### albogami2025deepfl (FULL_TEXT)
URL: Europe PMC PMC11791079 (about 100k of 157k characters read). IDFLM-ES: min-max normalization, golden jackal feature selection, federated hybrid deep belief network, dung beetle hyperparameter tuning, FedAvg ("a federated averaging model by calculating an average weight of the parameter"), random subset selection ("the server randomly chooses a subset"), Edge-IIoTset (15,000 samples, 15 classes, 70:30), accuracy 98.24%. Threat model informal. None of the six checklist features present. Not cited in related_work.tex. Closeness LOW.

### zhang2026endpca (ABSTRACT_ONLY)
OpenAlex abstract: entropy-weight combination of multiple weak Byzantine-robust aggregation rules into one trust score; convergence proof with bounded error; "consistently outperforms existing BRARs". Closed access. Not cited in related_work.tex. Closeness LOW (provisional): robust aggregation overlap in class only.

### zhang2026malicious (ABSTRACT_ONLY)
URLs: https://pure.bit.edu.cn/en/publications/malicious-or-benign-enhancing-the-contribution-of-model-updates-i/ and OpenAlex. HadAGG: cosine similarity and Shapley values separate benign, malicious, and benign-outlier updates; malicious updates are corrected by gradient projection, not discarded; weighted aggregation. Sentence "recent Byzantine-robust schemes address heterogeneous data": SUPPORTED (abstract states the heterogeneous-setting weakness of statistical filtering). Closeness LOW.

### zhu2026bpflh (FULL_TEXT, author accepted manuscript)
URL: https://gala.gre.ac.uk/id/eprint/52448/8/MA%2052448_BPFLH_Byzantine-Robust_Privacy-Preserving_Federated_Learning_%28AAM%29_2026.pdf (the AAM, not the version of record). Threat model (quote): "no more than N/2 users ... are either compromised or under the control of a malicious adversary ... label flipping or model poisoning", plus honest-but-curious non-colluding dual servers. Mechanism: Bray-Curtis element-wise dissimilarity with CKKS encryption. Setup: N=100 users, 100 rounds, 5 local epochs, Dirichlet beta=0.2, MNIST/Fashion-MNIST/CIFAR-10; baselines FedAvg, Median, Trimmed-Median, Krum, FLTrust, PEFL. The scoring step uses the median and standard deviation of scores (keyword hits at the algorithm description; I did not verify it is a MAD rule). Keyword search found no mention of packet loss, dropout, missing updates or fairness; DP appears only in related-work text (CoS-HFL).
Sentence check: "Byzantine-robust schemes address heterogeneous data, privacy and secure aggregation": SUPPORTED. Closeness LOW (shares: robust filtering with median-type statistics; differs: image datasets, cryptographic privacy, no delivery/selection).

### liu2026anonymous (ABSTRACT_ONLY)
OpenAlex abstract: single-masking secure aggregation, secure shuffling (removes metadata such as source IP and timestamps) for client anonymity, "baffle" mechanism limiting malicious-update influence, resistant to poisoning "even when 50% of fog nodes are contaminated", over 20% aggregation-efficiency gain. Sentence "address privacy and secure aggregation": SUPPORTED. LOW (provisional).

### shu2026trustworthy (ABSTRACT_ONLY)
OpenAlex abstract: secure two-party computation across two non-colluding servers so that Multi-Krum, Median and mean-based Byzantine-robust rules can run on confidential updates; acceptable overhead. Sentence "address privacy and secure aggregation": SUPPORTED (privacy via secure computation; "secure aggregation" is a loose description). LOW (provisional).

### s2dfl2026 (ABSTRACT_ONLY)
OpenAlex abstract: S-ALDP (sparsity-guided adaptive local DP with Top-k and noise calibration, about 95% communication reduction) and ASF-Agg (per-round statistical filtering plus reputation tracking) in a hierarchical edge-cloud framework; non-IID industrial IoT and image data; eps=5.0 example; up to 82.6% on CIFAR-10 under label flipping. Not cited in related_work.tex. Closeness LOW (provisional): it has noise injection and filtering together, but we could not read how it accounts for privacy.

## Overall assessment

1. Overlap with our contribution. None of the 14 does what our study does. The six full texts (Soomro preprint, Latif, Peng, Rahmati preprint, Albogami, Zhu) contain none of: route-aware client selection, a packet-level delivery/retransmission model, median-based surrogate imputation of missing updates, or a participation-fairness measure (Gini, never-selected clients). Latif is the closest (50 clients, statistical filtering of poisoned updates, latency reporting) and Zhu/Shu touch median-type robust rules, but neither studies which updates reach the aggregator. DP: Rahmati's preprint adds Gaussian noise; S2D-FL uses local DP (abstract only); neither was read closely enough to say whether a formal epsilon is certified.
2. Gap statement. Not contradicted by any of the 14. Limits: seven are ABSTRACT_ONLY and one METADATA_ONLY, so absence of route/delivery/fairness content there means "not mentioned in the abstract/metadata", not "absent from the paper". The gap statement is already scoped to "the sources above", which remains accurate.
3. Wording risks in related_work.tex. (a) The scope note says full texts were not re-read; this review did read six, so the note can be tightened. (b) Line 5 begins "Surveys and studies"; none of albanbay, alghadi, peng, rahmati is a survey (agrawal2022flids is outside this group). (c) The "These works focus on ... not on delivery path/selection" sentence is verified only for the six full-text entries; it is unverified for Albanbay and Alghadi. (d) Rahmati's arXiv preprint and the journal version have different author lists; the bib follows the journal version, which Crossref confirms.

## Corrections to the bib

No field-level correction is required: all 14 entries match Crossref (authors, title, venue, year, volume, pages/article number, DOI). Items to note:
- carillo2026incremental: Crossref shows no volume/pages (page "1-1", early access); keep the existing note. It is not cited in related_work.tex.
- Issue numbers are absent in Crossref for soomro, endpca, zhang2026malicious, s2dfl and alghadi; the bib omits them, which is consistent.
- Keys not cited in related_work.tex (carillo2026incremental, zhang2026endpca, s2dfl2026, albogami2025deepfl): cite them or drop them if not used elsewhere.
- IEEE landing pages were not read (blocked); the check for IEEE items is Crossref/OpenAlex-level, so treat as metadata-verified, not publisher-page-verified.

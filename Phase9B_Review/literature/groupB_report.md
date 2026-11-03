# Group B literature review (21 entries)

Reviewer note on method and reliability. Pages were read through WebFetch, which returns a model-generated digest of the page, not raw text. Quotes marked "(digest)" were relayed that way and should be spot-checked against the PDF before they go into the manuscript. Publisher sites (MDPI, nature.com, Springer, ScienceDirect, IEEE Xplore, Inderscience) returned 403 or cookie redirects. Full texts of PMC-indexed open-access papers were therefore read through Europe PMC (`https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML`). Metadata was checked against Crossref (`https://api.crossref.org/works/<DOI>`) and Europe PMC. Abstracts for paywalled items came from OpenAlex (abstract text reconstructed from its inverted index, so paraphrased by the tool) or from search snippets. Search engines failed to find several exact titles. That does not mean the papers do not exist, because Crossref confirms every DOI.

Where the table says FULL_TEXT, tables, figures and reference lists were usually not visible to me. The caveats are in the per-entry notes.

## 1. Access summary

| Level | Count | Entries |
|---|---|---|
| FULL_TEXT | 7 | almeida2025modular, alanazi2026edgeguard, zhang2026adaptive, liu2024iiot, mughal2024adaptive, padmavathi2025trust, wang2024trust (preprint version only) |
| FULL_TEXT_PARTIAL (first about 55% of body read; experiments not read) | 1 | bayat2025qlearning |
| ABSTRACT_ONLY | 8 | chen2025hierarchical, haripriya2025fault, aburukba2025scheduling, bhardwaj2024routing, zhou2024qos, geng2024smpc, shah2026trisafe, wang2026desa |
| METADATA_ONLY | 5 | abdallah2026routing, liu2026reliability, tang2026fedcst, lan2025ckks, li2023privacy |

Four of the 21 are in the bib but are not cited anywhere in the manuscript text (grep over the Phase9 `.tex` and `.md` files): padmavathi2025trust, wang2026desa, wang2024trust and bayat2025qlearning. The last two appear only in `UNRESOLVED_ISSUES.md`.

## 2. Master table

Closeness is measured against our study: route-scored client selection with delivery and fairness metrics, packet-level delivery models, surrogate imputation, median/MAD filtering with momentum, diagnostic DP, and a pre-registered null result.

| Key | Access | Metadata vs Crossref / Europe PMC | Route-aware client selection | Packet-level delivery | Imputation of missing updates | Median/MAD or robust aggregation | Participation fairness measured | DP (certified?) | Closeness |
|---|---|---|---|---|---|---|---|---|---|
| chen2025hierarchical | ABSTRACT_ONLY | OK | not stated | no (node "paralysis") | not stated | no (multi-center aggregation) | not stated | not stated | MEDIUM-LOW |
| haripriya2025fault | ABSTRACT_ONLY | OK | not stated | no (edge-server "paralysis ratio") | not stated | no (FedProx) | not stated | not stated | MEDIUM-LOW |
| almeida2025modular | FULL_TEXT | OK | no (round-robin) | no (worker-level failure events) | no (reassignment / 50% threshold) | no | no | no | MEDIUM |
| liu2026reliability | METADATA_ONLY | OK | unknown | unknown | unknown | unknown | unknown | unknown | UNKNOWN (title: "secure" and "configurable reliability") |
| tang2026fedcst | METADATA_ONLY | OK | unknown | unknown | unknown | unknown | unknown | unknown | UNKNOWN (title: reliable FL, clustered data) |
| aburukba2025scheduling | ABSTRACT_ONLY | OK | no (VM scheduling) | no | no | no | not stated | not stated | LOW |
| abdallah2026routing | METADATA_ONLY | OK | unknown | unknown | unknown | unknown | unknown | unknown | UNKNOWN (title: federated, secure, adaptive routing) |
| zhang2026adaptive | FULL_TEXT | OK | no (100% participation) | no (PDR/loss only as outputs in NS-3) | no | no (FedProx, loss-softmax weights) | no (per-client accuracy spread only) | DP asserted, no parameters, not certified | MEDIUM-LOW |
| bhardwaj2024routing | ABSTRACT_ONLY | OK | n/a (FL trains a next-hop policy) | simulation of opportunistic routing (delivery probability) | not stated | not stated | not stated | privacy claimed, unspecified | MEDIUM-LOW |
| alanazi2026edgeguard | FULL_TEXT (tables not seen) | OK | no (task-to-node scheduling) | no | no (median imputation of feature values only) | no (stated as future work) | no | no | LOW-MEDIUM |
| zhou2024qos | ABSTRACT_ONLY | OK | not stated | not stated | not stated | not stated | not stated | not stated | LOW |
| liu2024iiot | FULL_TEXT (results partly figure-based) | OK | partial (selection by training time and energy) | no (simplified average-bandwidth model) | no | no | no | no | LOW-MEDIUM |
| mughal2024adaptive | FULL_TEXT | OK | partial (node quality score = network conditions + AI expertise) | no | no | no | no | no | MEDIUM |
| padmavathi2025trust | FULL_TEXT | OK | no | no (Wi-Fi/LTE links only simulated through non-IID partitioning) | no | no (FedAvg) | no | Gaussian DP eps=1.0, delta=1e-5; no certification claim; plus CKKS | LOW-MEDIUM (uses UNSW-NB15, poisoning at 10-30%) |
| wang2024trust | FULL_TEXT of the Research Square preprint, not the Springer version | OK; the bib year 2025 is the volume year | no | no | no (only data cleaning) | no | no | no (AES encryption of parameters) | LOW |
| bayat2025qlearning | FULL_TEXT_PARTIAL | OK | no (DQN picks a proxy node; not FL) | no | no | no | no | no | LOW |
| li2023privacy | METADATA_ONLY | OK | unknown | unknown | unknown | unknown | unknown | unknown | LOW (privacy paper, from title) |
| lan2025ckks | METADATA_ONLY | OK | unknown | unknown | unknown | unknown | unknown | unknown | LOW (CKKS, from title) |
| geng2024smpc | ABSTRACT_ONLY | OK | no | no | no | not stated | not stated | not stated | LOW |
| shah2026trisafe | ABSTRACT_ONLY | OK | no | no | not stated | Byzantine, label-flip, FANG, time-delay attacks evaluated; defence is verifiable secure aggregation | not stated | DP noise added homomorphically; guarantee depends on assumptions (see notes) | MEDIUM-LOW |
| wang2026desa | ABSTRACT_ONLY | OK; Crossref title says "D2D", the bib expands it | no | no | no | Byzantine-robust, zk-SNARK based | no | no | LOW |

## 3. Per-entry notes

For each entry the order is: access and URL, metadata, what the paper does, verdict on each citing sentence, closeness.

### chen2025hierarchical (ABSTRACT_ONLY)
- Access: Crossref `https://api.crossref.org/works/10.1109/TNNLS.2024.3362974` and OpenAlex abstract. OpenAlex lists the paper as closed access.
- Metadata: authors, title, TNNLS 36(1), 47-61 and DOI all match. Crossref gives January 2025.
- Does (abstract, paraphrased by OpenAlex): proposes multicenter hierarchical FL (MCHFL), which replaces the single central server with several edge global aggregation centers. Reports that accuracy stays high with up to 50% of nodes paralyzed on MNIST, FashionMNIST and CIFAR-10, with maximum accuracy drops of 2.60%, 5.12% and 16.73%. Claims theoretical grounding. No network, route, imputation, fairness or DP content was visible.
- Sentence "Fault-tolerant and reliability-aware FL has been proposed for hierarchical edge networks": SUPPORTED at abstract level.
- Closeness: MEDIUM-LOW. It is about node and server failure and aggregator topology, evaluated on image data. It has no delivery model, no selection policy and no fairness measurement.

### haripriya2025fault (ABSTRACT_ONLY)
- Access: Crossref plus the OpenAlex abstract. OpenAlex says gold open access, CC-BY. `https://ieeexplore.ieee.org/document/11153937/` returned empty to WebFetch, so I could not read the full text even though it is open.
- Metadata: authors, title, IEEE Access 13, 158737-158750 and DOI all match.
- Does (abstract, paraphrased): hierarchical FL with clustered edge servers, transfer learning from pre-trained EfficientNet-B0 and TabNet, and FedProx aggregation. Models reliability as a "paralysis ratio" of failed or unresponsive edge servers. Reports accuracy above 93% with up to 40% of servers paralyzed, 4-6% accuracy gain and 25% lower communication latency than MCHFL (chen2025hierarchical), and analyses hyperparameter trade-offs.
- Sentence "via edge servers": SUPPORTED at abstract level.
- Closeness: MEDIUM-LOW. It is closest to our topic through fault modelling, but the failure unit is the server, not the packet or client update. No selection-fairness or imputation content is stated. Full text could change this, so it is worth reading.

### almeida2025modular (FULL_TEXT)
- Access: Europe PMC PMC12197033 `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12197033/fullTextXML`. I received about the first 100k of 135k characters (abstract to data availability) and did not read the rest.
- Metadata: Sensors 25(12), 3812, DOI 10.3390/s25123812 and authors all match. Europe PMC and Crossref agree.
- Does:
  - Modular FL framework (FlexFL) with seven modules. Supports centralized and decentralized, synchronous and asynchronous training over MPI, MQTT, Kafka and Zenoh.
  - Failures are benign and simulated: a 1% or 5% chance per worker every 10 s, with graceful exit and rejoin.
  - UNSW-NB15 (preprocessed NetFlow, binary), 10 workers, 10 rounds, ANN, ARM VMs.
  - Selection is Round Robin over a subpool. Synchronous rounds proceed once 50% of the selected subpool reports.
  - No imputation, no robust aggregation, no fairness metric, no DP.
  - Digest: "metadata such as bandwidth and latency could support better scheduling in future work".
- Sentence "for modular dynamic edge environments": SUPPORTED.
- Closeness: MEDIUM. Same dataset (UNSW-NB15) and same theme of FL under failures, but failures are worker-level, there is no route scoring and no packet-level model, and it does not examine whether faults skew participation. It is an engineering framework, not a controlled measurement of single factors.

### liu2026reliability (METADATA_ONLY)
- Access: Crossref only. OpenAlex has no abstract and the paper is closed. No full text.
- Metadata: authors, title, Computer Networks 274, article 111808, DOI all match. Crossref gives January 2026; the DOI year 2025 reflects online-first publication.
- Content: not read. Title only: "Secure FL with configurable reliability in heterogeneous edge computing".
- Sentence "for configurable reliability in heterogeneous edge computing": CANNOT_CHECK. It is consistent with the title. I cannot say what "reliability" means in the paper (for example straggler or dropout tolerance, or something coding-based). The word "Secure" suggests a security component that our sentence omits.
- Closeness: UNKNOWN. Flagged as potentially relevant, since reliability plus heterogeneity could include dropout recovery. It must be read before the gap statement is finalized.

### tang2026fedcst (METADATA_ONLY)
- Access: Crossref only. OpenAlex has no abstract. A search surfaced a different "FedCST" (Wang et al. 2024, clustering and split training); that is not this paper and was not used.
- Metadata: authors, title, Computer Networks 280, article 112209, DOI all match. Crossref gives May 2026.
- Content: not read.
- Sentence "for clustered IIoT data": CANNOT_CHECK, consistent with the title. "Reliable" in the title could refer to robustness or trustworthiness under clustered non-IID data, not to fault tolerance. Grouping it under "Fault tolerance and reliability" is therefore not verified.
- Closeness: UNKNOWN.

### aburukba2025scheduling (ABSTRACT_ONLY)
- Access: Crossref `https://api.crossref.org/works/10.3390/math13132198` and OpenAlex abstract (gold open access). `mdpi.com` returned 403, including the PDF.
- Metadata: Mathematics 13(13), 2198, 5 July 2025 and DOI match. Crossref authors are "Sheeja Rani S" and "Raafat Aburukba". The bib has "Rani S, Sheeja", which keeps the Crossref family name "Rani S". The key uses "aburukba".
- Does (abstract, paraphrased): MRKFL-FTS, a fault-tolerant scheduler for IoT requests in a cloud. Each server trains a radial-kernel SVR locally to identify resource-efficient VMs, the local models are aggregated, and a weighted round-robin task assigner allocates requests. Reports gains in efficiency, throughput, makespan, response time and energy.
- Sentence "request scheduling in cloud data centres" listed under "Fault-tolerant and reliability-aware FL has been proposed for ...": PARTLY. The paper is a FL-based scheduler whose fault tolerance concerns cloud VM and resource failure. It is not about FL training being fault-tolerant. The grouping is therefore loose. Suggested wording: "FL has been used inside a fault-tolerant request scheduler for cloud data centres".
- Closeness: LOW. No client selection, no update loss.

### abdallah2026routing (METADATA_ONLY)
- Access: Crossref only. OpenAlex has no abstract and is closed. The Springer page redirected to a cookie handshake.
- Metadata: J. Comb. Optim. 51(2), article 29, DOI 10.1007/s10878-026-01408-5. Crossref gives March 2026. All match the bib.
- Content: not read. Title only: "Federated Edge Intelligence for Secure and Adaptive Routing in IoT: A GRU-RL Based Framework". It is a single-author paper.
- Sentence "Routing and scheduling have been combined with FL in several ways": consistent with the title. CANNOT_CHECK beyond that.
- Closeness: UNKNOWN. It is one of the entries that most needs a full read, because it is the only one in this group whose title states routing, security and federation together.

### zhang2026adaptive (FULL_TEXT)
- Access: Europe PMC PMC13079809 `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13079809/fullTextXML`. I read characters 0-200000 of about 230000 (the last roughly 30k, likely back matter, were not read). nature.com redirected to a cookie handshake.
- Metadata: Sci Rep 16(1), 12246, DOI 10.1038/s41598-026-41074-5 and authors all match.
- Does:
  - A four-layer device, edge, fog and cloud architecture for power IoT routing. A Bi-LSTM with attention predicts traffic, energy, link quality and queue length. A multi-objective cost over energy, latency, inverse reliability and capability compatibility then drives path selection.
  - FL trains the shared prediction model. Edge nodes are FL clients, and aggregation is a data-size-weighted average every 30 s.
  - Client participation is a parameter, 50-100%, default 100%. "No selection strategy is described" (digest). FL does not select clients by route quality.
  - Setup: NS-3 on a 1000-node topology, 30 runs, 50 edge FL clients, 100 global iterations. No real traces. Grid topologies "based on IEEE standard test systems".
  - Failure scenarios cover node failure rates of 5-30%, interference and partitions. Packet loss is reported as an outcome (under 1% against 5-12% for AODV, DSR and OLSR). No packet-level failure model for update delivery.
  - Aggregation is FedProx with a loss-softmax weighting. No median or MAD, no imputation.
  - No fairness metric. It reports per-client accuracy spread (best 96%, worst 88%, std 3.2%).
  - DP and "secure aggregation" are asserted ("through differential privacy mechanisms and secure aggregation protocols", digest). No epsilon, delta or clipping, and no threat model.
  - Stated limitation: it assumes a "relatively stable network topology during federated learning convergence periods".
- Sentence "Routing and scheduling have been combined with FL in several ways": SUPPORTED, in the sense that FL is used to learn a routing model.
- Closeness: MEDIUM-LOW. It is a routing-for-IoT paper that uses FL as a training mechanism. We do the converse: the network path determines which updates reach the aggregator. It does not touch our questions on selection, fairness, packet-level delivery of updates or robust aggregation.

### bhardwaj2024routing (ABSTRACT_ONLY)
- Access: Crossref plus the OpenAlex abstract (closed). `inderscienceonline.com` returned 403.
- Metadata: Int. J. Sensor Networks 46(1), 24-38, 2024, DOI 10.1504/IJSNET.2024.141609 and authors all match.
- Does (abstract, paraphrased): FLRouter for opportunistic IoT networks. Nodes pick next-hop relays from their current state and local knowledge. Simulations show delivery probability up to 16% and 13% better as buffer size grows, and overhead ratio lower by roughly 42% and 34%. Privacy is mentioned.
- Sentence "Routing ... combined with FL": SUPPORTED at abstract level.
- Closeness: MEDIUM-LOW. FL is used to learn forwarding policy. It is not about which FL clients' updates arrive.

### alanazi2026edgeguard (FULL_TEXT, tables and algorithms not seen)
- Access: Europe PMC PMC13029866 `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13029866/fullTextXML`. I received the main body to the conclusions (about 100k of 162k characters). Tables 1-12, figures and algorithm boxes were not in the digest, and the last 62k characters were not read.
- Metadata: Sensors 26(6), 1989, DOI 10.3390/s26061989 and authors all match.
- Does:
  - Four stages: trust scoring, load and state forecast, trust-gated task scheduling (threshold 0.7, risk budget 0.3), and FedAvg-style adaptation of the client scheduling policy.
  - Data: Edge-IIoTset (61 features), trace-driven simulation. T=30 rounds.
  - It schedules tasks onto edge nodes. It does not choose network paths or routes ("Federated client sampling is described only as randomized", digest).
  - No packet-level model. No missing-update imputation (median imputation applies to missing features only). No robust aggregation: "Extending the framework to incorporate Byzantine-resilient aggregation" is future work. No participation fairness metric (it reports worst-client latency in a table I could not see).
  - No DP. It states "We do not explicitly model adversarial federated clients" (digest).
- Sentence "Routing and scheduling have been combined with FL": SUPPORTED for scheduling. It is not routing, so grouping it with the "routing" papers is slightly loose.
- Closeness: LOW-MEDIUM. Zero-trust, load-aware FL scheduling for an IDS dataset. It does not address which clients' updates arrive or how they are weighted.

### zhou2024qos (ABSTRACT_ONLY)
- Access: Crossref and the OpenAlex abstract (hybrid open access, CC-BY), plus a Lingnan University repository snippet. `doi.org` redirected to `linkinghub.elsevier.com`, which returned only "Redirecting".
- Metadata: Ad Hoc Networks 156, 103430, April 2024, DOI and authors match.
- Does (abstract): an edge-cloud architecture for QoS of AIoT devices, with FL used to train locally for privacy. Compared against a centralized approach on two widely used datasets. No further detail.
- Sentence "edge-cloud ... architectures target quality of service": SUPPORTED at abstract level.
- Closeness: LOW.

### liu2024iiot (FULL_TEXT, experiments partly figure-based)
- Access: Europe PMC PMC11244223 `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11244223/fullTextXML`. I read the whole text across two fetches (0-179k).
- Metadata: Sensors 24(13), 4182, DOI 10.3390/s24134182 and authors all match.
- Does:
  - Software-defined, containerized IIoT edge framework. FL part: each round selects k devices from a time-sorted queue of estimated local training times, with an energy cap that offloads excess computation to the edge center. Aggregation is a data-size-weighted average.
  - Experiments are simulation only: 40 devices, 15 per round, MNIST, MLP, random selection as the only baseline. Training time is 30-50% lower and energy 35-55% lower.
  - The authors say the transmission model is "significantly simplified" and ignores queuing, MAC, ARQ and FEC. It has no fairness measurement; it criticizes earlier selection methods for lacking "fairness considerations in device selection" (digest). No threat model, no robust aggregation, no DP, no imputation.
- Sentence "resource-aware FL architectures target ... resource constraints": SUPPORTED. The "quality of service" part is only loosely met: the paper targets delay and energy.
- Closeness: LOW-MEDIUM. It selects clients by compute and time, not by route or delivery success, and does not measure fairness. It does, however, name the lack of fairness as a gap in earlier selection work, which is useful context for our fairness measurement.

### mughal2024adaptive (FULL_TEXT)
- Access: Europe PMC PMC11579390 `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11579390/fullTextXML`. I read characters 0-200000 of about 186k, so the whole text.
- Metadata: Sci Rep 14(1), 28746, DOI 10.1038/s41598-024-78239-z and authors match.
- Does:
  - MEC-AI HetFL: three layers (edge clusters, edge-AI layer, global FL). Nodes get a quality score Q from a "network score" plus an "AI-expertise score" (Eq. 4), and selection uses it.
  - Experiments were on a Google Cloud VM with Keras. Baselines were EdgeFed, FedSA, FedMP and H-DDPG, and metrics were accuracy, precision, recall and F1. The dataset is not named.
  - The "up to 5 times better" claim in the abstract is not supported by Table 1, where accuracy gaps are at most about 3 points. The text contradicts itself on overhead versus EdgeFed.
  - No packet-level model, no fairness metric, no imputation, no robust aggregation, no DP, no threat model.
- Sentence "resource-aware FL architectures target quality of service and resource constraints": SUPPORTED.
- Closeness: MEDIUM. It is the nearest read paper to "network-aware client selection". The score is network-based, but it is a static quality score. It has no packet or delivery modelling and no fairness measurement, and it is not an IDS study.

### padmavathi2025trust (FULL_TEXT; not cited in the manuscript)
- Access: Europe PMC PMC12521663 `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12521663/fullTextXML` (digest reported that tables and references were included; figures not readable).
- Metadata: Sci Rep 15(1), 35832, DOI 10.1038/s41598-025-19712-1 and authors match.
- Does:
  - AI-SET: an edge IDS (Suricata plus LSTM and decision trees), FedAvg with Gaussian DP (eps=1.0, delta=1e-5) and CKKS homomorphic encryption (TenSEAL, 128-bit), and trust-based access control.
  - Datasets: NAB and UNSW-NB15. Raspberry Pi 4 and Jetson Nano testbed, up to 100 simulated devices, 50 rounds. 94.3% accuracy, 3.2% FPR, 85% accuracy at 20% poisoning.
  - No formal threat model. No route-aware selection, no packet-level model, no imputation, no robust aggregation (plain FedAvg), no fairness metric.
  - DP is stated as a setting. No certification claim, and no accountant is described.
  - Internal inconsistencies: 28 versus 30 rounds to convergence, no variance reporting, trust weights not given.
- Closeness: LOW-MEDIUM. Same dataset (UNSW-NB15) and a DP and poisoning component. It has no network-aware selection or delivery model. Not currently cited. If cited, use it only for "FL-IDS with DP, CKKS and poisoning tests".

### wang2024trust (FULL_TEXT of preprint; not cited in the manuscript)
- Access: Research Square preprint rs-4568992 `https://www.researchsquare.com/article/rs-4568992/latest.pdf`. The PDF was saved locally and text-extracted with `pdftotext`. I searched it by keyword and read the abstract and experiment section, but did not read the whole preprint. The Springer published version was not read, so the published text may differ.
- Metadata: J. Supercomput. 81, article 232, published online 3 December 2024, DOI 10.1007/s11227-024-06715-4. Authors Wang, Li, Zuo match. The bib key says 2024 and the year field says 2025 (volume year); both are defensible and the note field is accurate.
- Does:
  - Device trust and reputation management with FL and blockchain (Algorand-style consensus, AES encryption of local models). Local SVM and a weighted aggregation by device attributes.
  - Simulated smart-home dataset of 50 devices (about 100,000 records), 90.2% accuracy. Bad-mouthing, self-promoting and on-off attacks tested on trust weights.
  - Missing values are imputed only in data cleaning. No route-aware selection, no packet-level model, no robust aggregation, no DP, no fairness metric.
- Closeness: LOW. Its robustness question is trust-score manipulation, not Byzantine updates.

### bayat2025qlearning (FULL_TEXT_PARTIAL; not cited in the manuscript)
- Access: Europe PMC PMC12594803. The digest covered the abstract through the start of the security analysis (about 100k of 183k characters). Datasets and results were not read.
- Metadata: Sci Rep 15(1), 39153, DOI 10.1038/s41598-025-24510-w and authors match.
- Does: BDEQ, a Deep Q-Network that selects a Proxy Service Providing Node per request, with a reward weighted 0.5/0.3/0.2 over trust, latency and load, plus smart contracts and a permissioned blockchain. It does not use federated learning (the digest found FL only in related work). Its abstract reports a simulated gas-industry IIoT with latency down 35% and throughput up 28%.
- Closeness: LOW. This is not an FL paper, so it is a weak entry for an FL bibliography. It was already flagged in the earlier verification report.

### li2023privacy (METADATA_ONLY)
- Access: Crossref only. OpenAlex has no abstract and the paper is closed. A search returned look-alike privacy-preserving FL papers (for example from the same UESTC group) that are not this paper; none was used.
- Metadata: FGCS 144, 205-218, July 2023, DOI 10.1016/j.future.2023.03.010 and authors match.
- Sentence "Other privacy layers use secure aggregation, secure multi-party computation or homomorphic encryption": CANNOT_CHECK for this entry. The title says only "privacy-preserving scheme under edge computing", so I cannot say which of the three techniques it uses.
- Closeness: LOW (from title).

### lan2025ckks (METADATA_ONLY)
- Access: Crossref only. OpenAlex has no abstract. A search surfaced an IRMA paper "Adaptive Lightweight FL with Aggregation-Only CKKS" that has similar words but is not confirmed to be this paper, so it was not used.
- Metadata: Internet of Things 33, 101725, September 2025, DOI 10.1016/j.iot.2025.101725 and authors match.
- Sentence on homomorphic encryption: consistent with the title (CKKS is a homomorphic encryption scheme). Everything else is CANNOT_CHECK.
- Closeness: LOW.

### geng2024smpc (ABSTRACT_ONLY)
- Access: Crossref plus the OpenAlex abstract (closed).
- Metadata: 2024 IEEE AIoT, pp. 117-122, 24 July 2024, DOI 10.1109/AIoT63253.2024.00032 and authors match.
- Does (abstract, paraphrased): FL for IoT that combines MPC (so client updates are combined without exposing individuals) with blockchain. A security analysis covers model inversion, data poisoning and aggregator failure.
- Sentence on secure multi-party computation: SUPPORTED at abstract level.
- Closeness: LOW.

### shah2026trisafe (ABSTRACT_ONLY)
- Access: Crossref plus the OpenAlex abstract (gold open access, but `doi.org` full text not fetched).
- Metadata: IEEE Access 14, 89354-89379, DOI 10.1109/ACCESS.2026.3700048 and authors match. Crossref gives only the year 2026.
- Does (abstract, paraphrased): gateway-assisted IoT FL with a coordinator and three threshold helpers. It combines verifiable encrypted updates with range proofs, a plaintext-equivalence binding step, DP noise added homomorphically before decryption, and fixed-cadence batching against timing inference. Evaluated on Edge-IIoTset, N-BaIoT and MNIST under Byzantine, label-flip, FANG and time-delay attacks, with accuracy within 0.1-2.1 points of the no-attack baseline. Assumes the coordinator does not collude with helpers and that at least two helpers add honest DP noise.
- Sentence on secure aggregation, SMPC or homomorphic encryption: SUPPORTED at abstract level. The sentence undersells the paper: it also has a Byzantine evaluation and DP, and it uses IDS datasets.
- Closeness: MEDIUM-LOW. Overlaps our (d) and (e) in kind (IDS datasets, attacks, DP) but not in mechanism. It has no routing, packet-level delivery or participation fairness. Its DP guarantee is tied to explicit assumptions, which gives it a different standing from our diagnostic epsilon.

### wang2026desa (ABSTRACT_ONLY; not cited in the manuscript)
- Access: Crossref plus the OpenAlex abstract (closed).
- Metadata: IEEE TIFS 21, 1987-2001, DOI 10.1109/TIFS.2026.3658996 and authors match. Crossref title ends "Zero-Trust D2D Networks", while the bib writes "Device-to-Device".
- Does (abstract, paraphrased): Byzantine-robust decentralized secure aggregation for D2D FL with zk-SNARK proofs and a one-time masking scheme with dynamic adjacency and trust handling. No routing or packet-level content was stated.
- Closeness: LOW.

## 4. Sentence-level verdicts, `related_work.tex`

| Sentence (paragraph) | Cited keys | Verdict |
|---|---|---|
| "Fault-tolerant and reliability-aware FL has been proposed for hierarchical edge networks [chen], via edge servers [haripriya], for modular dynamic edge environments [almeida], for configurable reliability in heterogeneous edge computing [liu2026], for clustered IIoT data [tang] and for request scheduling in cloud data centres [aburukba]" | chen, haripriya, almeida | SUPPORTED (abstract level for chen and haripriya, full text for almeida) |
| | liu2026, tang | CANNOT_CHECK. Title-consistent only. The "reliability" meaning is unverified for both. |
| | aburukba | PARTLY. It is a FL-based fault-tolerant scheduler, not fault-tolerant FL. Rephrase. |
| "Our use of median-based surrogate imputation ... is far simpler than these mechanisms and is evaluated here only as a component" | all six | CANNOT_CHECK for liu2026, tang. PARTLY for the rest: none of the read or abstract-read papers describes missing-update imputation, so these are different mechanisms (topology redundancy, reassignment, thresholds), not more complex imputation. "Far simpler" is a comparison I could not confirm. |
| "Routing and scheduling have been combined with FL in several ways [abdallah, zhang, bhardwaj, alanazi]" | zhang | SUPPORTED (FL trains a routing predictor) |
| | bhardwaj | SUPPORTED (abstract: FLRouter) |
| | alanazi | SUPPORTED for scheduling (FL adapts a scheduling policy). It is not routing. |
| | abdallah | CANNOT_CHECK. Title-consistent only. |
| "edge-cloud or resource-aware FL architectures target quality of service and resource constraints [zhou, liu2024, mughal]" | zhou | SUPPORTED (abstract) |
| | liu2024 | SUPPORTED for resource constraints (delay and energy); QoS is only loosely met. |
| | mughal | SUPPORTED |
| "Other privacy layers use secure aggregation, secure multi-party computation or homomorphic encryption [bonawitz, shah, geng, lan, li2023]" | shah, geng | SUPPORTED (abstract level) |
| | lan | CANNOT_CHECK, title-consistent (CKKS is HE) |
| | li2023 | CANNOT_CHECK |
| Scope note: "full texts were not re-read ... we describe each only at the level its title and abstract support" | all | Accurate for 13 of the 21, and conservative for the 8 now read in full. Where full text was read it can be updated. |

## 5. Overall assessment

Overlap with our contribution among the 21:
- None of the papers I could read describes the combination of route- or delivery-scored client selection measured against participation fairness (Gini, never-selected clients), packet-coupled delivery with retransmissions, median-based surrogate imputation of missing updates, median/MAD filtering with server momentum, a diagnostic DP epsilon, and a pre-registered null result for a minimum-genuine-update guard.
- Of the routing, FL and fault-tolerance papers:
  - zhang2026adaptive (full text): routing for power IoT, with FL used to train the routing predictor. Participation is 100% by default. No client-selection strategy, no fairness metric, no update-loss handling. It reports packet loss and delivery as outcomes of the routing protocol, not as a delivery process for FL updates.
  - alanazi2026edgeguard (full text): task scheduling onto edge nodes; the authors say client sampling is random and Byzantine-resilient aggregation is future work. It is not routing in the network sense.
  - almeida2025modular (full text): the closest in setting (UNSW-NB15, benign failures, a 50% threshold for synchronous rounds). Failures are worker-level and there is no delivery model, no route-scored selection, no imputation and no fairness metric.
  - mughal2024adaptive (full text): node selection by a network-conditions score. It has no delivery process, no fairness measurement and no IDS focus.
  - bhardwaj2024routing, chen2025hierarchical, haripriya2025fault (abstract only): consistent with "FL for routing" and "aggregator or server failure", without the elements of our study, but unconfirmed beyond the abstract.
  - abdallah2026routing, liu2026reliability, tang2026fedcst (metadata only): I cannot say anything about their content.
- Is our stated gap contradicted? Not by any paper I could read. Our gap statement is explicitly limited to the sources examined, and the evidence in this group is consistent with that. Residual risk comes from three sets of papers:
  1. abdallah2026routing, liu2026reliability and tang2026fedcst, which I could not read at all.
  2. haripriya2025fault, chen2025hierarchical and bhardwaj2024routing, read only as abstracts.
  3. shah2026trisafe, read as an abstract, which covers robustness and DP on IDS data, so it is relevant to (d) and (e).
  Until those are read, the sentence "we did not find" should stay as written and should not be strengthened.
- Observations that sharpen the gap, all from papers I read:
  - liu2024iiot states that earlier selection methods lack fairness considerations, and none of the full-text papers measures participation fairness.
  - No full-text paper models packet-level delivery of updates. zhang2026adaptive and liu2024iiot simplify or leave it implicit. Almeida models worker failures only.
  - No full-text paper evaluates imputation or median/MAD filtering. Aggregation is a weighted mean or FedProx.
  - Where DP is mentioned (zhang2026adaptive, padmavathi2025trust), it is asserted as a setting with no accountant or certification. This supports presenting our diagnostic epsilon as one more "setting", but the point should not be used to criticize them without the full text of their DP sections.

## 6. Corrections to the bibliography

Metadata is correct for all 21 entries against Crossref (and Europe PMC for the eight open-access papers). Required or recommended changes:

1. wang2026desa: the Crossref title is "DeSA: Decentralized Secure Aggregation for Federated Learning in Zero-Trust D2D Networks". The bib expands it to "Device-to-Device". Match the publisher form, or confirm the IEEE Xplore title page.
2. wang2024trust: no field error. The key says 2024 and the year says 2025 (volume 81 is 2025; online 3 December 2024). Optionally rename the key or keep the existing `note`.
3. aburukba2025scheduling: the key names the second author, while the first author is Sheeja Rani S. Consider renaming it to `rani2025scheduling`. The author string "Rani S, Sheeja" follows Crossref's family-name "Rani S".
4. liu2026reliability: Crossref dates it January 2026 while the DOI carries 2025 (online first). The bib uses 2026. No change required.
5. Four entries are in the bib but uncited in the manuscript: padmavathi2025trust, wang2026desa, wang2024trust, bayat2025qlearning. Cite them or remove them. bayat2025qlearning is not an FL paper, and wang2024trust concerns trust-score attacks, so neither supports a federated robustness claim.
6. Text changes in `related_work.tex` (not a bib change):
   - Reword the aburukba clause, for example "FL has been used within a fault-tolerant request scheduler for cloud data centres".
   - Keep the tang2026fedcst and liu2026reliability clauses neutral until they are read.
   - Consider moving alanazi2026edgeguard from "routing" to "scheduling", and mentioning that shah2026trisafe also covers Byzantine robustness and DP on IDS datasets.

## 7. What I could not do

- I could not obtain any text beyond metadata for abdallah2026routing, liu2026reliability, tang2026fedcst, lan2025ckks and li2023privacy.
- I could not obtain full text for chen2025hierarchical, haripriya2025fault (open access, but IEEE Xplore returned empty), aburukba2025scheduling (open access, but MDPI returned 403), bhardwaj2024routing, zhou2024qos (hybrid OA), geng2024smpc, shah2026trisafe (gold OA) and wang2026desa.
- bayat2025qlearning was read only to the security analysis section.
- For the full-text papers, tables and figures were not visible. Numeric results quoted above come from the abstract or the digest, not from the tables.

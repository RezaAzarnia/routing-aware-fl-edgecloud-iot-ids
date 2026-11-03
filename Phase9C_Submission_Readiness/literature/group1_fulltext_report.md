# Group 1 literature verification (7 sources) - honest access report

Date of work: 2026-11-03. Result headline: **no full text of any of the 7 sources could be obtained by a legal automated route.** Every source is therefore ABSTRACT_ONLY (or weaker). I did not use pirate sites, did not bypass paywalls, and did not circumvent IEEE Xplore / Inderscience / ScienceDirect bot blocking (HTTP 418 / 403 were treated as "not accessible"). The two IEEE Access papers are gold open access (CC BY per Crossref/OpenAlex), but IEEE Xplore refuses scripted download; a human with a browser can read them legally at the DOI. Fetch note: the WebFetch tool returns a small-model digest, not raw text; everything marked "verbatim" below came from raw API/HTML responses obtained with curl (Crossref, OpenAlex, DOAJ, PubMed, Springer landing page), not from WebFetch digests.

## Machine-friendly table

| key | access level | what was actually read | closeness | contradicts gap? | sentence status |
|---|---|---|---|---|---|
| abdallah2026routing | ABSTRACT_ONLY (verbatim, Springer landing page HTML) + 37-item reference list | abstract, metadata, refs | LOW-MEDIUM | no | routing+FL clause SUPPORTED |
| liu2026reliability | ABSTRACT_ONLY, partial (search-engine digest of abstract excerpt; not verbatim) + 48-item ref list | 2 sentences of abstract paraphrased | LOW-MEDIUM | no | "reliability-oriented FL" PARTLY (reliability = node trust/collusion, not delivery) |
| tang2026fedcst | ABSTRACT_ONLY, very partial (digest of 2 abstract sentences) + 49-item ref list | metadata, 2 sentences paraphrased | LOW | no | "reliability-oriented FL" PARTLY/CANNOT_CHECK |
| haripriya2025fault | ABSTRACT_ONLY (verbatim via OpenAlex and DOAJ) | full abstract | MEDIUM-LOW | no | SUPPORTED |
| chen2025hierarchical | ABSTRACT_ONLY (verbatim via OpenAlex; PubMed record) | full abstract | MEDIUM-LOW | no | SUPPORTED |
| bhardwaj2024routing | ABSTRACT_ONLY (verbatim via OpenAlex) | full abstract | LOW-MEDIUM | no | SUPPORTED |
| shah2026trisafe | ABSTRACT_ONLY (verbatim via OpenAlex) | full abstract | MEDIUM-LOW | no | SUPPORTED (as a privacy-layer citation) |

Presence table summary (A = stated in what I read; N = not stated in the abstract, NOT proof of absence; "?" = unknown):

| key | route/network-aware client selection | packet-level delivery / retransmission | imputation of missing updates | median/MAD or robust aggregation | participation fairness | DP | pre-registered negatives |
|---|---|---|---|---|---|---|---|
| abdallah | N (FL trains GRU for routing; every IoT node trains) | A only at routing level (OMNeT++, PDR) - not FL-update delivery | N | N | N | A (DP "incorporated into the aggregation process"; certification unknown) | N |
| liu | ? | ? | ? | A (poisoning defence, per digest; mechanism unknown) | ? | ? (privacy-preserving; DP not confirmed) | ? |
| tang | ? | ? | ? | ? | ? | ? | ? |
| haripriya | N | N (latency/"incremental data delivery" in simulation, "paralysis ratio" of edge servers) | N | N (FedProx aggregation) | N | N | N |
| chen | N | N | N | N (multi-center aggregation) | N | N | N |
| bhardwaj | N (FL trains next-hop relay policy) | A at routing level (delivery probability, overhead ratio), not FL updates | N | N | N | privacy-aware claimed, unspecified | N |
| shah | N | N | N | A in the defence sense (zero-knowledge range proofs against Byzantine/label-flip/FANG; not median/MAD) | N | A (helper-added DP noise; guarantee conditional on assumptions) | N |

---

## 1. abdallah2026routing

**(1) Access: ABSTRACT_ONLY.** Routes tried:
1. `doi.org/10.1007/s10878-026-01408-5` via WebFetch: "Unable to verify domain" (tool refused). 
2. `link.springer.com/article/...` via WebFetch: same refusal; via curl: HTTP 200, 324 kB landing page. Contains abstract, full reference list, "Access this article / Buy Now" (paywalled). Metadata tags read.
3. Crossref API (curl): metadata and 37 references, no abstract, licence = Springer TDM only.
4. OpenAlex API: `oa_status: closed`, no repository copy.
5. Web searches (title+author, title keywords): no preprint or alternative copy found.
6. arXiv API title query: nothing. Semantic Scholar: HTTP 429 (rate limited).
The publisher PDF (`link.springer.com/content/pdf/...pdf`) is paywalled, so I did not attempt it.

**Verbatim abstract (Springer HTML):** "The ongoing proliferation of Internet of Things (IoT) networks in smart environments has heightened the demand for efficient, low-latency, and secure communication across dynamic and resource-constrained infrastructures. To address this challenge, we propose a federated edge intelligence framework that integrates Gated Recurrent Unit (GRU)-based traffic prediction with reinforcement learning (RL)-driven routing, enabling fully decentralized and privacy-preserving adaptive communication. Each IoT node independently trains a GRU model using federated learning to forecast short-term congestion and guide an RL agent in real-time route selection, eliminating the need for centralized control. Differential privacy is incorporated into the aggregation process to safeguard user data. The framework was implemented on edge devices and evaluated through OMNeT++ simulations and both real-world and simulated testbeds. Experimental results demonstrate that our decentralized method outperforms centralized GRU, RL-only, and conventional routing baselines, achieving 91.5% prediction accuracy, over 91% packet delivery ratio, and latencies below 75 ms in dense network conditions. [...]"

**(2) Content (abstract only).** Problem: low-latency secure routing in dense IoT. Method: FL-trained GRU congestion forecaster feeding an RL routing agent; DP in aggregation. Threat model: not stated in abstract (title says "secure"). Experiments: OMNeT++ plus real and simulated testbeds; datasets not stated. Contributions: as above. Limitations: not readable. Reference list (37 items) is routing/FL-for-IoT/RL/GRU literature; no robust-aggregation or client-selection-fairness references (Cho et al., Blanchard, etc. absent), which is weak indirect evidence only.

**(3) Presence table:** see summary above. Key point: routing is the *application* of FL; the network is not the thing that decides which FL updates reach the aggregator.

**(4) Sentences citing it.**
- L11: "Routing and scheduling have been combined with FL in several ways \cite{abdallah2026routing,...}". **SUPPORTED** (abstract: FL-trained GRU guides RL routing). Evidence above. Suggested: keep, but make the direction explicit: "FL has been used to learn routing policies (for example a federated GRU congestion predictor with RL routing and differential privacy in aggregation \cite{abdallah2026routing})".

**(5) Closeness: LOW-MEDIUM.** Shares the vocabulary (PDR, delay, DP, federated, routing) but the direction is reversed: they use FL to improve routing; we use route quality to decide which FL clients' updates arrive. No security-of-aggregation threat model visible, no fairness. Cannot exclude that the full text reports PDR per participating node, but nothing in the abstract suggests it.

**(6) Metadata:** Author Wajih Abdallah; title "Federated edge intelligence for secure and adaptive routing in IoT: a GRU-RL based framework"; J. Comb. Optim. 51(2), article 29, March 2026; DOI 10.1007/s10878-026-01408-5. Matches bib (bib title uses "GRU--RL" with en dash; fine). Verified against Springer meta tags and Crossref.

---

## 2. liu2026reliability

**(1) Access: ABSTRACT_ONLY, partial and non-verbatim.** Routes:
1. doi.org via WebFetch: 302 to `linkinghub.elsevier.com/retrieve/pii/S1389128625007741`; following it: tool refused (domain check).
2. curl to ScienceDirect: HTTP 403 (bot protection, not bypassed).
3. Crossref: metadata, 48 references, no abstract.
4. OpenAlex: closed, no abstract, no repository copy.
5. Web search (standard and extended): found the ScienceDirect abstract page; the search tool returned only a paraphrased excerpt. arXiv/CORE/Semantic Scholar: nothing / 429.
No full text.

**What I saw (digest, not verbatim; the search tool paraphrased):** edge nodes differ in reliability, raising collusion risk to privacy; existing edge privacy-preserving FL performs poorly against poisoning attacks, especially on non-IID data; authors design a privacy-preserving, poisoning-defending FL scheme on heterogeneous edge computing with a multi-server architecture, whose secure primitives keep gradients private and make node reliability *configurable*.

**(2) Content.** Problem: collusion among unreliable edge servers/nodes plus poisoning. Method: multi-server secure scheme with secret-sharing-style primitives (reference list includes Stinson, Atici on secret sharing; ShieldFL, LSFL, FLTrust, Krum, Yin et al.). Threat model: colluding edge nodes and poisoning clients. Datasets/experiments/limitations: not read.

**(3) Presence:** see summary. Robust aggregation / poisoning defence is present in some form (mechanism unknown). Anything about packet delivery, missing updates, selection or fairness: unknown.

**(4) Sentences.**
- L9: "reliability-oriented FL \cite{liu2026reliability,tang2026fedcst} (we have not read the latter two beyond their titles and make no statement about their mechanisms)". **PARTLY.** "Reliability" in Liu et al. refers to the trustworthiness (collusion resistance) of edge nodes in a secure aggregation/poisoning-defence scheme, not to delivery or fault reliability. Grouping it under "Fault tolerance and reliability" invites a wrong reading. Also the parenthetical is now outdated for abstract-level reading. Recommended: move it to the privacy/robust-aggregation paragraph: "Liu et al. \cite{liu2026reliability} propose a multi-server secure FL scheme in which the reliability (trustworthiness) of edge nodes is configurable, targeting collusion and poisoning; we have read only the abstract."

**(5) Closeness: LOW-MEDIUM.** Overlaps with (d)/(e) in topic (poisoning defence + privacy at the edge) but a cryptographic multi-server scheme, not a measurement study; no evidence of network-aware selection or delivery modelling. The precise distinction cannot be sharpened without full text.

**(6) Metadata:** Y. Liu, Y. Liang, R. Zhang, Z. Zhou; Computer Networks 274, article 111808; Crossref published January 2026 (DOI contains 2025, online-first); DOI 10.1016/j.comnet.2025.111808. Matches bib (bib "pages = 111808" is an article number; acceptable, or use `number`/`eid`). Year 2026 matches issue date.

---

## 3. tang2026fedcst

**(1) Access: ABSTRACT_ONLY, very partial.** Routes: doi.org (302 to linkinghub S1389128626002215; fetch refused); curl ScienceDirect 403; Crossref (metadata + 49 refs, no abstract); OpenAlex (request failed, no JSON); four web searches (exact title, with/without domain filter, extended mode). The final search returned a paraphrase of two abstract sentences. No full text, no verbatim abstract.

**What I saw (digest):** clustered data in IIoT (similar within a cluster, sharply different across clusters); "reliable" FL framework for a cloud-factory-device three-tier architecture; decoupled FL process with an adaptive weighting strategy against severe heterogeneity. Verify these two statements against the publisher page before relying on them.

**(2) Content.** Problem: data heterogeneity (clustered non-IID) in IIoT. Method: three-tier, decoupled training with adaptive weighting. Threat model, datasets, limitations: unknown. Reference list (49) is mostly IIoT clustering, client selection for non-IID (Li "group client selection", Zhang "Client selection ... non-IID MEC"), Byzantine-robust aggregation in IoT (Ni "rFedFW"), Sybil attacks (Xiao "SCA"). That indicates the authors position it near non-IID clustering and some security; it does not show what FedCST does.

**(3) Presence:** all unknown; "reliable" appears to refer to learning under heterogeneity, not delivery reliability (inference from a digest).

**(4) Sentences.** L9 (same sentence as Liu): **PARTLY / CANNOT_CHECK.** The word "reliability-oriented" is consistent with the title but, on the little I saw, the paper concerns clustered non-IID data. Recommended: "FedCST \cite{tang2026fedcst} targets reliable FL under clustered (non-IID) data in a three-tier industrial IoT architecture; we have read only a fragment of its abstract." Better still, drop it from the "fault tolerance" paragraph and put it with data-heterogeneity work.

**(5) Closeness: LOW** (data heterogeneity focus, no evidence of delivery or fairness elements).

**(6) Metadata:** Y. Tang, L. Ni, J. Zhang, Y. Liang; Computer Networks 280, article 112209, May 2026; DOI 10.1016/j.comnet.2026.112209. Matches bib (Crossref).

---

## 4. haripriya2025fault

**(1) Access: ABSTRACT_ONLY (verbatim).** Routes: doi.org -> `ieeexplore.ieee.org/document/11153937` (fetch refused by tool; WebFetch with different URL returned empty page); curl IEEE stamp/iel8/ielx8/getPDF URLs: HTTP 418 bot block (not bypassed); OpenAlex (gold OA, CC BY, no direct PDF URL, abstract retrieved verbatim); DOAJ API (abstract and metadata; full-text link is the IEEE page); Europe PMC: 0 hits; CORE: 0 hits; fatcat/scholar.archive.org: nothing; Semantic Scholar: 429. The article is legally open (CC BY) but only readable through IEEE's site in a browser.

**Verbatim abstract (OpenAlex/DOAJ):** "...This research addresses these issues through the development of a hierarchical federated learning framework that strategically combines clustered edge servers, the transfer-learning capabilities of pre-trained EfficientNet-B0 and TabNet models, and an enhanced aggregation approach based on FedProx ... A distinctive contribution of this work is the explicit modeling and evaluation of system reliability by defining a 'paralysis ratio' to quantify failed or unresponsive edge servers, and conducting real-time simulation experiments with incremental data delivery. ... maintaining model accuracy above 93% even under up to 40% server paralysis. In comparative benchmarks against the established Multi-Cluster Hierarchical FL (MCHFL) baseline, the framework achieves a 4-6% increase in classification accuracy and a 25% reduction in average communication latency." (OpenAlex text has mojibake quote marks; content as shown.)

**(2) Content.** Problem: fault tolerance and latency of edge FL. Method: clustered edge servers, pre-trained EfficientNet-B0 (images) / TabNet (tabular), FedProx. Threat model: node/server failure ("paralysis"), no adversary stated. Datasets: not named in abstract. Compares with MCHFL (= chen2025hierarchical). Limitations: not readable.

**(3) Presence:** none of our elements confirmed; unresponsive servers is a failure model, not a packet-level delivery model; no imputation (server failures are handled by hierarchy/FedProx); no fairness metric stated.

**(4) Sentences.**
- L9: "FL with edge servers and a pre-trained model for fault tolerance and latency \cite{haripriya2025fault}". **SUPPORTED** by the abstract (title and text). 

**(5) Closeness: MEDIUM-LOW.** Closest on "reliability under unresponsive nodes" and on latency; differs in that failures are at edge-server level in a hierarchical architecture, with no route-scored client selection, no packet-level delivery model, no recovery of missing client updates, no fairness measurement, no adversary. Because only the abstract was read, state the distinction as "not described in the abstract".

**(6) Metadata:** Eight authors R. Haripriya, A. Kumar, M. Pandey, N. Khare, J. Choudhary, D. P. Singh, S. Solanki, A. Haripriya (Crossref) match bib; IEEE Access 13, pp. 158737-158750, 2025; DOI 10.1109/ACCESS.2025.3607738. All match. (Landing page itself not reachable; verified against Crossref/DOAJ.)

---

## 5. chen2025hierarchical

**(1) Access: ABSTRACT_ONLY (verbatim).** Routes: doi.org -> IEEE Xplore document 10483107 (fetch refused/empty); OpenAlex (closed access; abstract verbatim); PubMed 38546988 (WebFetch digest of record, plus citation data); Crossref; web search for an arXiv/author version: nothing; arXiv API title query: nothing. Paywalled; not bypassed.

**Verbatim abstract (OpenAlex), key sentences:** "...we introduce the multicenter HFL (MCHFL) framework. This innovative framework replaces the traditional single central server architecture with a distributed network of robust global aggregation centers located at the edge, inherently enhancing fault tolerance crucial for maintaining operational integrity amidst edge network disruptions. Our comprehensive experiments with the MNIST, FashionMNIST, and CIFAR-10 datasets demonstrate the MCHFL's superior performance. Notably, even under high paralysis ratios of up to 50%, the MCHFL maintains high accuracy levels, with maximum accuracy reductions of only 2.60%, 5.12%, and 16.73% on these datasets, respectively. ... the MCHFL is the first edge multicenter FL framework with theoretical underpinnings."

**(2) Content.** Problem: single-point-of-failure server. Method: multiple edge aggregation centers. Threat model: device/server malfunction ("paralysis"), no adversary. Data: MNIST, FashionMNIST, CIFAR-10. Contribution: architecture plus theory. Limitations: not readable.

**(3) Presence:** none confirmed.

**(4) Sentences.** L9: "hierarchical multicenter FL with fault-tolerance mechanisms \cite{chen2025hierarchical}". **SUPPORTED** (title + abstract).

**(5) Closeness: MEDIUM-LOW.** Closest on failure ("paralysis") robustness, but architecture-level (decentralised aggregation), image benchmarks, no IDS, no client-selection or delivery model, no fairness, no adversary in abstract.

**(6) Metadata:** PubMed: IEEE TNNLS 2025 Jan;36(1):47-61, doi 10.1109/TNNLS.2024.3362974; six authors (Chen, Xu, Xu, Jiang, Tian, Ma) match Crossref and bib. All match.

---

## 6. bhardwaj2024routing

**(1) Access: ABSTRACT_ONLY (verbatim).** Routes: doi.org -> inderscience.com/link.php (fetch refused; curl 403 "Just a moment", Cloudflare, not bypassed); inderscienceonline.com abs URL 403; Crossref (no abstract, 0 refs, metadata); OpenAlex (closed; abstract verbatim); arXiv API: nothing; web searches: nothing beyond metadata.

**Verbatim abstract (OpenAlex):** "Opportunistic IoT networks are the type of wireless network that operate in challenging and dynamic environments where traditional network infrastructure is unreliable... a novel federated learning approach for routing optimisation in opportunistic IoT networks is proposed, where nodes opportunistically select the next-hop relay for message forwarding based on the current network state and local knowledge. Extensive simulation and analysis showcase the effectiveness and practicality of the proposed FLRouter in achieving efficient and privacy-aware routing within opportunistic IoT networks. The proposed approach outperforms existing methods in delivery probability, with gains of up to 16% and 13% as buffer size increases. Additionally, it demonstrates lower overhead ratios, with reductions of up to 42% and 34% compared to existing approaches."

**(2) Content.** Problem: routing in opportunistic IoT networks. Method: FLRouter, FL for next-hop relay choice. Metrics: delivery probability, overhead ratio. Threat model: privacy concern mentioned, no adversary. Datasets/limitations: unknown.

**(3) Presence:** network delivery metrics exist but for routing itself; nothing about FL-update delivery, selection of FL clients, imputation, robust aggregation, fairness, DP.

**(4) Sentences.** L11: "Routing and scheduling have been combined with FL in several ways \cite{...bhardwaj2024routing...}". **SUPPORTED** (FL used to learn routing).

**(5) Closeness: LOW-MEDIUM** (shares delivery-probability vocabulary; opposite direction of dependence).

**(6) Metadata:** Crossref: Bhardwaj, Singh, Gupta, Jadon, Dhurandher; Int. J. Sensor Networks 46(1), pp. 24-38, 2024; DOI 10.1504/IJSNET.2024.141609. Matches bib. Publisher page not reachable.

---

## 7. shah2026trisafe

**(1) Access: ABSTRACT_ONLY (verbatim).** Routes: doi.org -> IEEE Xplore 11550141 (fetch empty/refused); curl stamp.jsp: 418; OpenAlex (gold OA CC BY; abstract verbatim); DOAJ (record exists; link to IEEE); Crossref; Europe PMC/CORE/Semantic Scholar: nothing/429. Legally open but not machine-downloadable from IEEE.

**Verbatim abstract (OpenAlex), key sentences:** "This paper presents TriSAFE, a protocol composition for IoT federated learning with a single coordinating server and three threshold helpers. The server holds no decryption key. TriSAFE combines ... (i) encrypted client updates accompanied by zero-knowledge proofs that each coordinate lies within a bounded range; (ii) ... plaintext-equivalence protocol, PEP ...; (iii) helper-added differential privacy noise applied homomorphically before any decryption ...; and (iv) fixed-cadence batching with calibrated cover traffic to hide participation from passive network observers. Across two IoT intrusion-detection benchmarks (Edge-IIoTset and N-BaIoT) and MNIST, TriSAFE keeps accuracy within 0.1-2.1 percentage points of the no-attack baseline under Byzantine, label-flip, FANG, and time-delay attacks, with attack success rate below 1% ... the end to end overhead is 7-36% ... The design is practical ... under the assumption that the coordinator does not collude with two helpers and that at least two helpers contribute honest DP noise."

**(2) Content.** Problem: simultaneous update confidentiality, update validity and timing/participation privacy in IoT FL. Method: threshold-helper cryptographic protocol with ZK range proofs, PEP binding, DP noise, cover traffic. Threat: Byzantine, label-flip, FANG, time-delay attacks; passive network observer; non-colluding helpers. Data: Edge-IIoTset, N-BaIoT, MNIST. Limitations: stated assumptions (non-collusion, honest DP noise from >=2 helpers).

**(3) Presence:** gateway timing/cover traffic is about hiding participation, not modelling delivery; no selection, imputation, median/MAD, fairness; DP present with conditional guarantee.

**(4) Sentences.** L13: "Other privacy layers use secure aggregation, secure multi-party computation or homomorphic encryption \cite{bonawitz2017secagg,shah2026trisafe,...}". **SUPPORTED** (threshold encryption, homomorphic DP noise, secure aggregation). Optional addition: TriSAFE also evaluates Byzantine robustness on IDS datasets and includes DP; the sentence undersells overlap with (d)/(e) but is not wrong. Suggested: "TriSAFE \cite{shah2026trisafe} composes verifiable secure aggregation, range proofs, helper-added differential-privacy noise and cover traffic, and evaluates it on IoT intrusion-detection data under Byzantine and timing attacks."

**(5) Closeness: MEDIUM-LOW.** Same domain (IoT FL-IDS, attackers, DP) and "participation" appears, but as a privacy property against observers, with cryptographic defences and a (conditional) DP guarantee; our work is a measurement study with no cryptography, a diagnostic non-certified epsilon, and measures participation fairness of selection policies and delivery.

**(6) Metadata:** Crossref: S. H. Shah, I. Walker, M. Borowczak; IEEE Access 14, pp. 89354-89379, 2026; DOI 10.1109/ACCESS.2026.3700048. Matches bib. Title matches.

---

## Overall assessment

Is the gap statement contradicted by any of the 7? **No evidence of contradiction, but the evidence base is abstracts only (and two near-empty fragments).** None of the abstracts describes route-scored FL client selection, a packet-level delivery model for FL updates, imputation of missing updates, median/MAD filtering, participation-fairness measurement, or pre-registered negative results. Because the abstracts are short and none was read in full, "not mentioned in the abstract" must not be rendered as "absent".

Closest in spirit: haripriya2025fault and chen2025hierarchical (unresponsive/paralysed nodes, accuracy under failure ratios), shah2026trisafe (IoT IDS, adversaries, DP, participation as a privacy concern), abdallah2026routing and bhardwaj2024routing (delivery ratio/probability but for FL-trained routing, not for FL updates). liu2026reliability may be closer on (d)/(e) than the current text implies; tang2026fedcst is essentially unknown.

Claims to soften / sentences to change:
1. L9 "reliability-oriented FL \cite{liu2026reliability,tang2026fedcst}": do not group Liu and Tang as fault-tolerance work. Liu's "reliability" is node trust/collusion in a secure poisoning-resistant scheme; Tang concerns clustered non-IID data. Re-word as suggested above and update the parenthetical to "we read only abstract fragments".
2. L5 and L15: the scope note counts and the phrases "In the full texts we could read" / "none models how..." should not be extended to these 7; none of them was read in full. Keep "to the extent visible in abstracts".
3. L18 gap: keep the hedge "within the sources above" and add "(for seven further sources, only abstracts or abstract fragments were available)". Avoid "none of the surveyed works"-style wording for these.
4. L11: for abdallah, bhardwaj make the direction explicit (FL used to learn routing policies), so readers do not infer they study route effects on FL participation.
5. L13: optional neutral expansion for TriSAFE (see above) since it overlaps on IDS data, attackers and DP.
6. Scope note: these 7 are ABSTRACT_ONLY (Liu, Tang fragmentary), so counts "full text of 14 / abstract of 15 / metadata of 6" should list none of these 7 under full text and move abdallah, liu, tang from "bibliographic record only" to "abstract (partial)" if the counts are to be exact.

Recommended action for the authors: a human with a normal browser can legally read haripriya2025fault and shah2026trisafe in full (gold OA, CC BY) at their DOI links; the other five need institutional access or an author-provided accepted manuscript (request via the corresponding authors). Until then keep all statements about these seven at abstract level.

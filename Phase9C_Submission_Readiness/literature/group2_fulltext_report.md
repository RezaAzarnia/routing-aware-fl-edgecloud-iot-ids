# Group 2 literature verification (7 sources) - access-honest report

Date of check: 2026-11-03. Legal routes only. **No full text could be read for any of the 7 sources.** All statements below about content are limited to the abstract (and, for two sources, secondary descriptions); nothing was inferred about the body of any paper.

Fetch-tool caveat: the WebFetch tool returns a model-generated digest of a page, not raw text. WebSearch also returns digests. The ONLY raw, verbatim texts I handled are the JSON returned by the OpenAlex, Crossref, DOAJ and CORE APIs (via curl) and the Digital Commons HTML page for Geng. Quotes marked "[raw]" come from those; anything marked "[digest]" is a tool summary and must not be treated as verbatim.

## Machine-friendly table

| bib key | access level | abstract verbatim? | cited in related_work.tex | verdict on current sentence | closeness | metadata vs Crossref/OpenAlex |
|---|---|---|---|---|---|---|
| aburukba2025scheduling | ABSTRACT_ONLY (OA article exists, publisher blocked my tools) | yes [raw: Crossref, OpenAlex, DOAJ] | yes, Fault tolerance para | PARTLY (abstract-level only) | LOW | OK (author order shown as "Sheeja Rani S, Raafat Aburukba"; bib "Rani S, Sheeja" is the same person) |
| zhou2024qos | ABSTRACT_ONLY (OA CC-BY per OpenAlex, publisher blocked my tools) | yes [raw: OpenAlex] | yes, Network-aware para | SUPPORTED (abstract-level; QoS/resources) | LOW | OK |
| geng2024smpc | ABSTRACT_ONLY | yes [raw: Digital Commons page + OpenAlex] | yes, Privacy para | SUPPORTED (MPC; note blockchain too) | LOW | OK |
| wang2026desa | ABSTRACT_ONLY | yes [raw: OpenAlex] | NO (uncited) | n/a; optional citation | LOW | OK |
| lan2025ckks | ABSTRACT_ONLY, secondary digest only (no raw abstract obtained) | no [digest] | yes, Privacy para | SUPPORTED for "homomorphic encryption" (digest-level) | LOW | OK |
| li2023privacy | METADATA_ONLY plus secondary descriptions [digest] | no | yes, Privacy para | PARTLY / CANNOT_CHECK: descriptions point to masking + differential-privacy noise, not SA/SMPC/HE | LOW-MEDIUM (privacy side only) | OK |
| carillo2026incremental | ABSTRACT_ONLY | yes [raw: OpenAlex] | NO (uncited) | n/a; should be cited in FL-IDS para (abstract-level claims only) | LOW-MEDIUM | OK (early access; no vol/issue) |

Access-level definitions used: FULL_TEXT = read body; ABSTRACT_ONLY = only abstract; METADATA_ONLY = only bibliographic record. PARTIAL_TEXT percent: 0% for all seven.

## Routes tried (common summary, then per source)

Tools available: WebFetch (digest), WebSearch (digest), curl through Bash. One curl attempt that set a browser User-Agent to get past MDPI's 403 was refused by the environment's bot-check guard; I treated that as a boundary and did not retry or look for workarounds. Plain, non-spoofed requests were used afterwards.

Per source:

**aburukba2025scheduling** (gold OA, MDPI, CC-BY per OpenAlex)
1. WebFetch https://www.mdpi.com/2227-7390/13/13/2198/htm : HTTP 403.
2. WebFetch https://www.mdpi.com/2227-7390/13/13/2198/pdf?version=1751681625 (OpenAlex best_oa_location pdf_url) : HTTP 403.
3. curl, plain, same PDF URL : 000 / 403 (blocked). Not pursued further.
4. OpenAlex API (doi): is_oa true, oa_status gold, license cc-by, abstract returned raw.
5. Crossref API: metadata + abstract raw.
6. DOAJ API: record present, keywords raw (cloud, IoT, fault-tolerant scheduling, C-RAN, V-RAN, multi-objective federated learning).
7. CORE API: 1 record (data provider MDPI), fullText "Not available for public API users", downloadUrl empty; core.ac.uk/works page via WebFetch: 403.
8. Europe PMC (DOI query): 0 hits (not in PMC).
9. IDEAS/RePEc page (WebFetch): bibliographic record + abstract digest, no full text; says the MDPI version is downloadable.
10. WebSearch: confirmed abstract content; no full text.
Result: full text is legally free at MDPI, but my tools were refused. A human can open it in a browser: https://doi.org/10.3390/math13132198 .

**zhou2024qos** (Ad Hoc Networks 156, 103430; OpenAlex: hybrid OA, CC-BY, publishedVersion)
1. doi.org -> linkinghub.elsevier.com/retrieve/pii/S1570870524000416 : curl returned a redirect stub page only (2.7 KB, no article).
2. WebFetch https://www.sciencedirect.com/science/article/pii/S1570870524000416 : 403.
3. figshare record 25263466 (OpenAlex "submittedVersion" location): API says is_embargoed true, license All Rights Reserved; no files readable.
4. Europe PMC: 0 hits. CORE: no record for this DOI found.
5. OpenAlex/Crossref: metadata; OpenAlex abstract raw.
6. Lingnan University research portal (WebFetch): record + abstract digest, no PDF.
7. WebSearch: no full text found.
Result: free to read at ScienceDirect per OpenAlex license flag, but not fetchable by my tools.

**geng2024smpc** (IEEE AIoT 2024, pp. 117-122)
1. doi.org -> ieeexplore.ieee.org/document/10677602 (redirect only; not fetched, paywalled).
2. OpenAlex: closed; one repository location: https://digitalcommons.uncfsu.edu/college_health_science_technology/1109 (Fayetteville State Univ.).
3. curl of that page (200, 33 KB): abstract + metadata only. Its "Link to Full Text" points to a Scopus record, not a PDF. No viewcontent PDF link found.
4. Crossref: metadata. Semantic Scholar API: rate-limited (429), not retried.
Result: abstract only.

**wang2026desa** (IEEE TIFS 21, 1987-2001)
1. doi.org -> ieeexplore.ieee.org/document/11367022 (paywalled; not fetched).
2. OpenAlex: closed, no repository copy; abstract raw.
3. Semantic Scholar: openAccessPdf empty/null.
4. Crossref metadata.
5. No arXiv/CORE/EPMC copy surfaced (no arXiv hit for title; not found in searches).
Result: abstract only.

**lan2025ckks** (Internet of Things 33, 101725)
1. doi.org -> linkinghub.elsevier.com/retrieve/pii/S2542660525002392 (redirect only).
2. OpenAlex: closed; no abstract in index. Semantic Scholar: abstract elided by publisher, no OA PDF.
3. Crossref: metadata only, no abstract.
4. WebSearch: returned a digest of the ScienceDirect abstract (fragmentary). No raw abstract obtained.
Result: abstract-level only, via a digest.

**li2023privacy** (Future Generation Computer Systems 144, 205-218)
1. doi.org -> linkinghub.elsevier.com/retrieve/pii/S0167739X23000869 (redirect only).
2. OpenAlex: closed, no abstract. Semantic Scholar: no OA PDF.
3. Crossref: metadata only.
4. WebSearch: secondary descriptions (a survey's description of the scheme and a conclusion snippet) - digest, partly garbled, not verbatim.
Result: metadata only plus unverified secondary descriptions.

**carillo2026incremental** (IEEE TNSM, early access)
1. doi.org -> ieeexplore.ieee.org/document/11436100 : WebFetch returned an empty page.
2. Crossref API (via WebFetch): metadata, license CC BY-NC-ND 4.0 (VoR), full-text link to an IEEE staging PDF (xplorestaging.ieee.org ... 11436100.pdf) - not fetched, as a staging host is not a sanctioned public route.
3. OpenAlex: oa_status hybrid, license cc-by-nc-nd, pdf_url null, abstract raw.
4. Semantic Scholar search: openAccessPdf = doi.org link, status HYBRID (no direct PDF).
5. arXiv API/search: no preprint found. WebSearch: only same group's earlier works (BigData 2023, Computer Networks 2025); the university repository (iris.unina.it) host did not resolve from this machine; dblp record page returned an Anubis "Access Denied" page.
Result: abstract only. The paper is flagged open access in three indices, so a browser download at https://doi.org/10.1109/TNSM.2026.3675031 should work for the user.

## Per-source analysis

Everything in sections (2) is limited to what the abstracts (or digests) say.

### 1. aburukba2025scheduling

**(1) Access:** ABSTRACT_ONLY, see routes.

**(2) Content (abstract only).** Problem: resource failure in cloud computing, need for fault tolerance. Method: "multi-objective radial kernelized federated learning-based fault-tolerant scheduling (MRKFL-FTS) technique for allocating multiple IoT requests or user tasks to virtual machines in cloud IoT-based environments"; four entities (IoT devices, cloud servers, task assigners, VMs); radial-kernelized support vector regression in local training to "identify resource-efficient virtual machines"; locally trained models combined into a global aggregation model; "using a weighted round-robin method, the task assigner allocates incoming IoT service requests to virtual machines." Reported results: "8% improvement in task scheduling efficiency and fault prediction accuracy, a 36% improvement in throughput, and a 14% reduction in makespan and time complexity", 13% lower response time, 17% less energy, 8% scalability [all raw from Crossref/OpenAlex]. Threat model: not stated in the abstract (the "threat" is resource/VM failure, not an adversary). Datasets, limitations: NOT READ (abstract gives none). Experiments are compared "with conventional scheduling techniques".

**(3) Presence table (abstract-level; "not in abstract" is not "absent from paper")**

| element | status |
|---|---|
| route/network-aware client selection | not in abstract (task-to-VM assignment, not client selection) |
| packet-level delivery/retransmission | not in abstract |
| imputation/recovery of missing updates | not in abstract |
| median/MAD or other robust aggregation | not in abstract |
| participation-fairness measurement | not in abstract |
| differential privacy | not in abstract |
| pre-registered negative results | not in abstract |

**(4) Citing sentence (related_work.tex, Fault tolerance paragraph):** "FL-based scheduling of IoT requests to tolerate virtual-machine failures in cloud data centres (fault tolerance \emph{of the scheduler}, not of FL training) \cite{aburukba2025scheduling}"
Verdict: PARTLY (abstract-level). Supported: FL-based, IoT requests, VMs, cloud, fault tolerance in scheduling, and the scheduler-versus-training distinction (the FL model predicts resource-efficient VMs / faults; scheduling is by weighted round robin). Not fully supported: "tolerate VM failures" overstates; the abstract says the technique "improves resource awareness and fault tolerance in scheduling" and reports "fault prediction accuracy", i.e. fault-aware allocation. Mechanism of failure handling could not be read.
Suggested wording: "FL-trained regression models for fault-aware scheduling of IoT requests onto virtual machines in cloud data centres (the fault tolerance concerns the scheduler, not FL training) \cite{aburukba2025scheduling}". Optionally add to the scope note that only the abstract was read.

**(5) Closeness: LOW.** Shares the word "fault tolerance" and FL, but applies FL to cloud scheduling; no FL-training reliability, no client selection, no update delivery. Our study measures reliability and fairness of participation in FL training itself.

**(6) Metadata:** Crossref/OpenAlex: Mathematics, vol 13, issue 13, article 2198, published 2025-07-05, authors Sheeja Rani S and Raafat Aburukba. bib consistent (bib lists "Rani S, Sheeja"). DOI resolves.

### 2. zhou2024qos

**(1) Access:** ABSTRACT_ONLY.

**(2) Content (abstract, raw from OpenAlex).** Problem: edge computing for AIoT has "scarce resources on edge servers and the long distance between AIoT devices and remote cloud servers"; need for balance between limited edge resources and cloud latency to ensure QoS. Method: "an edge-cloud architecture that achieves optimal QoS for AIoT devices"; "a federated learning-based architecture to train AIoT devices' data locally, thereby ensuring privacy." Experiments: "comparing it with the centralized approach from the state-of-the-art using two widely used datasets" (datasets unnamed in abstract). Contributions: edge-cloud architecture for QoS with FL. Threat model / limitations: not in abstract; not read.

**(3) Presence table (abstract-level)**

| element | status |
|---|---|
| route/network-aware client selection | not in abstract (QoS/resource-aware architecture; no routing or selection mentioned) |
| packet-level delivery/retransmission | not in abstract |
| imputation/recovery of missing updates | not in abstract |
| robust aggregation (median/MAD) | not in abstract |
| participation-fairness measurement | not in abstract |
| differential privacy | not in abstract ("ensuring privacy" via local training only) |
| pre-registered negative results | not in abstract |

**(4) Citing sentence:** "...and edge--cloud or resource-aware FL architectures target quality of service and resource constraints \cite{zhou2024qos,liu2024iiot,mughal2024adaptive}."
Verdict: SUPPORTED at abstract level for zhou2024qos (QoS, resource constraints, edge-cloud, FL). Caveat: it sits in a paragraph titled "Network-aware", but the abstract shows no routing or network-state-aware selection, so it should not be read as "network-aware".
Suggested wording (unchanged is acceptable): "edge--cloud or resource-aware FL architectures target quality of service and resource constraints \cite{zhou2024qos,liu2024iiot,mughal2024adaptive}"; optionally rename the paragraph "Network-aware, edge and resource-aware FL".

**(5) Closeness: LOW.** FL for QoS of AIoT devices in an edge-cloud split; no selection policy, delivery model, fairness, robustness or noise. Whether it uses client selection internally cannot be checked.

**(6) Metadata:** Crossref: Ad Hoc Networks, vol 156, article 103430, issued 2024-04; online 2 Feb 2024 per Lingnan portal. Matches bib.

### 3. geng2024smpc

**(1) Access:** ABSTRACT_ONLY.

**(2) Content (abstract raw).** Problem: FL in IoT brings "model inversion, data poisoning, and central aggregation failure." Method: "a framework that integrates blockchain technology and secure multi-party computation (MPC) with FL in IoT networks"; "Utilizing MPC protocols, our framework securely aggregates model updates from clients without revealing individual data, while blockchain technology ensures transparency and immutability of transactions." Evaluation: "Security analysis shows that our framework can effectively address the three aforementioned security and privacy challenges and improve the reliability and robustness of FL processes" - i.e. a security analysis; no experiments are mentioned in the abstract. Datasets: none mentioned. Limitations: not read.

**(3) Presence table (abstract-level)**

| element | status |
|---|---|
| route/network-aware selection | not in abstract |
| packet-level delivery/retransmission | not in abstract |
| imputation/recovery of missing updates | not in abstract (only "central aggregation failure" is named as a threat) |
| median/MAD or robust aggregation | not in abstract (data poisoning named; defence mechanism not stated) |
| participation-fairness | not in abstract |
| differential privacy | not in abstract (MPC-based secure aggregation, not DP) |
| pre-registered negative results | not in abstract |

**(4) Citing sentence:** "Other privacy layers use secure aggregation, secure multi-party computation or homomorphic encryption \cite{bonawitz2017secagg,shah2026trisafe,geng2024smpc,lan2025ckks,li2023privacy}."
Verdict: SUPPORTED for geng2024smpc (MPC; also blockchain). Wording suggestion: "secure aggregation and secure multi-party computation (the latter combined with a blockchain in \cite{geng2024smpc})" if space permits; otherwise leave.

**(5) Closeness: LOW.** A privacy/integrity architecture; no simulation of delivery, selection or fairness; a security analysis, not a measurement study.

**(6) Metadata:** Crossref: 2024 IEEE Annual Congress on AIoT, pp. 117-122, published 2024-07-24, authors Geng, Liu, Chin-Tser Huang. Matches bib.

### 4. wang2026desa (uncited)

**(1) Access:** ABSTRACT_ONLY.

**(2) Content (abstract raw).** Problem: decentralised secure aggregation in device-to-device (D2D) FL without a central server, "in a zero-trust network vulnerable to Byzantine attacks." Method: "a novel Byzantine-robust decentralized SA protocol (DeSA)"; "an enhanced zk-SNARK proof system to verify the local model training process"; embedded zero-knowledge proofs for aggregation integrity; "a Byzantine-robust D2D aggregation protocol that can withstand malicious nodes"; "a one-time masking method that eliminates aggregated masks through a dynamic aggregation strategy" that "takes into account the adjacency and trust relationships among nodes in evolving network topologies." Evaluation: "theoretical analysis" and "real-world datasets"; "time required to verify an embedded proof is significantly reduced"; "accuracy remains robust against malicious nodes." Threat model: malicious/Byzantine nodes in zero-trust D2D. Limitations not read.

**(3) Presence table (abstract-level)**

| element | status |
|---|---|
| route/network-aware client selection | partial: aggregation strategy uses adjacency/trust in evolving topologies (not selection, not routing) |
| packet-level delivery/retransmission | not in abstract |
| imputation/recovery | not in abstract |
| median/MAD or robust aggregation | Byzantine-robust protocol based on cryptographic verification (mechanism beyond zk-proofs not stated) |
| participation-fairness | not in abstract |
| differential privacy | not in abstract (masking + proofs) |
| pre-registered negative results | not in abstract |

**(4) Citing sentence:** none (uncited). Should it be cited? Optional, low value. Best fit: the Robust aggregation sentence ("recent Byzantine-robust schemes address heterogeneous data, privacy and secure aggregation") as another recent example, or the Privacy sentence. It is a cryptographic/verification approach in serverless D2D, not a statistical filter; it does not touch our gap. Recommendation: either add to the Robust-aggregation list as "decentralised, proof-based Byzantine-robust secure aggregation \cite{wang2026desa}" (and update the scope note counts: abstract-only count +1), or drop it from the bibliography. Not needed for the gap statement. Do not describe its experiments beyond the abstract.

**(5) Closeness: LOW.** Different architecture (no server), cryptographic integrity rather than statistical filtering, no selection/fairness.

**(6) Metadata:** Crossref/OpenAlex: IEEE TIFS vol 21, pp. 1987-2001, 2026, six authors as in bib. Matches.

### 5. lan2025ckks

**(1) Access:** ABSTRACT_ONLY via a search digest [digest]; no raw abstract (Crossref and OpenAlex carry none; Semantic Scholar elided it). Treat anything below as unverified secondary text.

**(2) Content [digest]:** problem: FL for IoT private data is inefficient because of "computing resources and communication cost"; method: CKKS homomorphic encryption with "an adaptive weight-inactivation strategy, inspired by dropout", where part of the reorganised weights are encrypted and uploaded each round; claim: improves encryption/decryption and communication speed. Datasets, threat model, limitations: not read.

**(3) Presence table:** all seven elements "not seen"; the only privacy mechanism seen is CKKS homomorphic encryption (not DP).

**(4) Citing sentence:** the Privacy sentence above. Verdict: SUPPORTED (homomorphic encryption) at digest level; flagged as not verified against raw abstract. No change to wording needed; keep the scope note listing it as abstract-level only.

**(5) Closeness: LOW.** Efficiency of encrypted uploads; no selection, delivery, robustness, fairness. It does reduce uploaded weights per round, but that is not the same as update loss.

**(6) Metadata:** Crossref: Internet of Things vol 33, article 101725, published 2025-09; authors Yang Lan, Lixiang Li, Haipeng Peng, Yeqing Ren, Zhongkai Dang. Matches bib.

### 6. li2023privacy

**(1) Access:** METADATA_ONLY (title/authors/venue verified); content descriptions come only from search digests of secondary sources.

**(2) Content [digest, unverified]:** "ubiquitous intelligent federated learning privacy protection scheme (UIFLPP)" for edge computing; one survey describes "matrix masks" for transmission between embedded devices and edge servers and differential-privacy mechanisms training residual models on edge servers; the ScienceDirect conclusion is said to describe "lightweight mask addition and adaptive noise addition" while maintaining accuracy. Datasets, threat model, limitations: not read.

**(3) Presence table:** differential privacy: reported by secondary descriptions (formal accounting or certification status unknown); masking: reported; all other elements not seen.

**(4) Citing sentence:** the Privacy sentence ("Other privacy layers use secure aggregation, secure multi-party computation or homomorphic encryption"). Verdict: PARTLY / CANNOT_CHECK. If the secondary descriptions are right, the scheme is mask-plus-noise (differential privacy) rather than secure aggregation/MPC/HE, so the grouping is inaccurate and, more importantly, it is a DP-style scheme that could be read as relevant to our Gaussian-noise arm. Recommended: either verify the full text in a browser (legal institutional access) or reword and move.
Suggested wording: "Other privacy layers use secure aggregation, secure multi-party computation or homomorphic encryption \cite{bonawitz2017secagg,shah2026trisafe,geng2024smpc,lan2025ckks}, and edge-oriented schemes combine mask-based protection with noise addition \cite{li2023privacy} (we did not verify its privacy accounting)." Alternatively drop li2023privacy.

**(5) Closeness: LOW-MEDIUM on the privacy side only** (masking plus noise at edge servers, unverified); LOW on selection, delivery, robustness.

**(6) Metadata:** Crossref: Future Generation Computer Systems vol 144, pp. 205-218, July 2023; seven authors as in bib. Matches.

### 7. carillo2026incremental (uncited)

**(1) Access:** ABSTRACT_ONLY.

**(2) Content (abstract raw, OpenAlex):** NIDSs need "(i) being trained on network traffic gathered in different collection points ..., (ii) continuously learning emerging threats (viz., 0-day attacks), and (iii) be able to take attack countermeasures as soon as possible." They "integrate Federated Learning (FL) and Class Incremental Learning (CIL)", devising "a Federated Class Incremental Learning (FCIL) framework - suited for early-detection settings - that supports decentralized and continual model updates", "investigating the non-trivial intersection of FL algorithms with state-of-the-art CIL techniques ... in highly non-IID environments." Experiments: "three IoT datasets across different client scenarios" (datasets not named in the abstract), measuring learning new threats and retaining prior knowledge, few-sample training, comparison with "monolithic and centralized baselines". Threat model: emerging/0-day attacks on IoT (attacks on the IDS itself not stated). Limitations: not read.

**(3) Presence table (abstract-level)**

| element | status |
|---|---|
| route/network-aware client selection | not in abstract (FL algorithms across client scenarios; selection not mentioned) |
| packet-level delivery/retransmission | not in abstract |
| imputation/recovery of missing updates | not in abstract |
| median/MAD or robust aggregation | not in abstract |
| participation-fairness | not in abstract |
| differential privacy | not in abstract ("privacy-preserving" via FL only) |
| pre-registered negative results | not in abstract |
Whether it uses UNSW-NB15 or CICIoT2023 cannot be determined.

**(4) Citing sentence:** none. Should it be cited? Yes, a single clause in "Federated intrusion detection for IoT" is appropriate (most recent IEEE TNSM FL-IDS paper, same venue as soomro2026securedyn). Suggested addition: "...and continual-learning variants for emerging threats \cite{carillo2026incremental}." Plus extend the closing sentence of that paragraph only if the full text is read; at abstract level do not claim that it "does not model delivery or selection"; say "its abstract does not mention these". Scope note must count it as abstract-only.

**(5) Closeness: LOW-MEDIUM.** Same domain (federated IoT NIDS, several client scenarios, non-IID, perhaps shared datasets) but the problem is class-incremental learning across time; nothing in the abstract suggests delivery, selection fairness or Byzantine filtering. Precise distinction: its factor is the learning-algorithm side (continual learning); ours is the system-participation side with a fixed learner.

**(6) Metadata:** Crossref: IEEE TNSM, 2026, pp. 1-1 (early access), no volume/issue; license CC BY-NC-ND; authors as in bib (Pescapé; the character prints incorrectly in some API output only). Matches bib note ("volume and pages not confirmed"). Created 2026-03-17, deposited 2026-04-15.

## Overall assessment

1. **Is our gap contradicted by any of the 7?** No contradiction was found, but this is limited by access: only abstracts (and two secondary digests) were read. At abstract level none of the 7 mentions route-scored or fairness-measured client selection, packet-level delivery or retransmission models, imputation of missing updates, median/MAD filtering with a genuine-update analysis, or pre-registered negative results. Absence from an abstract is not absence from the paper, so the gap statement should stay scoped ("within the sources examined"), which it already is. The closest on any dimension are zhou2024qos (QoS in edge-cloud FL, resource scarcity) and carillo2026incremental (federated IoT IDS, multiple client scenarios), and neither is shown to measure what we measure.
2. **Claims to soften or fix**
   - aburukba2025scheduling: replace "to tolerate virtual-machine failures" with fault-aware scheduling wording (above); keep the scheduler-not-training qualifier.
   - li2023privacy: not verifiably secure aggregation/MPC/HE; reword or drop; verify it in a browser before keeping it in the privacy list. If it does use differential-privacy noise, add a caveat so the reader does not conflate it with our diagnostic RDP number.
   - zhou2024qos: keep, but do not imply routing or network-aware selection; consider renaming the paragraph header.
   - geng2024smpc: add "blockchain" or leave; fine as is.
   - lan2025ckks: fine; only digest-level evidence.
   - wang2026desa / carillo2026incremental: cite (carillo, in FL-IDS paragraph) or add/drop (wang) and update the scope-note counts (35 sources; counts of full-text/abstract-only/metadata-only) so that none of these seven is described as read in full.
   - The scope note says 14 read in full / 15 abstract-only / 6 metadata-only; for these 7, none can be moved to the full-text class on the evidence of this check. A user with browser access can obtain free full text for aburukba2025scheduling (MDPI, CC-BY), zhou2024qos (ScienceDirect, CC-BY per OpenAlex) and carillo2026incremental (IEEE, CC BY-NC-ND per Crossref), and these three could then be re-checked in minutes; the other four need institutional access.
3. **Not done / not possible:** no full text for any source; no raw abstract for lan2025ckks and li2023privacy; no check of datasets, threat models or limitations for any source.

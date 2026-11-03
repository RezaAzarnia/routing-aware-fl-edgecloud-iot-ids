# Group 3 literature verification (7 sources) - honest access report

Date of work: 2026-11-03. Verdict up front: **full text could NOT be obtained for any of the 7 sources by legal automated routes.** Every source is therefore at ABSTRACT_ONLY (published abstract, keywords, bibliographic record). Nothing below describes a method, dataset or limitation beyond what the abstract states. Where the abstract is silent, the presence table says "NOT STATED IN ABSTRACT (full text unread)", which is NOT the same as "absent".

Fetch-tool note: WebFetch returns a model-generated digest of the page, not raw text; the abstracts below were cross-checked against raw JSON (DOAJ API, CORE API, OpenAlex, Crossref) fetched with curl, and the quoted abstract sentences are exact text from DOAJ/CORE where marked "verbatim". OpenAlex abstracts for IEEE papers are reconstructed from an inverted index (word order faithful, punctuation approximate) and are labelled "reconstructed".

## Machine-friendly table

| key | access | OA status (OpenAlex/DOAJ) | closeness | related_work.tex cited? | verdict on current sentence | metadata check |
|---|---|---|---|---|---|---|
| albanbay2025ids | ABSTRACT_ONLY | gold OA CC BY (publisher blocks bots: HTTP 403) | LOW-MEDIUM | yes, sentence 2 of "Federated intrusion detection" | PARTLY (abstract-consistent; "none models delivery path/selection" cannot be verified from abstract; abstract mentions only latency and model size, not network delivery) | OK (DOAJ + OpenAlex: vol 14 no 4 art 78, 2025, DOI matches) |
| alghadi2025dos | ABSTRACT_ONLY | diamond OA CC BY-NC-ND (ScienceDirect 403 to scripted access) | LOW | yes, same sentence | PARTLY (same reason) | OK per OpenAlex/DOAJ; vol 3, art 100098, DOI matches; issue month: DOAJ says 2025-12, OpenAlex 2025-05, so year 2025 is safe |
| zhang2026endpca | ABSTRACT_ONLY | closed, no OA copy, no arXiv | LOW | NO (uncited) | n/a; optional | OK (Crossref + OpenAlex: TIFS vol 21, 1438-1453, 2026) |
| zhang2026malicious | ABSTRACT_ONLY | closed | LOW | yes, "recent Byzantine-robust schemes address heterogeneous data, ..." | SUPPORTED at abstract level for "heterogeneous data" | OK (TNSE vol 13, 6027-6040) |
| liu2026anonymous | ABSTRACT_ONLY | closed | LOW | yes, same sentence | SUPPORTED at abstract level for "privacy and secure aggregation" (not heterogeneity) | OK (TDSC vol 23 no 3, 5214-5225; Crossref issue date 2026-05, OpenAlex 2026-01-12 online) |
| shu2026trustworthy | ABSTRACT_ONLY | closed | LOW-MEDIUM (it uses Median among its robust rules) | yes, same sentence | SUPPORTED at abstract level for "privacy and secure aggregation" | OK (IoT-J vol 13 no 7, 12673-12686; Crossref issue date 2026-04-01) |
| s2dfl2026 | ABSTRACT_ONLY | gold OA CC BY-NC-ND (IEEE Xplore returned 418/202 to scripted access) | MEDIUM (only source that couples DP noise, statistical filtering and IoT edge) | NO (uncited) | n/a; recommend adding | OK (Crossref + DOAJ: OJCS vol 7, 914-923, 2026; authors Yang, Chen) |

## Routes tried (all sources)

Common routes, applied to each DOI where relevant:
1. Publisher/DOI landing page (WebFetch and curl). MDPI (`mdpi.com/2224-2708/14/4/78`, `/pdf`, `/htm`): HTTP 403 "Access Denied" (Akamai bot block). Elsevier (`doi.org/10.1016/j.csa.2025.100098` -> linkinghub -> sciencedirect `/pii/S2772918425000153`, `/pdfft`): 403 to scripted access. IEEE Xplore (`document/11503398`, `ielx8/.../11503398.pdf`, `stamp.jsp`): 202 empty, 418 "teapot", i.e. bot-blocked. I did not try to evade these blocks (that would be bypassing access controls even though the two Elsevier/MDPI/IEEE-OJCS papers are OA to human readers).
2. Crossref API (`api.crossref.org/works/<doi>`): metadata only, no abstracts for IEEE, no open full-text links (only a similarity-checking link for EndPCA). MDPI and Elsevier Crossref calls via curl returned non-JSON (not retried).
3. OpenAlex (`api.openalex.org/works/doi:...`): gave `is_oa`, locations, reconstructed abstracts. Closed with no OA location for EndPCA, Zhang-Malicious, Liu-Anonymous, Shu-Trustworthy. Gold/diamond OA with publisher location only for Albanbay, Alghadi, S2D-FL.
4. DOAJ API (`doaj.org/api/search/articles/doi:...`): returned full verbatim abstracts, keywords, affiliations for Albanbay, Alghadi (and S2D-FL). Full text link points back to the publisher (blocked).
5. CORE API (`api.core.ac.uk/v3/search/works/?q=doi:...` and `/v3/outputs/<id>/`): records for Albanbay and Alghadi exist but are DOAJ/MDPI metadata harvests with `fullText: null` and empty `downloadUrl`.
6. Europe PMC REST: 0 hits for `DOI:10.3390/jsan14040078` (not indexed).
7. arXiv API (`arxiv.org/api/query?search_query=ti:...` for EndPCA, HadAGG, "Anonymous and Byzantine-Robust", "Joint Privacy and Byzantine Resilience", S2D-FL): zero entries for all five, so no preprint exists under these titles.
8. Semantic Scholar Graph API: HTTP 429 (rate limited), nothing obtained.
9. Web search (3 queries for the closed IEEE papers): the search engine did not index EndPCA, Liu-Anonymous, Shu-Trustworthy or S2D-FL; for Zhang-Malicious it returned a Beijing Institute of Technology repository page (`pure.bit.edu.cn/en/publications/malicious-or-benign-...`) which gives only the abstract. Not fetched further (repository records of this kind typically carry abstract only; I did not verify whether a PDF is attached).
10. Not attempted: Google Scholar "all versions" (automated access prohibited), ResearchGate/Academia (no way to confirm author-uploaded public PDF from a scripted fetch), Sci-Hub etc. (excluded by instructions).

Net: no legal full-text route succeeded for any source. **Recommended human action (authors, who have institutional or browser access):** open the three OA papers directly in a browser (Albanbay: https://doi.org/10.3390/jsan14040078 ; Alghadi: https://doi.org/10.1016/j.csa.2025.100098 ; S2D-FL: https://doi.org/10.1109/OJCS.2026.3689594) and run the keyword checklist below; they are free to read. The four closed IEEE papers need institutional access or author-requested accepted manuscripts.

Keyword checklist for a human reader: "client selection", "route"/"routing", "packet", "retransmi", "loss"/"dropout"/"straggler", "missing"/"impute", "median"/"MAD", "Gini"/"fairness"/"participation", "epsilon"/"RDP"/"differential privacy", "pre-regist"/"negative result".

---

## 1. albanbay2025ids (ABSTRACT_ONLY)

**(1) Access.** See routes above. Source of text: DOAJ/CORE abstract, verbatim.
**(2) Content (abstract only).**
- Problem: FL-based IDS for IoT; the authors say previous work "primarily focused on maximizing accuracy" and "overlook the computational limitations of IoT hardware and the feasibility of local model deployment" (verbatim).
- Method/experiments: three architectures (DNN, CNN, CNN+BiLSTM) trained "using the CICIoT2023 dataset within a federated learning environment simulating up to 150 IoT devices"; evaluates accuracy, convergence speed, latency and model size over different local data scales; Raspberry Pi 5 deployment tests.
- Results: CNN "~98% accuracy with low latency and a compact model footprint"; CNN+BiLSTM "~99%" at higher computational cost.
- Threat model: none stated in abstract. Limitations: not stated in abstract (full text unread).
**(3) Presence table (abstract-level; full text unread).**

| element | status |
|---|---|
| route/network-aware client selection | NOT STATED IN ABSTRACT |
| packet-level delivery/retransmission | NOT STATED IN ABSTRACT (only inference latency and model size are mentioned, which is compute latency, not network delivery) |
| imputation of missing updates | NOT STATED IN ABSTRACT |
| robust aggregation (median/MAD) | NOT STATED IN ABSTRACT |
| participation fairness | NOT STATED IN ABSTRACT |
| differential privacy | NOT STATED IN ABSTRACT |
| pre-registered negative results | NOT STATED IN ABSTRACT |

**(4) Sentence audit.** Cited only in: "A survey \cite{agrawal2022flids} and several studies apply FL to IoT intrusion detection \cite{albanbay2025ids,alghadi2025dos,peng2025fdids,rahmati2025cybersecurity}". Evidence: abstract confirms FL-based IDS for IoT on CICIoT2023 (a dataset we also use). Verdict **SUPPORTED** for this clause. The following sentence ("In the full texts we could read, these works focus on the detector, the poisoning defence or the privacy layer, and none models how the delivery path or a client-selection policy shapes which updates reach the aggregator") is only abstract-consistent for this source; Albanbay is better described as an empirical model/data-scale study than a "detector, poisoning defence or privacy layer" paper. If the scope note counts it among "full texts we could read", that count must be rechecked (this report could not read it). Suggested wording: "Albanbay et al. \cite{albanbay2025ids} study model choice and local data volume for FL-based IDS on CICIoT2023 with up to 150 simulated devices (from the abstract; we did not read the full text)." and keep the generic claim as "none of the sources we read models..." with the abstract-only sources excluded.
**(5) Closeness: LOW-MEDIUM.** Same dataset (CICIoT2023), simulated many-client FL-IDS. Distinction: it is a scaling/model-selection study of the detector; abstract states no network-delivery model, selection policy or attacker. Caution: "up to 150 devices" shows a larger client count than ours, so we should not claim a larger scale.
**(6) Metadata.** DOAJ and OpenAlex agree with the bib: Journal of Sensor and Actuator Networks, vol 14, issue 4, article 78, July 2025, DOI 10.3390/jsan14040078, 7 authors in the same order. OK.

## 2. alghadi2025dos (ABSTRACT_ONLY)

**(1) Access.** Same as above; abstract verbatim from DOAJ/CORE.
**(2) Content (abstract).** Compares centralized vs FL detection of DoS attacks with RNN, LSTM, GRU, CNN; filter-based feature selection (Variance Threshold, Mutual Information, Chi-square, ANOVA, L1) combined by union plus wrapper RFE; dataset **IoTID20** (not CICIoT2023 or UNSW-NB15); metrics accuracy, precision, recall, F1, ROC-AUC. Best FL: CNN + ANOVA 99.73 percent; best centralized: GRU + MI 99.91 percent. Framing sentence (verbatim): "Federated Learning (FL) offers a privacy-preserving alternative by training models locally and transmitting only the updated model weights to a central server for aggregation." Threat model and limitations: not stated in the abstract.
**(3) Presence table.** All seven elements: NOT STATED IN ABSTRACT. (Abstract is entirely about feature selection and model comparison.)
**(4) Sentence audit.** Same cite group as above. The "FL for IoT intrusion detection" clause is **SUPPORTED**. The "detector, poisoning defence or privacy layer" characterisation fits only loosely (it is a detector/feature-selection study, no poisoning defence in the abstract). Suggested wording: "Al-Ghadi et al. \cite{alghadi2025dos} compare centralised and federated DoS detection on IoTID20 with ensemble feature selection and four deep models (abstract only read)."
**(5) Closeness: LOW.** Detector/feature-selection comparison; abstract has no selection, delivery, robustness or privacy component. Distinction: we do not study the detector architecture or feature selection.
**(6) Metadata.** Cyber Security and Applications, vol 3, article 100098, 2025, DOI 10.1016/j.csa.2025.100098; authors and order match. OpenAlex lists publication 2025-05-01; DOAJ month 12 (probably volume completion). Year 2025 OK.

## 3. zhang2026endpca (ABSTRACT_ONLY)

**(1) Access.** Crossref (metadata, no abstract), OpenAlex (closed, no OA location, reconstructed abstract), arXiv search (none), Semantic Scholar (429), web search (not indexed), IEEE (blocked/paywalled). No full text.
**(2) Content (OpenAlex reconstructed abstract).** Problem: FL vulnerable to "sophisticated poisoning attacks"; existing Byzantine Robust Aggregation Rules (BRARs) "rely on strong assumptions or challenging technical prerequisites". Method: EndPCA, an ensemble defence that uses the entropy weight method to consolidate scores from multiple BRARs into an ensemble trust score; claimed theoretical guarantee "of convergence with bounded error"; empirical outperformance of existing BRARs. Datasets, threat model details, limitations: not in abstract.
**(3) Presence table.** Robust aggregation: PRESENT (ensemble of BRARs, abstract). Route-aware selection, packet-level delivery, imputation, fairness, DP, pre-registered negatives: NOT STATED IN ABSTRACT (and implausible for this topic, but unread).
**(4) Sentence audit.** Currently uncited in related_work.tex (the bib key exists, so BibTeX will ignore it unless cited). Recommendation: either drop it from the bib, or cite it once in "Robust aggregation" as one more ensemble/score-based BRAR line. It does not contradict any claim. Suggested sentence: "Ensemble-style defences combine the scores of several Byzantine-robust rules into one trust score with a convergence guarantee under assumptions \cite{zhang2026endpca}; we use a single classical rule and make no such guarantee." (Wording about "under assumptions" is taken from the abstract's "under practical assumptions"; verify in full text before submission.) Given that it adds little, DROP is also acceptable.
**(5) Closeness: LOW.** Defence algorithm paper; no delivery/participation component stated.
**(6) Metadata.** Crossref and OpenAlex: IEEE TIFS vol 21, pp 1438-1453, 2026, DOI 10.1109/TIFS.2026.3655513, 8 authors matching the bib. OK.

## 4. zhang2026malicious (ABSTRACT_ONLY)

**(1) Access.** OpenAlex (closed), Crossref (metadata), arXiv search for "HadAGG" (0), web search (BIT repository abstract page found, not a full text), IEEE paywall. No full text.
**(2) Content (abstract).** Problem: Byzantine-robust FL in heterogeneous (non-IID) settings; existing defences relying on statistical analysis "struggle to separate benign outliers from malicious updates", hurting generalisation. Method: HadAGG, hybrid anomaly detection and aggregation using cosine similarity and Shapley values (a value-based contribution measure with a multi-objective loss/accuracy utility); instead of discarding suspicious updates it corrects them by gradient projection and aggregates with weights so each update contributes positively. Theoretical analysis plus experiments claimed. Datasets, attack list, limitations: not in abstract.
**(3) Presence table.** Robust aggregation (non-median; similarity plus Shapley): PRESENT. "Recovery"/correction of suspicious updates by projection: PRESENT but this is correction of malicious updates, NOT imputation of missing (undelivered) updates. All other elements: NOT STATED IN ABSTRACT.
**(4) Sentence audit.** Cited in "recent Byzantine-robust schemes address heterogeneous data, privacy and secure aggregation \cite{zhang2026malicious,zhu2026bpflh,liu2026anonymous,shu2026trustworthy}". Evidence: abstract explicitly addresses heterogeneous data. Verdict **SUPPORTED** (for "heterogeneous data"). Preferred more precise attribution: "...address heterogeneous data \cite{zhang2026malicious,zhu2026bpflh}, or privacy and secure aggregation \cite{liu2026anonymous,shu2026trustworthy}" (BPFLH is outside this group and not verified here).
**(5) Closeness: LOW.** It is a new robust aggregator for non-IID data; our paper claims no aggregator novelty. Note a mild overlap: it rescues rather than discards suspicious updates, whereas our MAD filter discards; we should not claim our filter is the only way to handle outliers.
**(6) Metadata.** OpenAlex/Crossref: IEEE TNSE vol 13, pp 6027-6040, 2026, DOI 10.1109/TNSE.2026.3654756, authors match. OK (title uses quotation marks; bib already braces them).

## 5. liu2026anonymous (ABSTRACT_ONLY)

**(1) Access.** OpenAlex (closed, no OA), Crossref (metadata), arXiv (0), web search (not indexed; returned neighbouring SEAR/BREA works, not this paper), IEEE paywall. No full text.
**(2) Content (abstract summary).** Two threats: privacy leakage from shared updates and poisoning by malicious clients. Scheme: (i) a single-masking protocol for privacy and aggregation efficiency; (ii) secure shuffling removing metadata such as source IP and timestamps for client anonymity; (iii) a "baffle" mechanism limiting malicious-update influence. Claims: resists poisoning "even when 50% of fog nodes are contaminated" (OpenAlex summary wording; the exact phrase should be verified), more than 20 percent aggregation-efficiency improvement. Datasets and limitations: not in abstract. The architecture includes fog nodes.
**(3) Presence table.** Robust aggregation ("baffle", unspecified mechanism): PRESENT at abstract level, mechanism unknown. Secure aggregation/masking: PRESENT. DP: NOT STATED IN ABSTRACT (masking and shuffling, not DP). All others: NOT STATED IN ABSTRACT.
**(4) Sentence audit.** Same cite group sentence. Evidence supports "privacy and secure aggregation". It does not support "heterogeneous data" for this paper, so the conjoined list should not attribute heterogeneity to it. Verdict **SUPPORTED** for the privacy/secure-aggregation part, **UNSUPPORTED** for heterogeneity (if the sentence is read as attributing all three to every cited paper). Suggested wording as in item 4.
**(5) Closeness: LOW.** Cryptographic anonymity plus defence; no selection or delivery model, as far as the abstract shows.
**(6) Metadata.** IEEE TDSC vol 23 no 3, pp 5214-5225, 2026, DOI 10.1109/TDSC.2026.3651776, authors match. Date: Crossref 2026-05, OpenAlex first online 2026-01-12; year 2026 OK.

## 6. shu2026trustworthy (ABSTRACT_ONLY)

**(1) Access.** OpenAlex (closed), Crossref (metadata), arXiv (0), web search (not indexed), IEEE paywall. No full text.
**(2) Content (abstract, reconstructed).** Generic FL framework combining robust aggregation with cryptographic privacy via secure two-party computation under a dual-server (two non-colluding servers) architecture; supports Multi-Krum, Median and Mean-based robust rules; experiments "on multiple benchmark datasets" indicate robust-method effectiveness is preserved with acceptable runtime and communication overhead. Threat model implied: adversarial participants plus non-colluding servers; details not in abstract. Limitations: not in abstract.
**(3) Presence table.** Robust aggregation incl. **Median**: PRESENT (abstract). Secure computation (2PC) privacy: PRESENT. DP: NOT STATED IN ABSTRACT. Route/packet/imputation/fairness/pre-registration: NOT STATED IN ABSTRACT.
**(4) Sentence audit.** Same cite group. Evidence supports "privacy and secure aggregation" (secure 2PC) and the robust-aggregation topic; it does not address heterogeneity in the abstract. Verdict **SUPPORTED** (privacy/secure aggregation). Suggested: "Shu et al. \cite{shu2026trustworthy} run Multi-Krum, Median and mean-based robust rules inside a dual-server secure two-party computation" (abstract-level; confirm in full text).
**(5) Closeness: LOW-MEDIUM.** Median-based rule appears, but it is evaluated as an encrypted-computation target, not as a measured effect against delivery/participation. Distinction: we measure the filter's behaviour versus number of genuine updates and participation under lossy delivery; no encrypted aggregation.
**(6) Metadata.** IEEE IoT-J vol 13 no 7, pp 12673-12686, 2026, DOI 10.1109/JIOT.2026.3651363, six authors match. OK.

## 7. s2dfl2026 (ABSTRACT_ONLY)

**(1) Access.** DOAJ API gave the verbatim abstract and keywords (FL, local differential privacy, Byzantine robustness, IoT edge computing, trust management); OpenAlex: gold OA CC BY-NC-ND (published version at IEEE). IEEE Xplore full text blocked to scripted fetch (418/202), so unread. arXiv: none.
**(2) Content (DOAJ abstract, verbatim in part).** Problem: simultaneously achieving "robustness against poisoning attacks, strong local differential privacy (LDP), and communication efficiency under severe resource constraints and non-IID data". Method: hierarchical S2D-FL. Client layer: Sparsity-Guided Adaptive LDP (S-ALDP), "dynamic Top-k sparsification and noise calibration", about 95 percent communication reduction. Edge-cloud layers: Adaptive Sparse Filtering Aggregation (ASF-Agg) "combines instantaneous statistical filtering with long-term reputation tracking" (Long-Term Trust-Aware Reputation Management, LTRM) against Byzantine attacks. Evaluation: "Non-IID industrial IoT and image datasets under strict LDP budgets (e.g., epsilon = 5.0)", up to 82.6 percent accuracy under label-flipping on CIFAR-10, 11.4 percent over the strongest baseline. Authors say "strong empirical privacy and robustness benefits". Threat model: poisoning/Byzantine (label flipping named). Limitations: not in abstract.
**(3) Presence table.** Robust aggregation (statistical filtering plus reputation, details unknown): PRESENT. Differential privacy: PRESENT as LDP with epsilon budgets; whether the epsilon is certified under stated assumptions cannot be determined from the abstract (the abstract itself says "empirical privacy ... benefits"). Trust/reputation-based weighting of clients: PRESENT. Route-aware selection, packet delivery/retransmission, imputation, participation fairness, pre-registered negatives: NOT STATED IN ABSTRACT.
**(4) Sentence audit.** Currently uncited. It is the one source combining DP noise, statistical filtering and IoT edge in a single pipeline, so it deserves a citation, in "Privacy" or "Robust aggregation". Suggested: "Joint robustness and privacy has also been pursued in IoT edge settings, e.g. S2D-FL, which pairs sparsified local-DP noise with statistical filtering and long-term client reputation \cite{s2dfl2026}; we study the interaction with delivery losses and report our RDP epsilon as diagnostic only." After reading the full text, confirm that it does not model unreliable delivery, which this abstract does not mention (so the sentence should not say it "does not").
**(5) Closeness: MEDIUM.** Combines DP noise, statistical filtering and IoT edge. Distinction: new algorithm (sparsified LDP plus reputation) vs our measurement study with no new estimator; our noise is central Gaussian with a diagnostic RDP epsilon, not LDP; we additionally measure delivery models, route-scored selection and participation fairness.
**(6) Metadata.** DOAJ + Crossref + OpenAlex: IEEE Open Journal of the Computer Society, vol 7, pp 914-923, 2026, DOI 10.1109/OJCS.2026.3689594, authors Jing Yang and Yasong Chen (Hanjiang Normal University). Matches bib. OK.

---

## Sentence-correction list (related_work.tex)

1. Sentence 2 of "Federated intrusion detection": "In the full texts we could read, these works focus on the detector, the poisoning defence or the privacy layer, and none models how the delivery path or a client-selection policy shapes which updates reach the aggregator." For albanbay2025ids and alghadi2025dos this report read only abstracts (the scope note and the previous groupA/B reports should be checked to see whether anyone else read their full text; I did not re-read those reports). Recommended: "In the sources we read in full, ... ; for the remainder (including \cite{albanbay2025ids,alghadi2025dos}) the abstracts describe detector design, model scaling or feature selection and mention no delivery model or selection policy."
2. "Robust aggregation" sentence: "recent Byzantine-robust schemes address heterogeneous data, privacy and secure aggregation \cite{zhang2026malicious,zhu2026bpflh,liu2026anonymous,shu2026trustworthy}" is acceptable only as a list of topics across the group. Recommended manuscript-ready: "recent Byzantine-robust schemes address heterogeneous data \cite{zhang2026malicious,zhu2026bpflh} and combine robustness with secure aggregation, anonymity or secure two-party computation \cite{liu2026anonymous,shu2026trustworthy}." Mention that these are abstract-level statements in the scope note.
3. Add (optional) s2dfl2026 in "Privacy" or "Robust aggregation" (wording in section 7). zhang2026endpca: add one short clause or drop from the bib.
4. Scope note: current count "14 full text, 15 abstract only, 6 metadata only" - none of these 7 should be counted as full text on the basis of this report.

## Overall conclusion

**Is our gap statement contradicted by any of these 7?** No. None of the seven abstracts mentions client selection by network quality or route, packet-level delivery or retransmission, imputation of missing updates, participation-fairness measurement or pre-registered negative results, so nothing here contradicts the claim "within the sources above, we did not find a controlled study that measures ..." But absence from an abstract is weak evidence, and for these seven the claim is only abstract-level. S2D-FL (MEDIUM) and Shu et al. (LOW-MEDIUM; uses Median) are the nearest on the robustness/privacy axes; Albanbay is the nearest on dataset (CICIoT2023, up to 150 simulated devices).

**Claims to soften.**
- Any statement that these works "focus on the detector / poisoning defence / privacy layer" and "none models ..." should be limited to "abstracts we read" for these seven.
- Do not attribute "heterogeneous data" to Liu et al. or Shu et al.; do not attribute DP to Liu et al. or Shu et al. (abstracts mention masking/shuffling and secure 2PC, not DP).
- Do not describe S2D-FL's privacy as certified or uncertified; its abstract says "empirical privacy ... benefits" and LDP budgets, details unread.
- Avoid claiming scale advantages: Albanbay et al. simulate up to 150 devices.
- Keep the "not a claim of priority" sentence, and add "limited to the abstracts of seven further sources" to the scope note, or have an author read the three OA papers in a browser (links above) and the four IEEE papers through institutional access before submission.

## Verification status of this report
Facts verified by raw API output: all metadata, DOAJ abstracts (Albanbay, Alghadi, S2D-FL), CORE record existence. Facts from WebFetch digests (OpenAlex-reconstructed IEEE abstracts for EndPCA, Zhang, Liu, Shu): OpenAlex data, summarised by the fetch tool, therefore the Liu "50% of fog nodes" figure and the ">20%" efficiency figure should be confirmed against the IEEE abstract before being quoted. No full text of any of the 7 sources was read; no quotes from full text are given.

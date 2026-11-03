# Bibliography verification report

Method: every entry was looked up in Crossref (api.crossref.org, title query and/or DOI) and, where useful, arXiv/web search. Title, authors, venue, year, volume, issue and page or article number were compared with the .bib entry. All DOIs below are the Crossref-registered DOIs (resolve at https://doi.org/<DOI>).

Limit on the "what it claims" column: Crossref returned no abstracts for these records, and the full texts were not read. The sentences come from the titles, plus abstract snippets from web search for SecureDyn-FL, BPFLH, Carillo et al. and EndPCA. Treat them as title-level; check the full text before citing for a specific claim.

Status counts: VERIFIED 32, CORRECTED 3, UNVERIFIABLE 0.

Common fix: most entries use "and others"; the full author lists are given in verified_references.bib. Listing "and others" is not an error by itself, so those entries stay VERIFIED.

## Part A: the 35 existing entries

| Key | Status | Evidence (DOI) | Correction / note | What it claims (scope for citing) |
|---|---|---|---|---|
| soomro2026securedyn | VERIFIED | 10.1109/TNSM.2025.3647642 (also arXiv 2601.06466) | Authors: Soomro, Khan, Hussain, Iqbal, Khalid, Yu. Vol 23, pp 1742-1765 confirmed. | FL IDS for IoT with temporal gradient auditing (GMM/Mahalanobis) against poisoning, additive-ElGamal secure aggregation with pruning/quantization, and personalization for non-IID data; evaluated on N-BaIoT and TON_IoT with up to 50% adversarial clients. Supports poisoning-robustness, privacy and IDS claims; no routing. |
| carillo2026incremental | CORRECTED | 10.1109/TNSM.2026.3675031 | Authors: Carillo, Cerasuolo, Bovenzi, Ciuonzo, Pescape. Crossref lists it as 2026 early access with page "1-1". The bib's vol 23 and pp 3865-3880 could not be confirmed, so they were dropped. Note: a different arXiv paper (2603.10776, Rehman et al., CICIoMT2024) has a similar topic; do not mix them up. | Federated plus incremental (class-incremental) NIDS for IoT emerging threats. Supports FL-IDS and evolving-threat claims; not routing, DP or Byzantine robustness. |
| latif2026multimodel | VERIFIED | 10.3390/s26103198 | Authors: Shahid Latif, Djamel Djenouri. Sensors 26(10):3198 confirmed. | Hierarchical FL IDS using several models with adaptive aggregation for robust IoT intrusion detection. Supports hierarchical FL-IDS; robustness scope not checked. |
| s2dfl2026 | VERIFIED | 10.1109/OJCS.2026.3689594 | Matches (Yang, Chen; OJCS vol 7, pp 914-923). | Sparsity-guided, trust-aware FL aiming at joint robustness and privacy in IoT edge computing. Supports a joint privacy-plus-robustness claim at title level. |
| shu2026trustworthy | VERIFIED | 10.1109/JIOT.2026.3651363 | Authors: Shu, Hu, Wang, He, Lu, Tian. IoT-J 13(7):12673-12686 confirmed. | FL framework combining privacy protection with Byzantine resilience. Supports privacy plus Byzantine claims. |
| liu2026anonymous | VERIFIED | 10.1109/TDSC.2026.3651776 | Authors: Liu, Zhang, Wu, Cao, Han, Tian. TDSC 23(3):5214-5225 confirmed. | Anonymous, Byzantine-robust FL with secure and efficient aggregation. Supports Byzantine robustness with secure aggregation. |
| zhu2026bpflh | VERIFIED | 10.1109/TDSC.2026.3661522 | Authors: Zhu, Shen, Liu, Qin, Ma. TDSC 23(3):6103-6118 confirmed. | Byzantine-robust FL on non-IID data using Bray-Curtis dissimilarity for detection, with CKKS homomorphic encryption protecting gradients. Supports Byzantine robustness with heterogeneity and HE privacy; not DP. |
| zhang2026endpca | VERIFIED | 10.1109/TIFS.2026.3655513 | Authors: Zhang, Hu, Cao, Sajjanhar, Yang, Hassan, Jin, Li. TIFS 21:1438-1453 confirmed. | Ensemble defense with provably convergent aggregation against poisoning in FL. Supports poisoning robustness with a convergence guarantee. |
| zhang2026malicious | VERIFIED | 10.1109/TNSE.2026.3654756 | Authors: Zhang, Wang, Li, Gai, Wang. TNSE 13:6027-6040 confirmed. | Byzantine-robust aggregation under heterogeneous data that tries to retain useful contribution from suspicious updates. Supports Byzantine robustness with non-IID data. |
| shah2026trisafe | VERIFIED | 10.1109/ACCESS.2026.3700048 | Authors: Shah, Walker, Borowczak. IEEE Access 14:89354-89379 confirmed. | Verifiable secure aggregation with DP and timing defenses for gateway-assisted IoT FL. Supports secure aggregation plus DP in a gateway/edge topology. |
| wang2026desa | VERIFIED | 10.1109/TIFS.2026.3658996 | Authors: Wang, Lu, Li, Wang, Gai, Chen. TIFS 21:1987-2001 confirmed. | Decentralized (server-free) secure aggregation for FL in zero-trust D2D networks. Supports secure aggregation without a central server. |
| tang2026fedcst | VERIFIED | 10.1016/j.comnet.2026.112209 | Authors: Tang, Ni, Zhang, Liang. Comput. Netw. 280:112209 confirmed. | Reliable FL under clustered data distribution in IIoT. Supports reliability under heterogeneity, not security. |
| abdallah2026routing | CORRECTED | 10.1007/s10878-026-01408-5 | Author: Wajih Abdallah. J Comb Optim 51(2), article number 29. The bib's "pp 1-28" is wrong. | Federated edge intelligence with a GRU plus reinforcement-learning routing framework for secure, adaptive IoT routing. Directly supports FL-for-routing; abstract not read. |
| zhang2026adaptive | VERIFIED | 10.1038/s41598-026-41074-5 | Authors: Y. Zhang, S. Zhang, S. Li, B. Yang, P. Chen. Sci Rep 16(1), article 12246 confirmed. | Adaptive routing protocol for large-scale power IoT using edge computing and FL. Supports FL-assisted routing. |
| alanazi2026edgeguard | VERIFIED | 10.3390/s26061989 | Authors: Abdulaziz G. Alanazi, Haifa A. Alanazi. Sensors 26(6):1989 confirmed. | Zero-trust, load-aware federated scheduling for secure, low-latency IoT edge networks. Supports load-aware scheduling plus security. |
| almeida2025modular | VERIFIED | 10.3390/s25123812 | Authors: Almeida, Teixeira, Baldoni, Antunes, Aguiar. Sensors 25(12):3812 confirmed. | Modular, resilient FL architecture for dynamic edge environments. Supports resilience to a dynamic edge. |
| aburukba2025scheduling | CORRECTED | 10.3390/math13132198 | Author is "Sheeja Rani S" and Raafat Aburukba. Bib "S, Sheeja Rani" is a mangled name; the BibTeX author is now `Rani S, Sheeja and Aburukba, Raafat`. | FL-driven scheduling of IoT requests for fault tolerance in cloud data centers. Supports fault-tolerant scheduling, not FL robustness to malicious clients. |
| albanbay2025ids | VERIFIED | 10.3390/jsan14040078 | Seven authors (Albanbay et al.). JSAN 14(4):78 confirmed. | Evaluates FL-based intrusion detection in IoT and the effect of data scaling. Supports FL-IDS performance evaluation. |
| alghadi2025dos | VERIFIED | 10.1016/j.csa.2025.100098 | Authors: Al-Ghadi, Manickam, Widia, Wulandari, Karuppayah. Cyber Secur. Appl. 3:100098 confirmed. | FL for DoS detection in IoT using ensemble feature selection and deep models. Supports FL-IDS for DoS. |
| chen2025hierarchical | VERIFIED | 10.1109/TNNLS.2024.3362974 | Authors: X. Chen, Xu, Xu, Jiang, Tian, Ma. TNNLS 36(1):47-61 confirmed. | Multicenter hierarchical FL with fault-tolerance mechanisms for resilient edge networks. Supports fault tolerance (node failure) in hierarchical FL. |
| geng2024smpc | VERIFIED | 10.1109/AIoT63253.2024.00032 | Authors: Geng, Liu, Huang. pp 117-122 confirmed. | Privacy-preserving FL for IoT based on secure multi-party computation. Supports SMPC-based privacy. |
| bhardwaj2024routing | VERIFIED | 10.1504/IJSNET.2024.141609 | Authors: Bhardwaj, Singh, Gupta, Jadon, Dhurandher. IJSNET 46(1):24-38 confirmed. (A duplicate record, 10.1504/IJSNET.2024.10064733, is the in-press version.) | FL approach for routing optimisation in opportunistic IoT networks. Supports FL-for-routing. |
| haripriya2025fault | VERIFIED | 10.1109/ACCESS.2025.3607738 | Authors: Haripriya, Kumar, Pandey, Khare, Choudhary, Singh, Solanki, Haripriya. IEEE Access 13:158737-158750 confirmed. | Fault tolerance and latency optimization of FL via edge servers and a pre-trained model. Supports fault tolerance and latency. |
| liu2026reliability | VERIFIED | 10.1016/j.comnet.2025.111808 | Authors: Y. Liu, Liang, Zhang, Zhou. Comput. Netw. 274:111808 confirmed (year 2026 per Crossref). | Secure FL with configurable reliability in heterogeneous edge computing. Supports reliability plus security. |
| mughal2024adaptive | VERIFIED | 10.1038/s41598-024-78239-z | Seven authors (Mughal, He, Das, Dharejo, Zhu, Khan, Alzahrani). Sci Rep 14(1), article 28746 confirmed. | Adaptive FL for resource-constrained IoT with edge intelligence and multi-edge clustering. Supports resource-aware or clustered edge FL. |
| liu2024iiot | VERIFIED | 10.3390/s24134182 | Matches. | FL-oriented edge computing framework for IIoT. Supports edge-FL architecture. |
| zhou2024qos | VERIFIED | 10.1016/j.adhoc.2024.103430 | Matches. | FL in an edge-cloud architecture to improve quality of service. Supports edge-cloud FL and QoS. |
| lan2025ckks | VERIFIED | 10.1016/j.iot.2025.101725 | Authors: Lan, Li, Peng, Ren, Dang. IoT 33:101725 confirmed. | Adaptive FL using CKKS homomorphic encryption for IoT data processing. Supports HE-based privacy; not DP. |
| peng2025fdids | VERIFIED | 10.3390/s25144309 | Matches. | FL with knowledge distillation for IDS in non-IID IoT. Supports FL-IDS under heterogeneity. |
| wang2024trust | VERIFIED | 10.1007/s11227-024-06715-4 | Authors: Wang, Li, Zuo. J Supercomput 81, article 232, published online 3 Dec 2024. The bib mixes 2024 (key) and 2025 (year); both are defensible. | Trust management for IoT devices using FL and blockchain. Supports trust or blockchain claims; not aggregation robustness. |
| rahmati2025cybersecurity | VERIFIED | 10.3390/informatics12030062 | Matches. | FL cybersecurity framework for IoT with privacy preservation and real-time threat detection. Supports FL-IDS with privacy. |
| li2023privacy | VERIFIED | 10.1016/j.future.2023.03.010 | Authors: Li, Lai, Wang, Li, Vijayakumar, Gupta, Alhalabi. FGCS 144:205-218 confirmed. | Privacy-preserving FL scheme under edge computing. Supports edge privacy-preserving FL. |
| bayat2025qlearning | VERIFIED | 10.1038/s41598-025-24510-w | Authors: Bayat, Jamali, Abbasi, Anari, Akbarpour. Sci Rep 15(1), article 39153 confirmed. | Dynamic Q-learning plus blockchain for secure IoT data sharing at the edge (a Q-learning and blockchain paper, not FL per the title). Cite only for RL or blockchain data sharing; it is weak support for FL claims. |
| albogami2025deepfl | VERIFIED | 10.1038/s41598-025-88163-5 | Sole author Nasser Nammas Albogami. Sci Rep 15(1), article 4041 confirmed. | Deep FL model for IoT-enabled edge security. Supports FL-based edge security at a general level. |
| padmavathi2025trust | VERIFIED | 10.1038/s41598-025-19712-1 | Authors: Padmavathi, Saminathan. Sci Rep 15(1), article 35832 confirmed. | Federated edge intelligence with trust-based access control. Supports trust/access-control claims. |

Notes on the audit:
- No entry looked hallucinated; every key resolved to a real Crossref record with matching title and venue.
- Citing risk: the 2026 entries are very recent. Several (carillo, abdallah) are early access or lack final pagination.
- Entries that do not support FL robustness or routing claims: tang2026fedcst (reliability only), wang2024trust (blockchain trust), bayat2025qlearning (no FL in title).

## Part B: foundational references (all in verified_references.bib)

| Key | Check | DOI / URL | Note |
|---|---|---|---|
| mcmahan2017fedavg | arXiv 1602.05629 confirmed; AISTATS 2017, PMLR 54 | 10.48550/arXiv.1602.05629 | No publisher DOI exists. Pages 1273-1282 are from the PMLR record (from memory, not fetched). |
| blanchard2017krum | arXiv 1703.02757 confirmed | 10.48550/arXiv.1703.02757 | NeurIPS 30 title is "Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent"; the arXiv title differs ("Byzantine-Tolerant Machine Learning"). Pages 119-129 from memory. |
| yin2018byzantine | arXiv 1803.01498 confirmed | 10.48550/arXiv.1803.01498 | ICML 2018, PMLR 80:5650-5659 (pages from memory). This paper covers coordinate-wise median and trimmed mean. |
| fang2020local | arXiv 1911.11815 confirmed | 10.48550/arXiv.1911.11815 | USENIX Security 2020; pages 1605-1622 from memory. |
| mironov2017renyi | Crossref confirmed | 10.1109/CSF.2017.11 | pp 263-275, Aug 2017. |
| zhu2019poisson | PMLR v97 page fetched | https://proceedings.mlr.press/v97/zhu19c.html | pp 7634-7642 confirmed. The PMLR title is misspelled "Poission". No DOI found. Authors Yuqing Zhu and Yu-Xiang Wang are from memory (not shown in the page fetch). Related: Wang, Balle, Kasiviswanathan, "Subsampled Renyi DP and Analytical Moments Accountant" (10.29012/jpc.723). |
| abadi2016dpsgd | Crossref confirmed | 10.1145/2976749.2978318 | pp 308-318. |
| mcmahan2018dprnn | arXiv 1710.06963 confirmed | 10.48550/arXiv.1710.06963 | ICLR 2018. This is the DP-FedAvg paper. |
| bonawitz2017secagg | Crossref confirmed | 10.1145/3133956.3133982 | pp 1175-1191. Ninth author Karn Seth added from memory. |
| hsu2019measuring | arXiv 1909.06335 confirmed | 10.48550/arXiv.1909.06335 | arXiv only. Introduces the Dirichlet partition and FedAvgM server momentum. |
| reddi2021adaptive | arXiv 2003.00295 confirmed | 10.48550/arXiv.2003.00295 | ICLR 2021. |
| moustafa2015unsw | Crossref confirmed | 10.1109/MilCIS.2015.7348942 | pp 1-6. |
| neto2023ciciot | Crossref confirmed | 10.3390/s23135941 | Sensors 23(13):5941. |
| rousseeuw1993mad | Crossref confirmed | 10.1080/01621459.1993.10476408 | JASA 88(424):1273-1283. |
| agrawal2022flids | Crossref confirmed | 10.1016/j.comcom.2022.09.012 | FL-for-IDS survey (Comput. Commun. 195:346-361). Ninth author Gadekallu added from memory. A second FL-IDS survey: Khraisat et al., ACM Comput. Surv. 57(1), 10.1145/3687124 (not in the bib file). |
| cho2020clientselection | arXiv 2010.01243 confirmed | 10.48550/arXiv.2010.01243 | Power-of-choice. The AISTATS 2022 version has a different title; it was not verified and is not included. |

Sign-flipping attacks: no single canonical reference was verified. Fang 2020 and Yin 2018 are verified and can motivate sign-flip and Byzantine attack models; do not attribute "sign-flipping" to a specific paper without finding one.

Details marked "from memory" were not confirmed against a fetched record and should be checked before submission.

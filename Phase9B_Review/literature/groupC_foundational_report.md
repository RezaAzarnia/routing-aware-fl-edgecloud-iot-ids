# Group C foundational references: verification report

Method: publisher/proceedings pages (PMLR, USENIX, NeurIPS), Crossref API (publisher-deposited metadata), arXiv abs pages, and text extracted from the arXiv/USENIX PDFs. Items not confirmed from a fetched page are marked UNCONFIRMED.

## Per-key table

| Key | Status | Authoritative source | Notes / corrections |
|---|---|---|---|
| mcmahan2017fedavg | OK | https://proceedings.mlr.press/v54/mcmahan17a.html | AISTATS 2017, PMLR 54, pp. 1273-1282, 5 authors confirmed. Page lists no DOI (arXiv DOI in bib acceptable). |
| blanchard2017krum | CORRECT (minor) | https://papers.nips.cc/paper/2017/hash/f4b9ec30ad9f68f89b29639786cb62ef-Abstract.html ; https://arxiv.org/abs/1703.02757 | Authors/title/venue match. NeurIPS title "Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent"; arXiv (v1 only) title "Byzantine-Tolerant Machine Learning": mismatch confirmed; bib correctly uses the NeurIPS title. NeurIPS page shows NO pages; 119-129 confirmed only by a secondary record (IP Paris portal, via search). Replaced the arXiv DOI (which belongs to the preprint) with the NeurIPS url. |
| yin2018byzantine | OK | https://proceedings.mlr.press/v80/yin18a.html | ICML 2018, PMLR 80, pp. 5650-5659, 4 authors confirmed. |
| fang2020local | CORRECT (minor) | https://www.usenix.org/conference/usenixsecurity20/presentation/fang | pp. 1605-1622 confirmed; 29th USENIX Security 2020. Page lists no DOI; arXiv DOI (1911.11815) is the preprint, so replaced by url, added publisher/ISBN. |
| mironov2017renyi | OK | Crossref 10.1109/CSF.2017.11 | CSF 2017, pp. 263-275. |
| zhu2019poisson | OK | https://proceedings.mlr.press/v97/zhu19c.html | ICML 2019, PMLR 97, pp. 7634-7642; authors exactly Yuqing Zhu and Yu-Xiang Wang (two). PMLR title spelled "Poission" (already noted in bib). |
| abadi2016dpsgd | OK | Crossref 10.1145/2976749.2978318 | 7 authors, pp. 308-318. |
| mcmahan2018dprnn | OK (venue via arXiv only) | https://arxiv.org/abs/1710.06963 | arXiv comment "Camera-ready ICLR 2018 version". OpenReview page blocked by bot check, so the ICLR record itself is UNCONFIRMED. |
| bonawitz2017secagg | OK | Crossref 10.1145/3133956.3133982 | 9 authors; 9th = Karn Seth, order matches bib. pp. 1175-1191. (dl.acm.org blocked; Crossref used.) |
| hsu2019measuring | OK | arXiv 1909.06335 | arXiv-only preprint; no peer-reviewed venue found/verified. |
| reddi2021adaptive | OK | arXiv 2003.00295 (PDF header "Published as a conference paper at ICLR 2021") | OpenReview not fetched. |
| moustafa2015unsw | OK | Crossref 10.1109/MilCIS.2015.7348942 | MilCIS 2015, pp. 1-6. |
| neto2023ciciot | OK | Crossref 10.3390/s23135941 | Sensors 23(13), 5941; 6 authors match. |
| rousseeuw1993mad | OK | Crossref 10.1080/01621459.1993.10476408 | JASA 88(424), 1273-1283. |
| agrawal2022flids | OK | Crossref 10.1016/j.comcom.2022.09.012 | 9 authors, 9th = Thippa Reddy Gadekallu, order matches. Comput. Commun. 195, 346-361. Publisher title uses lowercase "intrusion detection system"; harmless. |
| cho2020clientselection | CORRECT | https://arxiv.org/abs/2010.01243 ; https://proceedings.mlr.press/v151/jee-cho22a.html | arXiv: v1 only (3 Oct 2020), title as in bib. AISTATS 2022 paper (PMLR 151, pp. 10351-10375) is titled "Towards Understanding Biased Client Selection in Federated Learning", same 3 authors. Recommend citing the peer-reviewed version as key cho2022biased (in corrected .bib). The old note "not verified here" can be dropped. |

## Claim verdicts

(a) Yin et al. cover coordinate-wise median and trimmed mean: SUPPORTED (abstract, Definition 1, Algorithm 1 Options I/II).

(b) Fang/Yin as motivation for a sign-flipping / scaled-negative-update attack: NOT DIRECTLY SUPPORTED (full text searched).
- Fang et al.: evaluated attacks are Gaussian, label flipping, and their partial/full-knowledge local model poisoning attacks. The full-knowledge attack aims to deviate each global parameter "towards the inverse of the direction along which the global model parameter would change without attacks" (per-coordinate direction s_j = +/-1, crafted values relative to benign min/max). Conceptually closest (inverse-direction attack) but it is an optimisation-derived crafted attack, not a plain sign flip or a scaled negative of the client's own update. The terms sign-flip/scaling do not appear as attacks.
- Yin et al.: Byzantine machines are simulated only by label flipping (y -> 9-y) and uniformly random labels; the paper explicitly says they do not "simply add extreme values in the features or gradients". No sign-flip.
- Safe wording: Fang for the inverse-direction untargeted model-poisoning threat; Yin for the arbitrary-update Byzantine model; define sign-flip/scaling as the authors' own attack, or cite a source that defines it (none verified here).

(c) Hsu et al. 2019 introduce Dirichlet partition and FedAvgM: SUPPORTED. Text: per-client class distribution q ~ Dir(alpha p), used to synthesise non-identical data; Sec. 4.2 "We term this approach FedAvgM (Federated Averaging with Server Momentum)". Caveat: arXiv preprint only.

(d) Reddi et al. cover server optimizers incl. momentum: SUPPORTED with nuance. FedOpt with FedAdagrad/FedYogi/FedAdam; FedAvgM is a baseline (server momentum 0.9) but attributed to Hsu et al. (2019). Cite Hsu for FedAvgM itself.

(e) Mironov and Zhu & Wang for an RDP accountant with Poisson subsampling: SUPPORTED (RDP definition/composition; RDP for Poisson-subsampled mechanisms, title/venue confirmed; theorem details not read). Possible addition, unverified by me: Mironov, Talwar, Zhang 2019, "Renyi Differential Privacy of the Sampled Gaussian Mechanism", the usual reference for sampled Gaussian.

(f) Rousseeuw & Croux 1993 for MAD and 1.4826: PARTIALLY CONFIRMED. Bibliographic data confirmed. The paper proposes Sn and Qn as alternatives to the MAD and discusses MAD scaling; secondary sources (SAS docs, R package) tie the 1.4826 Gaussian-consistency constant to the scaled MAD, but I could not read the paper, so the 1.4826 attribution to this paper is UNCONFIRMED. The constant is 1/Phi^-1(0.75) = 1.4826 and can be stated as a derivation.

(g) Cho et al. relate client selection to bias/participation: SUPPORTED, strongest for the AISTATS 2022 version (abstract: biased client selection affects convergence; Power-of-Choice trades convergence speed against solution bias).

(h) Agrawal et al. is a survey of FL for IDS: SUPPORTED (arXiv 2106.09527 abstract: "extensive and exhaustive review on the use of FL in intrusion detection system", seen via search snippet; Elsevier page returned 403/redirect).

## Krum, Yin, Fang: IDS or generic ML?
- Krum: generic distributed SGD. The fetched arXiv v1 (16 pages) is theory only (Sections 1-6, no experiments). Experiments in the NeurIPS version were not verified.
- Yin: generic; MNIST with logistic regression and CNN.
- Fang: generic; MNIST, Fashion-MNIST, CH-MNIST, Breast Cancer Wisconsin (Diagnostic). IoT only mentioned as an example device type.
None evaluates on IDS data.

## Confirmed only by weak sources
Krum pp. 119-129 (secondary); McMahan 2018 ICLR (arXiv comment); Reddi ICLR 2021 (PDF header).

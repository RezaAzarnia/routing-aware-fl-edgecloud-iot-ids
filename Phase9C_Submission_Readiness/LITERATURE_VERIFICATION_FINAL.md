# Literature verification: final status after Phase 9C

Reports: Phase 9B `Phase9B_Review/literature/group{A,B,C}_*`; Phase 9C `literature/group{1,2,3}_fulltext_report.md` (the 21 sources not previously read in full). Three delegated reviewers tried at least four legal routes per source (publisher/DOI pages, Crossref, OpenAlex, DOAJ, CORE, Europe PMC, arXiv, Semantic Scholar, repositories). Publisher sites (MDPI, ScienceDirect, IEEE Xplore, Springer, Inderscience) refused scripted access (HTTP 403/418/429); that protection was not evaded and no pirate source was used. **Result: none of the 21 could be obtained in full by legal automated means.** The Phase 9C review therefore improved the *abstract-level* evidence and corrected sentences, but **M1 (full-text verification) is NOT closed**; it requires the authors' browser or institutional access.

## Access achieved for the 35 application-level sources (after Phase 9C)
| Level | Count | Sources |
|---|---|---|
| Full or partial full text (incl. preprints/accepted manuscripts) | 14 | soomro2026securedyn, latif2026multimodel, peng2025fdids, rahmati2025cybersecurity (arXiv v1), albogami2025deepfl, zhu2026bpflh, almeida2025modular, alanazi2026edgeguard, zhang2026adaptive, liu2024iiot, mughal2024adaptive, padmavathi2025trust, wang2024trust (preprint), bayat2025qlearning (55%) |
| Abstract or abstract fragment | 20 | haripriya2025fault, chen2025hierarchical, bhardwaj2024routing, shah2026trisafe, abdallah2026routing (verbatim abstract), liu2026reliability (fragment), tang2026fedcst (fragment), aburukba2025scheduling, zhou2024qos, geng2024smpc, wang2026desa, lan2025ckks (digest), carillo2026incremental, albanbay2025ids, alghadi2025dos, zhang2026endpca, zhang2026malicious, liu2026anonymous, shu2026trustworthy, s2dfl2026 |
| Bibliographic record only | 1 | li2023privacy |
Of the 35, **7 were dropped** from the bibliography as unneeded or unsupportable (carillo2026incremental, zhang2026endpca, wang2026desa, wang2024trust, bayat2025qlearning, padmavathi2025trust, and li2023privacy, whose mask/noise mechanism could not be verified). **28 application-level sources remain cited**: **11 read in full or in part** (soomro, latif, peng, rahmati, albogami, zhu, almeida, alanazi, zhang2026adaptive, liu2024iiot, mughal) and **17 at abstract level** (haripriya, chen, bhardwaj, shah, abdallah, liu2026reliability, tang, aburukba, zhou, geng, lan, albanbay, alghadi, zhang2026malicious, liu2026anonymous, shu, s2dfl); none is cited on a record-only basis. The 16 foundational entries are verified separately (Group C). Total bibliography: 44 entries, all cited (`BIBLIOGRAPHY_AUDIT.md`).

## Corrections applied to the manuscript text (related_work.tex)
1. Scope note: counts restated (28 cited application-level sources: 11 full/partial text, 17 abstract level); statements about abstract-only sources are tagged "(abstract level)".
2. IDS paragraph: albanbay/alghadi are not claimed to be poisoning/privacy papers; "survey" applies only to `agrawal2022flids`; `albogami2025deepfl` (full text read) cited.
3. Robust aggregation: heterogeneity attributed only to zhang2026malicious/zhu2026bpflh; liu2026anonymous/shu2026trustworthy described as secure-aggregation/2PC; s2dfl2026 added with "abstract level" and without a privacy-certification statement.
4. Fault tolerance: aburukba reworded (fault tolerance of a scheduler, not of FL training); liu2026reliability and tang2026fedcst moved out of the fault-tolerance list and described as "reliability" in other senses (abstract fragments only).
5. Network-aware paragraph renamed "Network-aware, edge and resource-aware FL"; routing studies described as FL used to *learn* routing (opposite dependence); the unverifiable clause "far simpler than these mechanisms" removed (Phase 9B).
6. Privacy: li2023privacy removed; geng2024smpc described as SMPC with a blockchain; shah2026trisafe's overlap (Byzantine attacks on IDS data with DP) stated openly.
7. Gap statement: states 11 / 17, that absence from an abstract is not proof of absence, and that no systematic search was done.
8. Group C (foundational): sign-flip attack described as our own, with Fang/Yin as related threat models; 1.4826 stated as $1/\Phi^{-1}(0.75)$; FedAvgM attributed to Hsu et al.; `cho2020clientselection` replaced by `cho2022biased`.

## Claims that remain uncertain (do not strengthen)
* Anything about internals of the 20 abstract-level sources (e.g. whether abdallah2026routing, liu2026reliability, tang2026fedcst, haripriya2025fault, chen2025hierarchical, bhardwaj2024routing or shah2026trisafe contain delivery/selection/imputation/fairness elements) — "not in the abstract" is not evidence of absence.
* Figures quoted from digests (e.g. "50% fog nodes", ">20% efficiency" for liu2026anonymous) are not used in the manuscript.
* Pages of Krum (119-129) rest on a secondary record; Hsu et al. is arXiv-only; McMahan 2018 and Reddi 2021 venues confirmed via arXiv/PDF headers.
* Fetch-tool quotes are digests, not raw text; spot-check before quoting.

## Human action to close M1 (free, browser-accessible)
Read in full, in this order: haripriya2025fault and shah2026trisafe (gold OA on IEEE Xplore), albanbay2025ids (MDPI), alghadi2025dos (Elsevier OA), s2dfl2026 (IEEE OJCS OA), aburukba2025scheduling (MDPI), zhou2024qos (ScienceDirect), then via institutional access abdallah2026routing, liu2026reliability, tang2026fedcst, chen2025hierarchical, bhardwaj2024routing, shu2026trustworthy, zhang2026malicious, liu2026anonymous, geng2024smpc, lan2025ckks. For each, confirm or soften the cited sentence and update the NOVELTY_COMPARISON_MATRIX.

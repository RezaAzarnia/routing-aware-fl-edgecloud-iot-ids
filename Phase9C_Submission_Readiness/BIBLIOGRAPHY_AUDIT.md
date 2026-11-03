# Bibliography audit (exact inventory, Phase 9C)

Source of truth: `Phase9_Manuscript_Revision/bibliography/verified_references.bib`, LaTeX sources `latex/main.tex` + `sections/related_work.tex`, compiled `main.bbl`. Reproduce: `python Phase9C_Submission_Readiness/scripts/bib_audit.py` (output saved in `evidence/bibliography_inventory.json`).

## Reconciliation of the counts
| Quantity | Phase 9B report | Verified in Phase 9C |
|---|---|---|
| Entries in .bib | 52 | **52 at the start of Phase 9C** → **44 now** |
| Distinct cited keys | 43 | 43 at the start → **44 now** |
| Uncited entries | "8" (arithmetic left 1 unexplained: 52 − 43 = 9) | **9 at the start**: the 8 listed (albogami2025deepfl, bayat2025qlearning, carillo2026incremental, padmavathi2025trust, s2dfl2026, wang2024trust, wang2026desa, zhang2026endpca) **plus `cho2020clientselection`**, the superseded arXiv version of Cho et al. that was kept in the .bib after the manuscript was switched to `cho2022biased` (the unexplained ninth entry) |
| Entries printed in the reference list (`main.bbl`) | 43 | **44 now** |
| Undefined citations | 0 | 0 |

## Actions taken (Phase 9C)
* Removed (not needed, unsupportable or weak): `cho2020clientselection` (superseded), `bayat2025qlearning` (not an FL paper), `wang2024trust` (trust-score attacks, not aggregation), `padmavathi2025trust` (access control), `carillo2026incremental` (abstract only, early access, not needed), `wang2026desa` (abstract only, off-topic for the gap), `zhang2026endpca` (abstract only, adds nothing), `li2023privacy` (record only; mask/noise mechanism unverified).
* Now cited deliberately: `albogami2025deepfl` (full text read; FL-IDS list) and `s2dfl2026` (abstract level; joint robustness + privacy clause).
* Final: **44 entries = 44 cited = 44 printed**, 0 undefined.

## Composition of the final 44
| Group | Entries | Verification level |
|---|---|---|
| Foundational / methodological (16): mcmahan2017fedavg, blanchard2017krum, yin2018byzantine, fang2020local, mironov2017renyi, zhu2019poisson, abadi2016dpsgd, mcmahan2018dprnn, bonawitz2017secagg, hsu2019measuring, reddi2021adaptive, moustafa2015unsw, neto2023ciciot, rousseeuw1993mad, agrawal2022flids, cho2022biased | metadata checked against authoritative pages (PMLR, USENIX, NeurIPS, arXiv, Crossref); claims checked in Group C | Krum pages secondary; Hsu arXiv-only; McMahan 2018/Reddi 2021 via arXiv headers |
| Application-level (28), read in full or in part (11) | soomro2026securedyn, latif2026multimodel, peng2025fdids, rahmati2025cybersecurity, albogami2025deepfl, zhu2026bpflh, almeida2025modular, alanazi2026edgeguard, zhang2026adaptive, liu2024iiot, mughal2024adaptive | full/partial text + Crossref/Europe PMC metadata |
| Application-level, abstract level (17) | haripriya2025fault, chen2025hierarchical, bhardwaj2024routing, shah2026trisafe, abdallah2026routing, liu2026reliability, tang2026fedcst, aburukba2025scheduling, zhou2024qos, geng2024smpc, lan2025ckks, albanbay2025ids, alghadi2025dos, zhang2026malicious, liu2026anonymous, shu2026trustworthy, s2dfl2026 | abstract/fragment + Crossref/OpenAlex/DOAJ metadata |

## Metadata findings
* No field-level error in any of the 35 original application entries (authors, title, venue, year, volume, pages/article number, DOI match Crossref / OpenAlex / Europe PMC / DOAJ); three earlier corrections applied in Phase 9 (carillo — now removed —, abdallah pages → article number 29, aburukba author name). Notes: `liu2026reliability` DOI says 2025 but issue date is January 2026 (bib 2026 acceptable); pages of liu2026reliability, tang2026fedcst, abdallah2026routing are article numbers; IEEE landing pages were not readable (Crossref-level check).
* Foundational corrections applied: `blanchard2017krum` (NeurIPS title/URL), `fang2020local` (USENIX URL, ISBN), Cho et al. (AISTATS 2022 version, PMLR 151).
* Open items for the authors: confirm Krum pages (119-129) in the NeurIPS proceedings; decide whether to cite the peer-reviewed venue of Hsu et al. if one exists (none found); spot-check any quotation that originated from a fetch-tool digest.

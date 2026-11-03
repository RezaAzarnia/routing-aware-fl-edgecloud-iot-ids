# Manuscript edit log, Phase 9D (numerical results unchanged; 93/93 checks still pass)

| Location | Change | Reason |
|---|---|---|
| Abstract | "indistinguishable from clean FedAvg" → "within 0.001 ROC-AUC of clean FedAvg" | equivalence was not tested; state the measured gap |
| Introduction | "commonly combined" → "often combined"; "rarely measured" → "in the sources we examined, … rarely measured" | avoid an unsupported claim about the whole literature |
| Sec. Datasets | UNSW-NB15 feature count "194" → "192–194 depending on the seed's training split" | found in the 15-pair preprocessing audit (one-hot categories depend on the seed) |
| Methods / Results / captions | internal labels "Phase 6C", "Phase 8 finding" → "main experiment", "found during the audit" | reader-facing wording; one occurrence of the file path `Phase9_Manuscript_Revision/...` in a table source line is a path, kept |
| Sec. Results (routing) | "Our earlier manuscript" → "An earlier version of this manuscript" | consistency |
| Discussion | "necessary and sufficient" → measured statement (undefended collapses; filtered within 0.001 AUC of clean FedAvg; five seeds, exploratory); extra delay "an artefact" → "attributable to the stricter delivery model (the single-factor control shows the same delay)" | overclaim removed; evidence cited |
| Reproducibility paragraph | "155 unit tests" → "172 in ordinary runs; three further tests that read the locked files run only in a separately authorised workflow"; branch wording generalised; access disclosure retained | accuracy after Phase 9C |
| Related work | closed-source statements about routing studies rewritten as "not stated in the parts we read"; zhou2024qos and zhang2026malicious tagged "abstract level"; shah2026trisafe: "whether their mechanisms differ cannot be judged from the abstract" | `LITERATURE_CLAIMS_AUDIT.md` |
Table and figure captions were re-read for consistency (Tables 2–8, Figs. 1–7: protocol, seeds, partition, "best/last" and source-file statements agree with the text); the PDF compiles without undefined citations or overfull boxes; bibliography 44 = 44 cited = 44 printed.

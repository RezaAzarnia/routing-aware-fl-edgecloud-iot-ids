# Seed provenance of the manuscript's existing Figures 3–6 — UNRESOLVED (documented, not guessed)

Manuscript (Git HEAD 7d5280d) captions: Fig. 3 "UNSW-NB15 routing, participation fairness, and detection over five seeds"; Fig. 4 "Markers and error bars summarize five seeds"; Fig. 5 "Curves represent five-seed means"; Fig. 6 "policy means (n = 5)". **No caption or text states which five seeds.**

Evidence found in the repository (each is an inference, none is a run record):
1. `Table4_Audit_Package/TABLE4_EVIDENCE_AUDIT.md`: "Table 4 and the performance figures (fig3–fig8) come from the original July 2026 study … original code (≈ 7c75b2d) — **inferred** … there is **no run record** to confirm it"; the original README documents seeds 2–6.
2. The earlier reviewer audit (`FINAL_REVIEWER_AUDIT.md`, concern 3): the content of Figs 3–6 (four selection policies including UCB, independent/coupled networks, selection Gini, never-selected clients) **matches the Phase 10 study** (UNSW only; seeds 22–26 in the Phase 10 manifest), whereas Table 3 states main seeds 12–16.
3. `Table4_V2_Package/TABLE4_V2_MANUSCRIPT_IMPACT.md`: only Fig. 3 is referenced next to Table 4; Figs 4–6 were not scanned as Table-4 dependent.
4. The supplementary participation study in this package (seeds 12–16; top-k, coverage-aware, uniform; independent/coupled; UNSW from SUPP_V1, CICIoT2023 from SUPP_V2) does **not** include a UCB policy and is not the source of the existing figures.

Possible sources (unconfirmed): original study seeds 2–6; Phase 10 seeds 22–26; Table 4 v2 seeds 12–16. The data files behind the manuscript PNGs (fig3–fig6.png) were not available to verify. **Required author action:** identify the generating script and seed list for each of Figs 3–6, then state them in the captions or Experimental Setup; if they cannot be recovered, state that the seed identity is not recorded, or regenerate the figures from the verified 12–16 data. Until then, patch C10 contains the placeholder `[AUTHOR TO CONFIRM: seeds]`.

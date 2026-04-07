# Node Verification Report — permit_nodes & settlement_nodes

Date: 2026-04-07
Corpus: indonesian-construction-law/ (uu/, pp/, permen/)
Also scanned: local_regulations/

---

## PERMIT_NODES

| Node ID | Source Claimed | Corpus Found? | Verified | Discrepancy |
|---------|---------------|---------------|----------|-------------|
| NIB | (entry point, no source) | N/A | TRUE | None |
| UU6_2023_Art7_8 | UU No. 6 Tahun 2023 Pasal 7 & 8 | YES — UU_6_2023_CiptaKerja.txt lines 682-786 | TRUE | Pasal 7 & 8 confirmed as risk-categorization (Low/Medium/High). |
| KKPR | PP No. 28 Tahun 2025 Pasal 27 | YES — PP_28_2025_PerizinanBerbasisRisiko.txt line 843 | TRUE | KKPR/spatial conformity confirmed. |
| KKPR_FAILURE | PP No. 28 Tahun 2025 Pasal 27 | YES | TRUE | Same source as KKPR, consistent. |
| ENV_APPROVAL | PP No. 28 Tahun 2025 Pasal 27 | YES | TRUE | Environmental gate consistent with risk-based framework. |
| PBG | PP No. 16 Tahun 2021 Pasal 253 | YES — PP_16_2021_BatangTubuh.txt line 16020 | TRUE | PBG issuance process confirmed. |
| SLF | PP No. 16 Tahun 2021 Pasal 283 | YES — PP_16_2021_BatangTubuh.txt line 17863 | TRUE | SLF/as-built certification confirmed. |
| ACCESSIBILITY_GATE | Permen PUPR No. 14/PRT/M/2017 | PARTIAL | PARTIAL | 1:12 ramp ratio found in Lampiran2.txt line 1712. 90cm door width NOT confirmed in corpus. |
| BIM_GATE | SIDLACOM cycle | NOT FOUND | FALSE | "SIDLACOM" not in corpus. BIM 2000m2/2-floor threshold not found. Source unverified. |
| BID_REASONABLENESS | Permen 10/2021 + AHSP 2026 | NOT FOUND | FALSE | Permen 10/2021 does not exist. SMKK confirmed in Permen 8/2023. "AHSP 2026" is future-dated, not in corpus. |

Summary: 7/10 fully verified, 1 partial, 2 failed.

---

## SETTLEMENT_NODES

| Node ID | Source Claimed | Corpus Found? | Verified | Discrepancy |
|---------|---------------|---------------|----------|-------------|
| UU1_2011_HOUSING | UU No. 1 Tahun 2011 | NOT IN CORPUS | FALSE | UU 1/2011 absent from uu/ folder. |
| PSU_STANDARDS | UU No. 1 Tahun 2011 | NOT IN CORPUS | FALSE | Same. PSU concept in UU 6/2023 but primary source missing. |
| MBR_ELIGIBILITY | Permen PKP No. 5 Tahun 2025 | NOT IN CORPUS | FALSE | Permen PKP 5/2025 absent. MBR mentioned in UU 6/2023 but income thresholds unverified. |
| MBR_SUBSIDY_PATH | Permen PKP No. 5 Tahun 2025 | NOT IN CORPUS | FALSE | Same as above. |
| SPATIAL_RATIO_GATE | SNI 03-1733-2004 | NOT IN CORPUS | FALSE | SNI 03-1733-2004 absent from sni/ folder. 1:250 ratio not verified. |
| PPPSRS_LOGIC | Permen PKP No. 4 Tahun 2025 | NOT IN CORPUS | FALSE | Permen PKP 4/2025 absent. PPPSRS mentioned in UU 6/2023 but referenced permen missing. |
| RETROFIT_SUBSIDY_CROSS | Cross-module intersection | N/A | UNVERIFIABLE | Plausible concept, no specific regulation cited. |

Summary: 0/7 fully verified. 5 failed, 1 unverifiable, 1 conceptual.

---

## KEY DISCREPANCIES

CRITICAL:
1. BIM_GATE — SIDLACOM not found in corpus; BIM thresholds (2000m2, 2 floors) unverified.
2. BID_REASONABLENESS — Permen 10/2021 absent; "AHSP 2026" future-dated reference not in corpus.
3. UU1_2011_HOUSING — Entire UU 1/2011 missing from corpus.
4. MBR_ELIGIBILITY / MBR_SUBSIDY_PATH — Permen PKP 5/2025 missing.
5. SPATIAL_RATIO_GATE — SNI 03-1733-2004 missing.
6. PPPSRS_LOGIC — Permen PKP 4/2025 missing.

PARTIAL:
7. ACCESSIBILITY_GATE — 1:12 ramp confirmed, but 90cm door width claim unverified.

---

## RECOMMENDED ACTIONS

1. Add UU No. 1 Tahun 2011 (Housing Act) to uu/ corpus.
2. Add Permen PKP No. 4/2025 and No. 5/2025 to permen/ corpus (or correct to actual MBR/subsidy regulations).
3. Add SNI 03-1733-2004 to sni/ folder.
4. Correct BID_REASONABLENESS source — Permen 10/2021 does not exist; use actual SMKK/AHSP regulation.
5. Remove or find actual source for BIM_GATE (SIDLACOM not verified).
6. Verify 90cm door width against Permen 14/2017 Lampiran.

# RowletAI — V3.1 Integration Checklist

## 1. Scoring Engine — FROZEN
- [x] V3 syntax check
- [x] V3 automated unit tests
- [x] Valuation V3 audit
- [x] Risk V3 audit
- [x] Momentum V3 audit
- [x] Growth V3 audit
- [x] Bagger 25/20/20/20/15 formula audit
- [x] Dividend separate from Bagger
- [x] Representative validation 7/7

## 2. Company Journal V3.1 Candidate
- [x] Executive View uses one interpretation layer from canonical V3 composite signal
- [x] Analyst Conclusion Overall Model View uses the same interpretation layer
- [x] Section 08 shows the five actual Bagger dimensions: Growth, Quality, Valuation, Risk Strength, Momentum
- [x] Dividend remains in Section 05 and is not presented as a Bagger dimension
- [x] Evidence coverage wording now refers specifically to Bagger/scoring-dimension coverage
- [x] Coverage label is dynamic: Complete vs Partial Scoring Coverage
- [x] Fundamental CAGR wording distinguishes compounded forecast levels from Section 04 scenario bands
- [x] Section 04 Bear/Base/Bull disclaimer preserved
- [x] MASTER dashboard.py untouched

## 3. V3.1 Candidate Technical Checks
- [x] dashboard_scoring_v3_1_candidate.py compiles
- [x] test_dashboard_scoring_v3_1.py passes 9/9

## 4. Next Manual Regression — AADI.JK
- [ ] Company Header
- [ ] Executive View
- [ ] Research View matches Section 09 Overall Model View
- [ ] Bagger Score remains 69.5 for the current AADI test state
- [ ] Section 03 Revenue / Net Profit / EPS render correctly
- [ ] Section 03 CAGR wording is clear
- [ ] Section 04 scenario labels remain intact
- [ ] Section 05 Dividend Analysis remains intact
- [ ] Section 06 Valuation & Price Simulation remains intact
- [ ] Section 07 Risk & Catalysts remains intact
- [ ] Section 08 shows Quality instead of Dividend
- [ ] Section 09 Overall Model View is consistent with Executive View

## 5. Market Intelligence Regression
- [ ] STEP 1 unchanged visually
- [ ] STEP 2 unchanged visually
- [ ] Sector dropdown works
- [ ] Bagger Score filter works
- [ ] Evidence filter works
- [ ] Liquidity filter works
- [ ] Company count remains correct
- [ ] Download Results works
- [ ] Reset Filter works

## 6. Final MASTER Integration — LOCKED UNTIL ABOVE PASSES
- [ ] Backup MASTER
- [ ] Integrate V3 engine into MASTER surgically
- [ ] Preserve STEP 1
- [ ] Preserve STEP 2
- [ ] Preserve Company Journal layout
- [ ] Run py_compile
- [ ] Run automated tests
- [ ] Run representative validation
- [ ] Run Company Journal regression
- [ ] Run Market Intelligence regression
- [ ] Final visual audit

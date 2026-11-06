# RowletAI — Scoring Engine V2 Full-Universe Audit

Run date: 2026-09-27

## Scope

The V2 scoring engine was executed against the reconstructed project datasets:
- `bagger_scores.json` — 962 companies
- `fundamentals.json` — 962 companies
- `momentum_scores.json` — 514 companies with momentum evidence
- `risk_metrics.json` — 518 companies with risk evidence
- `company_profiles.json` — 962 companies

The production `bagger_scores.json` was not overwritten. The new output is `data/bagger_scores_v2.json`.

## Full-universe result

- Universe: **962** companies
- Full 5-dimension Bagger Score: **396**
- High evidence: **396**
- Moderate evidence: **39**
- Low evidence: **429**
- Insufficient evidence: **98**
- Strong composite: **16**
- Balanced composite: **104**
- Weak composite: **190**
- Low composite: **86**
- Insufficient evidence signal: **566**

## Factor availability

| Factor | Available | Missing |
|---|---:|---:|
| Growth | 822 | 140 |
| Quality | 861 | 101 |
| Valuation | 869 | 93 |
| Momentum | 514 | 448 |
| Risk Strength | 518 | 444 |
| Bagger | 396 | 566 |

## Engine validation

### Risk

The liquidity-aware risk engine materially changed the risk output for illiquid/stale names. Compared with the old engine, the mean absolute change in `risk_score` was **14.54 points**, with **79.87%** of common observations moving by more than 5 points.

The engine applies liquidity quality and hard caps to reduce false safety from stale prices and low trading activity.

### Valuation

Mean absolute change in `valuation_score`: **9.02 points**; **58.02%** of common observations changed by more than 5 points.

Forward P/E is incorporated when available, P/E is excluded when non-positive, and P/B is secondary. Relative ranking falls back to the universe when a sufficiently populated sector/industry peer group is unavailable.

### Growth

The current batch has **0 cached Company Reports**, so multi-period CAGR components were not available in this full-universe run. The engine therefore correctly retained the verified YoY growth evidence rather than fabricating multi-period values.

This is an evidence limitation, not a calculation error.

### Momentum

Mean absolute change in `momentum_score`: **8.09 points**; **55.64%** of common observations changed by more than 5 points.

The V2 engine reduces redundant trend counting and applies liquidity confirmation.

### Bagger

The frozen composite weights remain:
- Growth 25%
- Quality 20%
- Valuation 20%
- Momentum 20%
- Risk Strength 15%

The score requires all five dimensions. Rounded output can differ by up to 0.005 from recomputing the weighted sum from the already-rounded displayed components; this is normal rounding behavior.

## Important data-quality finding

`company_profiles.json` currently contains blank sector/industry values for **961 of 962** companies; only one company has a populated sector/industry pair. Therefore, the V2 valuation engine is structurally sector-aware, but the supplied batch data does **not** provide enough verified sector/industry evidence to activate meaningful sector-peer valuation for the universe.

The correct behavior is to fall back to universe-relative valuation rather than invent sectors.

## Recommendation before production replacement

Keep `bagger_scores.json` unchanged for now. Use `bagger_scores_v2.json` as the validated candidate output. The next data-quality step should be to populate verified sector/industry and cached Company Report history/forward forecasts, then rerun the exact same engine without changing the scoring formula.

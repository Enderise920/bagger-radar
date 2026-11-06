# RowletAI Scoring Audit — Final V3 Candidate

## Baseline
Audited dashboard: `dashboard(1).py` uploaded 27 Sep 2026. The dashboard remains untouched.

## Universe test
- Fundamentals: 962 companies
- Momentum coverage: 514
- Risk coverage: 518
- V3 complete Bagger scores: 396
- V3 dividend scores: 487

## Final architecture
- Growth 25%
- Quality 20%
- Valuation 20%
- Momentum 20%
- Risk Strength 15%
- Dividend: separate research score; not part of Bagger

## Corrections implemented
### 1. Valuation
- Positive Forward P/E preferred; TTM P/E fallback.
- Forward P/E and TTM P/E are not stacked together because they represent highly correlated PE evidence.
- P/B is secondary at 30% when available.
- Positive multiples only.
- Industry peers preferred when at least 15 valid peers exist; sector is fallback; full universe is last resort.
- Intrinsic value/scenario outputs remain outside the measured score.

### 2. Risk
- Core risk uses 20D volatility, 60D volatility, 60D max drawdown and 20D max daily loss.
- Core risk = 80%; liquidity/price-quality = 20%.
- Zero-return ratio and unique-price ratio are incorporated.
- Explicit anti-false-safety caps prevent stale prices from looking safe.
- `risk_strength` is the favorable Bagger contribution; `risk_score` is its inverse display penalty.

### 3. Momentum
- 20D return 35%.
- 60D return 25%.
- Price vs MA60 20%.
- Trend acceleration 20%, defined as 20D return minus one-third of 60D return.
- Liquidity confirmation reduces confidence without being counted as a second full risk penalty.

### 4. Growth
- Current verified YoY revenue and earnings growth are primary.
- Optional 3Y revenue/earnings/EPS CAGR fields are supported when real Company Report evidence is available.
- Percentile ranking prevents extreme raw growth from dominating.
- Missing data stays missing.

### 5. Bagger
- Arithmetic and 25/20/20/20/15 weights remain unchanged.
- A complete numeric score requires all five dimensions.
- Evidence level is now independent from numeric completeness. A stock can have five numbers and still be LOW/MEDIUM evidence if market-data quality is weak.
- Composite thresholds preserved: 65 strong, 50 balanced, 35 weak.

### 6. Dividend
- Remains separate from Bagger.
- Yield, payout sustainability, cash-flow payout where applicable, and verified dividend history are used.
- Extreme yield is gated when payout evidence is missing/stressed.
- Banks are not forced through the non-bank cash-payout methodology.

## 962-company result summary
- Mean V3 Bagger Score: 46.81
- Evidence HIGH: 146
- Evidence MEDIUM: 95
- Evidence LOW: 155
- Evidence INSUFFICIENT: 566

## Change profile vs current `bagger_scores.json`
- **growth_score**: common 822; mean absolute change 0.06; >10 point change 0.0%; correlation 1.000.
- **quality_score**: common 861; mean absolute change 0.90; >10 point change 0.0%; correlation 0.998.
- **valuation_score**: common 867; mean absolute change 4.96; >10 point change 14.0%; correlation 0.944.
- **momentum_score**: common 514; mean absolute change 5.34; >10 point change 15.6%; correlation 0.959.
- **risk_strength**: common 452; mean absolute change 17.24; >10 point change 74.1%; correlation 0.382.
- **bagger_score**: common 380; mean absolute change 2.83; >10 point change 0.3%; correlation 0.962.

## Interpretation
The largest structural change is risk/liquidity treatment. Growth and quality remain close to the current architecture; valuation and momentum move more because the peer-relative and trend definitions are more explicit. The Bagger composite remains comparatively stable because its weights are unchanged and only companies with all five dimensions receive a numeric composite.

The V3 files are **candidates for integration**, not a replacement of the production dashboard. The next integration step should make Company Journal consume the same V3 score objects instead of maintaining a separate live momentum/risk calculation path.

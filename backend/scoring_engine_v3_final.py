"""RowletAI scoring engine v3 — audited, evidence-aware scoring.

This module is deliberately independent from Streamlit/dashboard.py.
It recalculates the quantitative layers from source tables and keeps missing
inputs missing. It does not fabricate data and does not write files by itself.

Bagger Score weights are frozen to the project's architecture:
Growth 25%, Quality 20%, Valuation 20%, Momentum 20%, Risk Strength 15%.
Dividend is a separate research score and does not enter Bagger Score.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


BAGGER_WEIGHTS = {
    "growth_score": 0.25,
    "quality_score": 0.20,
    "valuation_score": 0.20,
    "momentum_score": 0.20,
    "risk_strength": 0.15,
}


# ----------------------------- generic helpers -----------------------------

def num(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return np.nan
    return v if np.isfinite(v) else np.nan


def clip_score(x: Any) -> float:
    v = num(x)
    return float(np.clip(v, 0.0, 100.0)) if np.isfinite(v) else np.nan


def _series(df: pd.DataFrame, col: str) -> pd.Series:
    if df is None or col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def robust_percentile(
    series: Sequence[Any], value: Any, *, higher_is_better: bool = True,
    min_n: int = 15,
) -> float:
    """Universe percentile with stable tie handling.

    Percentiles are based on the valid reference population. Magnitude does not
    dominate the score, so extreme values such as 900% earnings growth do not
    overwhelm the rest of the model. A small population is treated as
    insufficient rather than pretending to be statistically strong.
    """
    v = num(value)
    s = pd.to_numeric(pd.Series(series), errors="coerce").dropna()
    if not np.isfinite(v) or len(s) < min_n:
        return np.nan
    # Mid-rank percentile. Include the observation itself without the old
    # asymmetric +1/N correction.
    rank = float((s < v).sum() + 0.5 * (s == v).sum()) / float(len(s))
    score = 100.0 * rank
    if not higher_is_better:
        score = 100.0 - score
    return float(np.clip(score, 0.0, 100.0))


def _component_score(
    ref: pd.Series, value: Any, *, higher_is_better: bool = True,
    min_n: int = 15,
) -> float:
    return robust_percentile(ref, value, higher_is_better=higher_is_better, min_n=min_n)


def _weighted_available(items: Iterable[Tuple[float, float]]) -> float:
    pairs = [(num(v), float(w)) for v, w in items if np.isfinite(num(v)) and w > 0]
    if not pairs:
        return np.nan
    total_w = sum(w for _, w in pairs)
    return float(sum(v * w for v, w in pairs) / total_w)


def _evidence_from_count(n: int, total: int) -> str:
    if n >= total:
        return "HIGH"
    if n >= max(2, int(np.ceil(total * 0.6))):
        return "MEDIUM"
    if n >= 1:
        return "LOW"
    return "INSUFFICIENT"


# ----------------------------- quality score -----------------------------

def quality_score(row: Mapping[str, Any], universe: pd.DataFrame) -> Dict[str, Any]:
    """Quality = ROE + ROA, with optional leverage only when defensible.

    ROE and ROA remain the core quality evidence because that is what the
    dashboard methodology states. DER is deliberately not allowed to distort
    banks/non-banks differently; it is reported as supplemental evidence only.
    """
    vals = []
    details: Dict[str, Any] = {}
    for key, weight in (("roe_ttm", 0.60), ("roa_ttm", 0.40)):
        v = num(row.get(key))
        if np.isfinite(v):
            s = _component_score(_series(universe, key), v, higher_is_better=True)
            if np.isfinite(s):
                vals.append((s, weight))
                details[key] = s
    score = _weighted_available(vals)
    return {
        "quality_score": clip_score(score),
        "quality_evidence": _evidence_from_count(len(vals), 2),
        "quality_details": details,
    }


# ----------------------------- growth score -----------------------------

def _growth_value(row: Mapping[str, Any], names: Sequence[str]) -> float:
    for name in names:
        v = num(row.get(name))
        if np.isfinite(v):
            return v
    return np.nan


def growth_score(row: Mapping[str, Any], universe: pd.DataFrame) -> Dict[str, Any]:
    """Growth from independent growth evidence; optional CAGRs if supplied.

    Current source files expose quarterly YoY revenue and earnings growth.
    If future rebuilds add multi-year CAGRs, they are incorporated automatically.
    Missing metrics are renormalized, never converted to zero.
    """
    definitions = [
        (("yoy_quarter_revenue_growth", "revenue_growth_yoy"), 0.30),
        (("yoy_quarter_earnings_growth", "earnings_growth_yoy"), 0.30),
        (("revenue_cagr_3y", "revenue_cagr"), 0.15),
        (("earnings_cagr_3y", "earnings_cagr"), 0.15),
        (("eps_cagr_3y", "eps_cagr"), 0.10),
    ]
    vals = []
    details: Dict[str, Any] = {}
    for names, weight in definitions:
        v = _growth_value(row, names)
        if not np.isfinite(v):
            continue
        # Reference percentile is naturally robust to extreme growth values.
        ref_col = next((c for c in names if c in universe.columns), None)
        if ref_col is None:
            continue
        s = _component_score(_series(universe, ref_col), v, higher_is_better=True)
        if np.isfinite(s):
            vals.append((s, weight))
            details[ref_col] = s
    score = _weighted_available(vals)
    # The two quarterly YoY metrics are the current verified base evidence.
    # Multi-year CAGR fields are optional enrichment: absence of them must not
    # downgrade a company to LOW when both current growth measures are present.
    base_available=sum(1 for names,_ in definitions[:2] if any(np.isfinite(num(row.get(n))) for n in names))
    optional_available=sum(1 for names,_ in definitions[2:] if any(np.isfinite(num(row.get(n))) for n in names))
    if base_available==2:
        # Current verified universe evidence is quarterly YoY revenue + earnings.
        # Multi-year CAGR is an enhancement, not a prerequisite for HIGH.
        growth_evidence="HIGH"
    elif base_available==1:
        growth_evidence="LOW"
    else:
        growth_evidence="INSUFFICIENT"
    return {
        "growth_score": clip_score(score),
        "growth_evidence": growth_evidence,
        "growth_details": details,
    }


# ----------------------------- valuation score -----------------------------

def _peer_reference(
    universe: pd.DataFrame,
    row: Mapping[str, Any],
    value_col: str,
    *,
    min_peers: int = 15,
) -> pd.Series:
    """Prefer sector/industry peers when classification is populated."""
    base = _series(universe, value_col)
    sector = str(row.get("sector", "") or "").strip()
    industry = str(row.get("industry", "") or "").strip()
    # Industry is usually the tighter economic peer set; use it first when
    # sufficiently populated, then sector, then the full universe.
    if industry and "industry" in universe.columns:
        mask = universe["industry"].astype(str).str.strip().str.casefold().eq(industry.casefold())
        peer = pd.to_numeric(universe.loc[mask, value_col], errors="coerce").dropna()
        if len(peer) >= min_peers:
            return peer
    if sector and "sector" in universe.columns:
        mask = universe["sector"].astype(str).str.strip().str.casefold().eq(sector.casefold())
        peer = pd.to_numeric(universe.loc[mask, value_col], errors="coerce").dropna()
        if len(peer) >= min_peers:
            return peer
    return base


def valuation_score(row: Mapping[str, Any], universe: pd.DataFrame) -> Dict[str, Any]:
    """Relative valuation score using one PE signal plus secondary P/B.

    Forward P/E is preferred; TTM P/E is used only when forward P/E is
    unavailable. P/E must be positive. P/B is secondary. The two PE variants
    are not stacked together because they are highly correlated measures of
    the same valuation dimension.
    """
    details: Dict[str, Any] = {}
    pe_score = np.nan
    pb_score = np.nan
    relative_to = []

    fpe = num(row.get("forward_pe"))
    pe = num(row.get("pe_ttm"))
    pb = num(row.get("pb_mrq"))

    if np.isfinite(fpe) and fpe > 0 and "forward_pe" in universe.columns:
        ref_univ = universe[pd.to_numeric(universe["forward_pe"], errors="coerce") > 0].copy()
        ref = _peer_reference(ref_univ, row, "forward_pe")
        pe_score = _component_score(ref, fpe, higher_is_better=False)
        if np.isfinite(pe_score):
            details["forward_pe"] = pe_score
            relative_to.append("Forward P/E")
    elif np.isfinite(pe) and pe > 0 and "pe_ttm" in universe.columns:
        ref_univ = universe[pd.to_numeric(universe["pe_ttm"], errors="coerce") > 0].copy()
        ref = _peer_reference(ref_univ, row, "pe_ttm")
        pe_score = _component_score(ref, pe, higher_is_better=False)
        if np.isfinite(pe_score):
            details["pe_ttm"] = pe_score
            relative_to.append("P/E TTM")

    if np.isfinite(pb) and pb > 0 and "pb_mrq" in universe.columns:
        ref_univ = universe[pd.to_numeric(universe["pb_mrq"], errors="coerce") > 0].copy()
        ref = _peer_reference(ref_univ, row, "pb_mrq")
        pb_score = _component_score(ref, pb, higher_is_better=False)
        if np.isfinite(pb_score):
            details["pb_mrq"] = pb_score
            relative_to.append("P/B")

    if np.isfinite(pe_score) and np.isfinite(pb_score):
        score = 0.70 * pe_score + 0.30 * pb_score
    elif np.isfinite(pe_score):
        score = pe_score
    elif np.isfinite(pb_score):
        score = pb_score
    else:
        score = np.nan

    return {
        "valuation_score": clip_score(score),
        "valuation_evidence": ("HIGH" if np.isfinite(pe_score) and np.isfinite(pb_score) else "MEDIUM" if np.isfinite(pe_score) else "LOW" if np.isfinite(pb_score) else "INSUFFICIENT"),
        "valuation_relative_to": ";".join(relative_to) if relative_to else "NONE",
        "valuation_details": details,
    }


# ----------------------------- liquidity / risk -----------------------------

def infer_liquidity_state(row: Mapping[str, Any]) -> str:
    state = str(row.get("liquidity_state", "") or row.get("liquidity_flag", "")).upper().strip()
    if state:
        if "NO_TRADING" in state:
            return "NO_TRADING_EVIDENCE"
        if "STALE" in state:
            return "STALE"
        if "LOW_ACTIVITY" in state or "LIMITED" in state:
            return "LOW_ACTIVITY"
        if "CAUTION" in state:
            return "CAUTION"
        if "ACTIVE" in state:
            return "ACTIVE"
    z = num(row.get("zero_return_ratio_20d"))
    u = num(row.get("unique_price_ratio_20d"))
    if np.isfinite(z) and np.isfinite(u):
        if z >= 0.80 or u <= 0.15:
            return "NO_TRADING_EVIDENCE"
        if z >= 0.50 or u <= 0.30:
            return "STALE"
        if z >= 0.30 or u <= 0.50:
            return "LOW_ACTIVITY"
        if z >= 0.15 or u <= 0.70:
            return "CAUTION"
    return "ACTIVE"


def liquidity_quality(row: Mapping[str, Any]) -> Tuple[float, str]:
    state = infer_liquidity_state(row)
    mapping = {
        "ACTIVE": 100.0,
        "CAUTION": 80.0,
        "LOW_ACTIVITY": 60.0,
        "STALE": 30.0,
        "NO_TRADING_EVIDENCE": 0.0,
    }
    return mapping.get(state, 50.0), state


def risk_strength(row: Mapping[str, Any], universe: pd.DataFrame) -> Dict[str, Any]:
    """Risk strength: lower realized risk = higher score.

    Core risk is 80%; liquidity quality is 20%. This prevents a stock with
    artificially flat prices from receiving a strong risk score merely because
    its measured volatility is near zero.
    """
    defs = [
        ("volatility_20d", False, 0.25),
        ("volatility_60d", False, 0.25),
        ("max_drawdown_60d", True, 0.25),
        ("max_daily_loss_20d", True, 0.25),
    ]
    vals = []
    details: Dict[str, Any] = {}
    for col, higher_is_better, weight in defs:
        v = num(row.get(col))
        if not np.isfinite(v) or col not in universe.columns:
            continue
        s = _component_score(_series(universe, col), v, higher_is_better=higher_is_better)
        if np.isfinite(s):
            vals.append((s, weight)); details[col] = s
    core = _weighted_available(vals)
    lq, state = liquidity_quality(row)
    if np.isfinite(core):
        strength = 0.80 * core + 0.20 * lq
    else:
        strength = lq if state != "ACTIVE" else np.nan
    # Hard caps protect against false safety from stale/flat prices.
    caps = {
        "NO_TRADING_EVIDENCE": 20.0,
        "STALE": 40.0,
        "LOW_ACTIVITY": 65.0,
    }
    if state in caps and np.isfinite(strength):
        strength = min(strength, caps[state])
    # Ratio-based ceilings are authoritative when explicit trading-quality
    # evidence is available; they prevent a flat/stale series from looking
    # safer merely because realized volatility is low.
    zr = num(row.get("zero_return_ratio_20d"))
    up = num(row.get("unique_price_ratio_20d"))
    if np.isfinite(zr):
        if zr >= 0.80:
            strength = min(strength, 15.0)
        elif zr >= 0.60:
            strength = min(strength, 30.0)
    if np.isfinite(up):
        if up <= 0.20:
            strength = min(strength, 20.0)
        elif up <= 0.40:
            strength = min(strength, 35.0)
    return {
        "risk_strength": clip_score(strength),
        "risk_score": clip_score(100.0 - strength) if np.isfinite(strength) else np.nan,
        "risk_evidence": _evidence_from_count(len(vals), 4),
        "risk_details": details,
        "liquidity_state": state,
        "liquidity_quality": lq,
    }


# ----------------------------- momentum -----------------------------

def momentum_score(row: Mapping[str, Any], universe: pd.DataFrame) -> Dict[str, Any]:
    """Momentum with horizon balance and explicit evidence quality.

    35% 20D return, 25% 60D return, 20% price-vs-MA60, 20% trend acceleration.
    The acceleration term compares short-horizon return with the 60D trend and
    avoids simply counting two highly correlated MA signals twice.
    """
    vals = []
    details: Dict[str, Any] = {}
    definitions = [
        ("return_20d", 0.35),
        ("return_60d", 0.25),
        ("price_vs_ma60", 0.20),
    ]
    for col, weight in definitions:
        v = num(row.get(col))
        if np.isfinite(v) and col in universe.columns:
            s = _component_score(_series(universe, col), v, higher_is_better=True)
            if np.isfinite(s):
                vals.append((s, weight)); details[col] = s

    r20 = num(row.get("return_20d")); r60 = num(row.get("return_60d"))
    if np.isfinite(r20) and np.isfinite(r60):
        acceleration = r20 - (r60 / 3.0)
        ref = pd.to_numeric(universe.get("return_20d", pd.Series(dtype=float)), errors="coerce") - pd.to_numeric(universe.get("return_60d", pd.Series(dtype=float)), errors="coerce") / 3.0
        s = _component_score(ref, acceleration, higher_is_better=True)
        if np.isfinite(s):
            vals.append((s, 0.20)); details["trend_acceleration"] = s

    raw = _weighted_available(vals)
    state = infer_liquidity_state(row)
    # Confidence adjustment only for trading evidence quality; do not use the
    # liquidity penalty twice in the Bagger score via risk.
    confidence = {"ACTIVE":1.00,"CAUTION":0.95,"LOW_ACTIVITY":0.90,"STALE":0.75,"NO_TRADING_EVIDENCE":0.50}.get(state,0.90)
    score = raw * confidence if np.isfinite(raw) else np.nan
    return {
        "raw_momentum_score": clip_score(raw),
        "momentum_score": clip_score(score),
        "momentum_evidence": _evidence_from_count(len(vals), 4),
        "momentum_confidence": confidence,
        "momentum_details": details,
        "liquidity_state": state,
    }


# ----------------------------- dividend -----------------------------

def _payout_score(v: float) -> float:
    if not np.isfinite(v) or v < 0:
        return np.nan
    # Smooth preference for sustainable payout rather than treating 30% as a
    # magic cliff.  40–65% is the central zone; very high payout is penalized.
    if v <= 0.40:
        return 70.0 + 25.0 * (v / 0.40)
    if v <= 0.65:
        return 95.0 + 5.0 * ((v - 0.40) / 0.25)
    if v <= 1.00:
        return 100.0 - 50.0 * ((v - 0.65) / 0.35)
    return max(5.0, 50.0 - 35.0 * min(v - 1.0, 1.0))


def dividend_score(row: Mapping[str, Any], universe: pd.DataFrame) -> Dict[str, Any]:
    """Dividend quality, separate from Bagger Score.

    Yield is capped by a reliability/sustainability gate so an extreme yield
    cannot dominate when payout coverage is weak. Historical consistency is
    used when supplied by Company Report enrichment.
    """
    y = num(row.get("yield_ttm"))
    payout = num(row.get("payout_ratio"))
    cash = num(row.get("cash_payout_ratio"))
    comps=[]; details={}
    if np.isfinite(y) and "yield_ttm" in universe.columns:
        ys=_series(universe,"yield_ttm")
        # Winsorize reference only; this prevents one distressed yield from
        # making the rest of the universe look artificially weak.
        s=_component_score(ys[ys>=0],y,higher_is_better=True)
        if np.isfinite(s): comps.append((s,0.35)); details["yield_score"]=s
    ps=_payout_score(payout)
    if np.isfinite(ps): comps.append((ps,0.25)); details["payout_score"]=ps
    cs=_payout_score(cash)
    if np.isfinite(cs) and not ("bank" in str(row.get("sector","")).lower() or "bank" in str(row.get("industry","")).lower()):
        comps.append((cs,0.20)); details["cashflow_score"]=cs
    hist=row.get("historical_dividends")
    if isinstance(hist,(list,tuple,dict)):
        vals=[]
        items=hist.items() if isinstance(hist,dict) else enumerate(hist)
        for year,item in items:
            if isinstance(item,dict):
                d=num(item.get("total_dividend")); d=d if np.isfinite(d) else num(item.get("dividend")); d=d if np.isfinite(d) else num(item.get("dividend_per_share"))
            else: d=num(item)
            if np.isfinite(d): vals.append(d)
        if len(vals)>=3:
            consistency=100.0*sum(v>0 for v in vals)/len(vals)
            comps.append((consistency,0.20)); details["consistency_score"]=consistency
    score=_weighted_available(comps)
    # Yield above 8% is not automatically good. Apply a conservative gate when
    # payout is unavailable or clearly stressed.
    if np.isfinite(score) and np.isfinite(y) and y>0.08:
        if np.isfinite(payout) and payout>1.0:
            score=min(score,45.0)
        elif not np.isfinite(payout):
            score=min(score,75.0)
    return {"dividend_score":clip_score(score),"dividend_evidence":_evidence_from_count(len(comps),4),"dividend_details":details}


# ----------------------------- composite -----------------------------

def _evidence_rank(label: Any) -> int:
    return {"HIGH":3,"GOOD":3,"MEDIUM":2,"MODERATE":2,"LOW":1,"LIMITED":1,"INSUFFICIENT":0,"NO_DATA":0}.get(str(label).upper(),0)


def bagger_score(scores: Mapping[str, Any]) -> Dict[str, Any]:
    """Final composite with frozen weights and separate evidence quality.

    A complete numeric composite is allowed only when all five quantitative
    dimensions exist. Evidence level is then graded independently from the
    numeric completeness so a stock with stale/weak market data cannot be
    mislabeled HIGH merely because five numbers happen to exist.
    """
    vals={k:num(scores.get(k)) for k in BAGGER_WEIGHTS}
    available=[k for k,v in vals.items() if np.isfinite(v)]
    if len(available)==5:
        score=sum(vals[k]*w for k,w in BAGGER_WEIGHTS.items())
        signal=("STRONG_COMPOSITE" if score>=65 else "BALANCED_COMPOSITE" if score>=50 else "WEAK_COMPOSITE" if score>=35 else "LOW_COMPOSITE")
    else:
        score=np.nan
        signal="INSUFFICIENT_EVIDENCE"

    dim_evidence=[
        scores.get("growth_evidence"), scores.get("quality_evidence"),
        scores.get("valuation_evidence"), scores.get("momentum_evidence"),
        scores.get("risk_evidence"),
    ]
    ranks=[_evidence_rank(x) for x in dim_evidence if x is not None]
    liq=str(scores.get("liquidity_state", "")).upper()
    weak_liq=liq in {"STALE","NO_TRADING_EVIDENCE"}
    limited_liq=liq in {"LOW_ACTIVITY","CAUTION"}

    if len(available)<5:
        evidence="INSUFFICIENT"
    elif weak_liq or any(r<=1 for r in ranks):
        evidence="LOW"
    elif limited_liq or any(r==2 for r in ranks):
        evidence="MEDIUM"
    else:
        evidence="HIGH"

    return {
        "bagger_score":clip_score(score),
        "available_dimensions":len(available),
        "evidence_level":evidence,
        "composite_signal":signal,
    }


def score_row(
    row: Mapping[str, Any],
    fundamentals: pd.DataFrame,
    momentum: Optional[pd.DataFrame]=None,
    risk: Optional[pd.DataFrame]=None,
    profiles: Optional[pd.DataFrame]=None,
) -> Dict[str, Any]:
    """Score one company from normalized source rows."""
    r=dict(row)
    sym=str(r.get("symbol", "")).upper().strip()
    if profiles is not None and not profiles.empty and "symbol" in profiles.columns:
        hit=profiles[profiles.symbol.astype(str).str.upper().eq(sym)]
        if not hit.empty:
            for k,v in hit.iloc[0].to_dict().items():
                if k != "symbol" and (k not in r or not str(r.get(k, "")).strip() or pd.isna(r.get(k))):
                    r[k]=v
    # Merge market/risk evidence before scoring the dimensions that depend on it.
    if momentum is not None and not momentum.empty and "symbol" in momentum.columns:
        hit=momentum[momentum.symbol.astype(str).str.upper().eq(sym)]
        if not hit.empty: r.update(hit.iloc[0].to_dict())
    if risk is not None and not risk.empty and "symbol" in risk.columns:
        hit=risk[risk.symbol.astype(str).str.upper().eq(sym)]
        if not hit.empty: r.update(hit.iloc[0].to_dict())

    out={}
    out.update(growth_score(r,fundamentals))
    out.update(quality_score(r,fundamentals))
    out.update(valuation_score(r,fundamentals))
    out.update(momentum_score(r, momentum if momentum is not None else pd.DataFrame()))
    out.update(risk_strength(r, risk if risk is not None else pd.DataFrame()))
    out.update(dividend_score(r, fundamentals))
    out.update(bagger_score(out))
    out["symbol"]=sym
    return out


def score_universe(
    fundamentals: pd.DataFrame,
    momentum: Optional[pd.DataFrame]=None,
    risk: Optional[pd.DataFrame]=None,
    profiles: Optional[pd.DataFrame]=None,
) -> pd.DataFrame:
    """Recalculate all companies without mutating the input tables."""
    if fundamentals is None or fundamentals.empty or "symbol" not in fundamentals.columns:
        return pd.DataFrame()
    base=fundamentals.copy()
    if profiles is not None and not profiles.empty and "symbol" in profiles.columns:
        pc=[c for c in ["symbol","sector","industry","company_name","description"] if c in profiles.columns]
        base=base.merge(profiles[pc],on="symbol",how="left",suffixes=("","_profile"))
        for c in ["sector","industry","company_name","description"]:
            cp=f"{c}_profile"
            if cp in base.columns:
                if c in base.columns:
                    base[c]=base[c].where(base[c].notna() & base[c].astype(str).str.strip().ne(""),base[cp])
                else:
                    base[c]=base[cp]
        base=base.drop(columns=[c for c in base.columns if c.endswith("_profile")],errors="ignore")

    rows=[]
    for _, row in base.iterrows():
        rows.append(score_row(row.to_dict(),base,momentum,risk,profiles=None))
    return pd.DataFrame(rows)


__all__=[
    "BAGGER_WEIGHTS","score_universe","score_row","bagger_score",
    "growth_score","quality_score","valuation_score","momentum_score",
    "risk_strength","dividend_score","infer_liquidity_state",
]

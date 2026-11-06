"""RowletAI Scoring Engine V2.

Evidence-first scoring for the five Market Intelligence dimensions:
Risk, Valuation, Growth, Momentum and Bagger.

Design goals:
- No fabricated values: missing evidence remains NaN.
- Cross-sectional scores are percentile based and robust to outliers.
- Risk explicitly separates market risk from trading/liquidity quality.
- Valuation is sector/industry relative when a sufficiently large peer group exists.
- Growth uses multi-period verified Company Report history when available, otherwise
  falls back to the current verified YoY observations with a lower evidence grade.
- Momentum reduces double counting between returns and moving-average signals and
  applies a liquidity-confidence confirmation.
- Bagger keeps the established 25/20/20/20/15 weights.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np
import pandas as pd


WEIGHTS = {
    "growth_score": 0.25,
    "quality_score": 0.20,
    "valuation_score": 0.20,
    "momentum_score": 0.20,
    "risk_strength": 0.15,
}

EPSILON = 1e-12


def num(x: Any) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else np.nan
    except Exception:
        return np.nan


def finite_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()


def percentile_score(value: Any, reference: pd.Series, higher_is_better: bool = True,
                     min_obs: int = 8) -> float:
    """Return an evidence-relative 0-100 percentile score.

    The selected observation is appended to the reference population so the
    returned percentile is stable and directly comparable to the universe.
    Extreme raw values do not change the ordering of the other observations.
    """
    v = num(value)
    ref = finite_series(reference)
    if np.isnan(v) or len(ref) < min_obs:
        return np.nan
    combined = pd.concat([ref, pd.Series([v])], ignore_index=True)
    pct = float(combined.rank(method="average", pct=True).iloc[-1] * 100.0)
    if not higher_is_better:
        pct = 100.0 - pct + (100.0 / len(combined))
    return float(np.clip(pct, 0.0, 100.0))


def _reference_column(df: pd.DataFrame, col: str, mask: pd.Series | None = None) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    x = df.loc[mask, col] if mask is not None else df[col]
    return finite_series(x)


def _peer_mask(df: pd.DataFrame, group_col: str, group_value: Any) -> pd.Series | None:
    if group_col not in df.columns or group_value is None:
        return None
    g = str(group_value).strip()
    if not g or g.lower() in {"nan", "none", "unknown", "-", "—"}:
        return None
    return df[group_col].astype(str).str.strip().str.casefold().eq(g.casefold())


def _relative_percentile(df: pd.DataFrame, row: pd.Series, col: str,
                         higher_is_better: bool, preferred_group: str = "sector",
                         secondary_group: str = "industry", min_peer: int = 8) -> tuple[float, str]:
    """Use sector/industry peer population when enough valid observations exist."""
    value = num(row.get(col))
    if np.isnan(value):
        return np.nan, "NONE"
    for group_col, label in ((preferred_group, "SECTOR"), (secondary_group, "INDUSTRY")):
        mask = _peer_mask(df, group_col, row.get(group_col))
        if mask is None:
            continue
        ref = _reference_column(df, col, mask)
        if len(ref) >= min_peer:
            return percentile_score(value, ref, higher_is_better, min_obs=min_peer), label
    ref = _reference_column(df, col)
    return percentile_score(value, ref, higher_is_better, min_obs=min_peer), "UNIVERSE"


def _sector_or_industry(row: pd.Series) -> str:
    for c in ("sector", "industry"):
        v = str(row.get(c, "")).strip()
        if v and v.lower() not in {"nan", "none", "unknown", "-", "—"}:
            return v
    return ""


def _report_historical(report: Mapping[str, Any] | None) -> pd.DataFrame:
    if not isinstance(report, Mapping):
        return pd.DataFrame(columns=["year", "revenue", "earnings", "eps"])
    fin = report.get("historical_financials") or []
    eps_raw = report.get("historical_eps") or {}
    rows = []
    if isinstance(fin, list):
        for item in fin:
            if not isinstance(item, Mapping):
                continue
            try:
                year = int(item.get("year"))
            except Exception:
                continue
            e = eps_raw.get(str(year), {}) if isinstance(eps_raw, Mapping) else {}
            eps = e.get("eps") if isinstance(e, Mapping) else e
            rows.append({
                "year": year,
                "revenue": num(item.get("revenue")),
                "earnings": num(item.get("earnings")),
                "eps": num(eps),
            })
    if isinstance(eps_raw, Mapping):
        years = {r["year"] for r in rows}
        for k, item in eps_raw.items():
            try:
                year = int(k)
            except Exception:
                continue
            if year in years or not isinstance(item, Mapping):
                continue
            rows.append({"year": year, "revenue": np.nan, "earnings": np.nan,
                         "eps": num(item.get("eps"))})
    if not rows:
        return pd.DataFrame(columns=["year", "revenue", "earnings", "eps"])
    return pd.DataFrame(rows).drop_duplicates("year", keep="last").sort_values("year").reset_index(drop=True)


def _cagr(start: Any, end: Any, years: int) -> float:
    s, e = num(start), num(end)
    if np.isnan(s) or np.isnan(e) or years <= 0 or s <= 0 or e <= 0:
        return np.nan
    return float((e / s) ** (1.0 / years) - 1.0)


def score_risk(df: pd.DataFrame, risk_df: pd.DataFrame) -> pd.DataFrame:
    """Risk engine: market risk + explicit liquidity/trading-quality risk.

    Core risk = volatility 20D/60D, drawdown and max daily loss.
    Liquidity confidence = 50% non-zero-return ratio + 50% unique-price ratio.
    Core risk contributes 80%; liquidity quality contributes 20%.
    Illiquid/stale observations receive a hard ceiling on risk strength so
    zero volatility caused by no trading cannot be interpreted as safety.
    """
    out = df.copy()
    if "symbol" not in out.columns:
        return out
    risk = risk_df.copy() if isinstance(risk_df, pd.DataFrame) else pd.DataFrame()
    if not risk.empty and "symbol" in risk.columns:
        cols = [c for c in ["symbol", "volatility_20d", "volatility_60d",
                            "max_drawdown_60d", "max_daily_loss_20d",
                            "zero_return_ratio_20d", "unique_price_ratio_20d",
                            "liquidity_state"] if c in risk.columns]
        out = out.drop(columns=[c for c in cols if c != "symbol" and c in out.columns], errors="ignore")
        out = out.merge(risk[cols], on="symbol", how="left", suffixes=("", "_riskv2"))

    refs = {c: _reference_column(out, c) for c in [
        "volatility_20d", "volatility_60d", "max_drawdown_60d", "max_daily_loss_20d",
        "zero_return_ratio_20d", "unique_price_ratio_20d"
    ]}
    strengths, scores, evidence, liq_flags = [], [], [], []
    for _, row in out.iterrows():
        components = []
        for col, higher in [
            ("volatility_20d", False),
            ("volatility_60d", False),
            ("max_drawdown_60d", True),
            ("max_daily_loss_20d", True),
        ]:
            v = num(row.get(col))
            if not np.isnan(v):
                p = percentile_score(v, refs[col], higher, min_obs=8)
                if not np.isnan(p):
                    components.append(p)
        core = float(np.mean(components)) if len(components) >= 3 else np.nan

        zr = num(row.get("zero_return_ratio_20d"))
        up = num(row.get("unique_price_ratio_20d"))
        liq_components = []
        if not np.isnan(zr):
            liq_components.append(100.0 * np.clip(1.0 - zr, 0.0, 1.0))
        if not np.isnan(up):
            liq_components.append(100.0 * np.clip(up, 0.0, 1.0))
        liq = float(np.mean(liq_components)) if liq_components else np.nan

        state = str(row.get("liquidity_state", "")).upper()
        if state in {"NO_TRADING_EVIDENCE", "STALE"}:
            liq = min(liq if not np.isnan(liq) else 0.0, 20.0)
        elif state == "LOW_ACTIVITY":
            liq = min(liq if not np.isnan(liq) else 35.0, 45.0)
        elif state == "CAUTION":
            liq = min(liq if not np.isnan(liq) else 55.0, 70.0)

        if np.isnan(core):
            strength = np.nan
        elif np.isnan(liq):
            strength = core
        else:
            strength = 0.80 * core + 0.20 * liq

        # Explicit anti-false-safety ceilings.
        if not np.isnan(zr) and zr >= 0.80:
            strength = min(strength, 15.0)
        elif not np.isnan(zr) and zr >= 0.60:
            strength = min(strength, 30.0)
        if not np.isnan(up) and up <= 0.20:
            strength = min(strength, 20.0)
        elif not np.isnan(up) and up <= 0.40:
            strength = min(strength, 35.0)

        strengths.append(strength)
        scores.append(100.0 - strength if not np.isnan(strength) else np.nan)
        liq_flags.append(state or ("ACTIVE" if not np.isnan(liq) and liq >= 70 else "CAUTION" if not np.isnan(liq) else "NO_DATA"))
        if np.isnan(strength):
            evidence.append("NO_DATA")
        elif (len(components) >= 4 and not np.isnan(liq) and liq >= 70):
            evidence.append("GOOD")
        elif len(components) >= 3 and not np.isnan(liq) and liq >= 45:
            evidence.append("MODERATE")
        else:
            evidence.append("LIMITED")
    out["risk_strength"] = np.round(strengths, 2)
    out["risk_score"] = np.round(scores, 2)
    out["risk_evidence"] = evidence
    out["liquidity_flag"] = liq_flags
    return out


def score_valuation(df: pd.DataFrame, reports: Mapping[str, Any] | None = None) -> pd.DataFrame:
    """Valuation engine: sector/industry-relative PE + PB, with forward PE priority."""
    out = df.copy()
    reports = reports or {}
    # Enrich only from already cached/verified Company Reports. No API calls here.
    forward = []
    sectors = []
    industries = []
    for _, row in out.iterrows():
        sym = str(row.get("symbol", "")).upper()
        rep = reports.get(sym) or reports.get(sym.replace(".JK", ""))
        val = rep.get("valuation", {}) if isinstance(rep, Mapping) else {}
        overview = rep if isinstance(rep, Mapping) else {}
        fv = num(row.get("forward_pe"))
        if np.isnan(fv): fv = num(val.get("forward_pe"))
        forward.append(fv)
        s = str(row.get("sector", "")).strip()
        i = str(row.get("industry", "")).strip()
        if not s or s.lower() in {"nan", "none"}:
            s = str(overview.get("sector", "")).strip()
        if not i or i.lower() in {"nan", "none"}:
            i = str(overview.get("industry", "")).strip()
        sectors.append(s)
        industries.append(i)
    out["forward_pe"] = pd.to_numeric(forward, errors="coerce")
    if "sector" not in out.columns: out["sector"] = sectors
    else: out["sector"] = out["sector"].where(out["sector"].notna() & out["sector"].astype(str).str.strip().ne(""), pd.Series(sectors, index=out.index))
    if "industry" not in out.columns: out["industry"] = industries

    scores = []
    evidence = []
    relative_to = []
    for idx, row in out.iterrows():
        pe_scores = []
        pe_sources = []
        fpe = num(row.get("forward_pe"))
        if fpe > 0:
            p, src = _relative_percentile(out, row, "forward_pe", False)
            if not np.isnan(p): pe_scores.append((p, 0.60)); pe_sources.append("Forward P/E")
        pe = num(row.get("pe_ttm"))
        # Negative/non-profitable P/E is not a valuation signal.
        if pe > 0:
            p, src = _relative_percentile(out, row, "pe_ttm", False)
            if not np.isnan(p): pe_scores.append((p, 0.40 if not fpe > 0 else 0.40)); pe_sources.append("P/E TTM")
        pe_score = (sum(s*w for s,w in pe_scores) / sum(w for _,w in pe_scores)) if pe_scores else np.nan

        pb = num(row.get("pb_mrq"))
        pb_score = np.nan
        pb_src = "NONE"
        if pb > 0:
            pb_score, pb_src = _relative_percentile(out, row, "pb_mrq", False)

        if not np.isnan(pe_score) and not np.isnan(pb_score):
            score = 0.70 * pe_score + 0.30 * pb_score
        elif not np.isnan(pe_score):
            score = pe_score
        elif not np.isnan(pb_score):
            score = pb_score
        else:
            score = np.nan

        scores.append(score)
        evidence.append("GOOD" if not np.isnan(score) and len(pe_scores) >= 2 else "MODERATE" if not np.isnan(score) else "NO_DATA")
        relative_to.append(";".join(sorted(set(pe_sources + ([f"P/B {pb_src}"] if not np.isnan(pb_score) else [])))) or "NONE")
    out["valuation_score"] = np.round(scores, 2)
    out["valuation_evidence"] = evidence
    out["valuation_relative_to"] = relative_to
    return out


def score_growth(df: pd.DataFrame, reports: Mapping[str, Any] | None = None) -> pd.DataFrame:
    """Growth engine with multi-period verified history and capped extreme growth.

    When a verified Company Report is available, 3Y CAGR is incorporated.
    Otherwise the current YoY observations remain usable but are graded as
    lower evidence. Extreme one-period growth is clipped to the 1st/99th
    percentile of the universe before percentile ranking.
    """
    out = df.copy()
    reports = reports or {}
    # Build multi-period derived fields from reports without inventing missing values.
    rev3, earn3, eps3, multi_evidence = [], [], [], []
    for _, row in out.iterrows():
        sym = str(row.get("symbol", "")).upper()
        rep = reports.get(sym) or reports.get(sym.replace(".JK", ""))
        h = _report_historical(rep)
        if h.empty:
            rev3.append(np.nan); earn3.append(np.nan); eps3.append(np.nan); multi_evidence.append("YOY_ONLY")
            continue
        last = h.iloc[-1]
        target_year = int(last["year"]) - 3
        base = h[h["year"].eq(target_year)]
        if base.empty:
            # Use the earliest point at least 2 years back; never interpolate.
            older = h[h["year"] <= int(last["year"]) - 2]
            base = older.iloc[[0]] if not older.empty else pd.DataFrame()
        yrs = int(last["year"] - int(base.iloc[-1]["year"])) if not base.empty else 0
        rev3.append(_cagr(base.iloc[-1]["revenue"], last["revenue"], yrs) if yrs else np.nan)
        earn3.append(_cagr(base.iloc[-1]["earnings"], last["earnings"], yrs) if yrs else np.nan)
        eps3.append(_cagr(base.iloc[-1]["eps"], last["eps"], yrs) if yrs else np.nan)
        multi_evidence.append("MULTI_PERIOD" if yrs >= 2 else "YOY_ONLY")
    out["revenue_cagr_multi"] = rev3
    out["earnings_cagr_multi"] = earn3
    out["eps_cagr_multi"] = eps3

    # Clip raw growth to the universe's 1st/99th percentile before ranking.
    def robust_ref(col: str) -> pd.Series:
        x = finite_series(out[col])
        if len(x) < 8: return x
        lo, hi = x.quantile(0.01), x.quantile(0.99)
        return x.clip(lo, hi)

    yoy_rev_ref = robust_ref("yoy_quarter_revenue_growth")
    yoy_earn_ref = robust_ref("yoy_quarter_earnings_growth")
    rev3_ref = robust_ref("revenue_cagr_multi")
    earn3_ref = robust_ref("earnings_cagr_multi")
    eps3_ref = robust_ref("eps_cagr_multi")

    scores, evidence = [], []
    for _, row in out.iterrows():
        parts = []
        rr = num(row.get("yoy_quarter_revenue_growth"))
        ee = num(row.get("yoy_quarter_earnings_growth"))
        r3 = num(row.get("revenue_cagr_multi"))
        e3 = num(row.get("earnings_cagr_multi"))
        ep3 = num(row.get("eps_cagr_multi"))
        if not np.isnan(rr):
            p_rr=percentile_score(np.clip(rr, yoy_rev_ref.min() if len(yoy_rev_ref) else rr, yoy_rev_ref.max() if len(yoy_rev_ref) else rr), yoy_rev_ref, True)
            if not np.isnan(p_rr): parts.append((p_rr, 0.30))
        if not np.isnan(ee):
            p_ee=percentile_score(np.clip(ee, yoy_earn_ref.min() if len(yoy_earn_ref) else ee, yoy_earn_ref.max() if len(yoy_earn_ref) else ee), yoy_earn_ref, True)
            if not np.isnan(p_ee): parts.append((p_ee, 0.30))
        if not np.isnan(r3):
            p_r3=percentile_score(r3, rev3_ref, True)
            if not np.isnan(p_r3): parts.append((p_r3, 0.15))
        if not np.isnan(e3):
            p_e3=percentile_score(e3, earn3_ref, True)
            if not np.isnan(p_e3): parts.append((p_e3, 0.15))
        if not np.isnan(ep3):
            p_ep3=percentile_score(ep3, eps3_ref, True)
            if not np.isnan(p_ep3): parts.append((p_ep3, 0.10))
        if parts:
            score = sum(v*w for v,w in parts) / sum(w for _,w in parts)
        else:
            score = np.nan
        scores.append(score)
        evidence.append("GOOD" if len(parts) >= 4 else "MODERATE" if len(parts) >= 2 else "LIMITED" if parts else "NO_DATA")
    out["growth_score"] = np.round(scores, 2)
    out["growth_evidence"] = evidence
    return out


def score_momentum(df: pd.DataFrame, momentum_df: pd.DataFrame) -> pd.DataFrame:
    """Momentum engine with reduced double-counting and liquidity confirmation."""
    out = df.copy()
    mom = momentum_df.copy() if isinstance(momentum_df, pd.DataFrame) else pd.DataFrame()
    if not mom.empty and "symbol" in mom.columns:
        cols = [c for c in ["symbol", "return_20d", "return_60d", "price_vs_ma20", "price_vs_ma60", "liquidity_state", "liquidity_flag", "zero_return_ratio_20d", "unique_price_ratio_20d"] if c in mom.columns]
        out = out.drop(columns=[c for c in cols if c != "symbol" and c in out.columns], errors="ignore")
        out = out.merge(mom[cols], on="symbol", how="left", suffixes=("", "_momv2"))

    # Trend acceleration is less redundant than counting MA20 and MA60 as separate
    # trend scores. It measures short-vs-long trend separation.
    out["trend_acceleration"] = pd.to_numeric(out.get("price_vs_ma20"), errors="coerce") - pd.to_numeric(out.get("price_vs_ma60"), errors="coerce")
    refs = {c: _reference_column(out, c) for c in ["return_20d", "return_60d", "price_vs_ma60", "trend_acceleration"]}
    scores, evidence, liq_flags = [], [], []
    for _, row in out.iterrows():
        comps=[]
        for col, w in [("return_20d",0.35),("return_60d",0.25),("price_vs_ma60",0.20),("trend_acceleration",0.20)]:
            v=num(row.get(col))
            if not np.isnan(v):
                p=percentile_score(v, refs[col], True, min_obs=8)
                if not np.isnan(p): comps.append((p,w))
        raw = sum(v*w for v,w in comps)/sum(w for _,w in comps) if comps else np.nan
        state=str(row.get("liquidity_state",row.get("liquidity_flag",""))).upper()
        if state in {"NO_TRADING_EVIDENCE","STALE"}:
            mult=0.50
        elif state=="LOW_ACTIVITY":
            mult=0.75
        elif state=="CAUTION":
            mult=0.90
        else:
            mult=1.00
        # If explicit liquidity ratios are available, confirm rather than blindly
        # trusting the categorical flag.
        zr=num(row.get("zero_return_ratio_20d")); up=num(row.get("unique_price_ratio_20d"))
        if not np.isnan(zr) and zr >= 0.80: mult=min(mult,0.50)
        elif not np.isnan(zr) and zr >= 0.60: mult=min(mult,0.75)
        if not np.isnan(up) and up <= 0.20: mult=min(mult,0.50)
        elif not np.isnan(up) and up <= 0.40: mult=min(mult,0.75)
        score=raw*mult if not np.isnan(raw) else np.nan
        scores.append(score)
        liq_flags.append(state or "NO_DATA")
        evidence.append("GOOD" if len(comps)>=4 and mult>=0.9 else "MODERATE" if len(comps)>=3 else "LIMITED" if comps else "NO_DATA")
    out["raw_momentum_score"] = np.round(scores,2)  # raw label retained for backward compatibility; score includes liquidity confirmation.
    out["momentum_score"] = np.round(scores,2)
    out["momentum_evidence"] = evidence
    out["liquidity_state"] = liq_flags
    return out


def score_bagger(df: pd.DataFrame) -> pd.DataFrame:
    """Final composite using the frozen RowletAI 25/20/20/20/15 weights."""
    out=df.copy()
    vals=[]; dims=[]; evidence=[]; signals=[]
    for _,row in out.iterrows():
        available={k:num(row.get(k)) for k in WEIGHTS}
        valid={k:v for k,v in available.items() if not np.isnan(v)}
        d=len(valid)
        dims.append(d)
        if d==5:
            score=sum(valid[k]*w for k,w in WEIGHTS.items())
            vals.append(float(np.clip(score,0,100)))
            evidence.append("HIGH")
            if score>=65: signals.append("STRONG_COMPOSITE")
            elif score>=50: signals.append("BALANCED_COMPOSITE")
            elif score>=35: signals.append("WEAK_COMPOSITE")
            else: signals.append("LOW_COMPOSITE")
        else:
            vals.append(np.nan)
            evidence.append("LOW" if d==3 else "MODERATE" if d==4 else "INSUFFICIENT")
            signals.append("INSUFFICIENT_EVIDENCE")
    out["bagger_score"]=np.round(vals,2)
    out["available_dimensions"]=dims
    out["evidence_level"]=evidence
    out["composite_signal"]=signals
    return out


def run_engine(fundamentals: pd.DataFrame, momentum: pd.DataFrame,
               risk: pd.DataFrame, profiles: pd.DataFrame | None = None,
               reports: Mapping[str, Any] | None = None,
               existing: pd.DataFrame | None = None) -> pd.DataFrame:
    """Run all five engines in dependency order."""
    f=fundamentals.copy()
    m=momentum.copy() if isinstance(momentum,pd.DataFrame) else pd.DataFrame()
    r=risk.copy() if isinstance(risk,pd.DataFrame) else pd.DataFrame()
    p=profiles.copy() if isinstance(profiles,pd.DataFrame) else pd.DataFrame()
    if "symbol" not in f.columns:
        raise ValueError("fundamentals must contain symbol")
    base=f.copy()
    if isinstance(existing, pd.DataFrame) and "symbol" in existing.columns:
        keep=[c for c in existing.columns if c not in base.columns and c != "symbol"]
        if keep:
            base=base.merge(existing[["symbol"]+keep],on="symbol",how="left")
    if not p.empty and "symbol" in p.columns:
        pc=[c for c in ["symbol","sector","industry","company_name","description"] if c in p.columns]
        base=base.merge(p[pc],on="symbol",how="left",suffixes=("","_profile"))
        for c in ["sector","industry","company_name","description"]:
            pc2=f"{c}_profile"
            if pc2 in base.columns:
                base[c]=base[c].where(base[c].notna() & base[c].astype(str).str.strip().ne(""),base[pc2]) if c in base.columns else base[pc2]
        base=base.drop(columns=[c for c in base.columns if c.endswith("_profile")],errors="ignore")
    base=score_risk(base,r)
    base=score_valuation(base,reports)
    base=score_growth(base,reports)
    base=score_momentum(base,m)
    base=score_bagger(base)
    return base


def validation_report(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Return a compact before/after audit table for all five dimensions."""
    keys=["growth_score","valuation_score","momentum_score","risk_score","risk_strength","bagger_score"]
    a=old.set_index("symbol") if "symbol" in old.columns else old.copy()
    b=new.set_index("symbol") if "symbol" in new.columns else new.copy()
    rows=[]
    for col in keys:
        if col not in a.columns or col not in b.columns: continue
        x=pd.to_numeric(a[col],errors="coerce"); y=pd.to_numeric(b[col],errors="coerce")
        common=pd.concat([x.rename("old"),y.rename("new")],axis=1).dropna()
        rows.append({
            "metric":col,
            "common":int(len(common)),
            "mean_old":float(common.old.mean()) if len(common) else np.nan,
            "mean_new":float(common.new.mean()) if len(common) else np.nan,
            "mean_abs_change":float((common.new-common.old).abs().mean()) if len(common) else np.nan,
            "changed_gt_5":float(((common.new-common.old).abs()>5).mean()*100) if len(common) else np.nan,
            "corr":float(common.old.corr(common.new)) if len(common)>=3 else np.nan,
        })
    return pd.DataFrame(rows)

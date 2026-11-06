import numpy as np
import pandas as pd
from scoring_engine_v3_final import (
    robust_percentile, growth_score, quality_score, valuation_score,
    momentum_score, risk_strength, dividend_score, bagger_score
)

def main():
    assert robust_percentile(range(1,21),20)==97.5
    fund=pd.DataFrame({
        'symbol':['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P'],
        'roe_ttm':np.linspace(.02,.20,16), 'roa_ttm':np.linspace(.01,.10,16),
        'pe_ttm':np.linspace(5,30,16), 'forward_pe':np.linspace(4,25,16),
        'pb_mrq':np.linspace(.5,5,16), 'yield_ttm':np.linspace(0,.08,16),
        'yoy_quarter_revenue_growth':np.linspace(-.2,.5,16),
        'yoy_quarter_earnings_growth':np.linspace(-.5,1.5,16),
    })
    mom=pd.DataFrame({'symbol':fund.symbol,'return_20d':np.linspace(-.2,.2,16),'return_60d':np.linspace(-.3,.3,16),'price_vs_ma60':np.linspace(-.2,.2,16),'price_vs_ma20':np.linspace(-.1,.1,16)})
    risk=pd.DataFrame({'symbol':fund.symbol,'volatility_20d':np.linspace(.01,.5,16),'volatility_60d':np.linspace(.02,.4,16),'max_drawdown_60d':np.linspace(-.5,-.01,16),'max_daily_loss_20d':np.linspace(-.15,-.01,16),'zero_return_ratio_20d':np.linspace(0,.6,16),'unique_price_ratio_20d':np.linspace(1,.4,16)})
    row=fund.iloc[-1].to_dict(); row.update(mom.iloc[-1].to_dict()); row.update(risk.iloc[-1].to_dict());
    q=quality_score(row,fund); g=growth_score(row,fund); v=valuation_score(row,fund); m=momentum_score(row,mom); r=risk_strength(row,risk); d=dividend_score(row,fund)
    assert all(0<=x<=100 for x in [q['quality_score'],g['growth_score'],v['valuation_score'],m['momentum_score'],r['risk_strength']])
    b=bagger_score({'growth_score':g['growth_score'],'quality_score':q['quality_score'],'valuation_score':v['valuation_score'],'momentum_score':m['momentum_score'],'risk_strength':r['risk_strength']})
    assert b['available_dimensions']==5 and np.isfinite(b['bagger_score'])
    # Missing dimension must never become zero.
    bm=bagger_score({'growth_score':80,'quality_score':70,'valuation_score':60,'momentum_score':50,'risk_strength':np.nan})
    assert np.isnan(bm['bagger_score']) and bm['available_dimensions']==4
    print('ALL V3 SCORING TESTS PASSED')

if __name__=='__main__': main()

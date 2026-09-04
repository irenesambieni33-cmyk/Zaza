"""RE-ZERO technical indicator engine.
Pure pandas/numpy indicators: trend, momentum, volatility, volume/flow,
market regime and crypto-specific statistics. No paid TA library required.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from config import *


def _true_range(high, low, close):
    prev = close.shift(1)
    return pd.concat([(high-low), (high-prev).abs(), (low-prev).abs()], axis=1).max(axis=1)


def _safe_div(a, b):
    return a / b.replace(0, np.nan)


def _ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def _rsi(close, n=14):
    d = close.diff()
    g = d.clip(lower=0).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = g / l.replace(0, np.nan)
    r = 100 - 100/(1+rs)
    r[(l==0)&(g>0)] = 100
    r[(g==0)&(l>0)] = 0
    return r


def _adx(high, low, close, n=14):
    tr = _true_range(high, low, close)
    up, down = high.diff(), -low.diff()
    plus = pd.Series(np.where((up>down)&(up>0), up, 0.0), index=close.index)
    minus = pd.Series(np.where((down>up)&(down>0), down, 0.0), index=close.index)
    atr = tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    p = 100*plus.ewm(alpha=1/n, adjust=False, min_periods=n).mean()/atr.replace(0,np.nan)
    m = 100*minus.ewm(alpha=1/n, adjust=False, min_periods=n).mean()/atr.replace(0,np.nan)
    dx = 100*(p-m).abs()/(p+m).replace(0,np.nan)
    return dx.ewm(alpha=1/n, adjust=False, min_periods=n).mean(), p, m


def _supertrend(high, low, close, atr, mult=3.0):
    hl2=(high+low)/2; bu=hl2+mult*atr; bl=hl2-mult*atr
    fu=pd.Series(np.nan,index=close.index); fl=pd.Series(np.nan,index=close.index); tr=pd.Series(np.nan,index=close.index)
    valid=atr.first_valid_index()
    if valid is None: return pd.Series(np.nan,index=close.index),tr
    s=close.index.get_loc(valid); fu.iloc[s]=bu.iloc[s]; fl.iloc[s]=bl.iloc[s]; tr.iloc[s]=1
    for i in range(s+1,len(close)):
        pc=close.iloc[i-1]; pu=fu.iloc[i-1]; pl=fl.iloc[i-1]
        fu.iloc[i]=bu.iloc[i] if pd.notna(bu.iloc[i]) and (pd.isna(pu) or bu.iloc[i]<pu or pc>pu) else pu
        fl.iloc[i]=bl.iloc[i] if pd.notna(bl.iloc[i]) and (pd.isna(pl) or bl.iloc[i]>pl or pc<pl) else pl
        prev=tr.iloc[i-1] if pd.notna(tr.iloc[i-1]) else 1
        tr.iloc[i]=1 if (pd.notna(pu) and close.iloc[i]>pu) else -1 if (pd.notna(pl) and close.iloc[i]<pl) else prev
    return pd.Series(np.where(tr>0,fl,fu),index=close.index),tr


def _psar(high, low, step=.02, max_af=.20):
    sar=pd.Series(np.nan,index=high.index); direction=pd.Series(1.0,index=high.index)
    if len(high)==0:return sar,direction
    sar.iloc[0]=low.iloc[0]; ep=high.iloc[0]; af=step; bull=True
    for i in range(1,len(high)):
        v=sar.iloc[i-1]+af*(ep-sar.iloc[i-1])
        if bull:
            v=min(v,low.iloc[i-1],low.iloc[i-2] if i>1 else low.iloc[i-1])
            if low.iloc[i]<v: bull=False; v=ep; ep=low.iloc[i]; af=step
            elif high.iloc[i]>ep: ep=high.iloc[i]; af=min(max_af,af+step)
        else:
            v=max(v,high.iloc[i-1],high.iloc[i-2] if i>1 else high.iloc[i-1])
            if high.iloc[i]>v: bull=True; v=ep; ep=high.iloc[i]; af=step
            elif low.iloc[i]<ep: ep=low.iloc[i]; af=min(max_af,af+step)
        sar.iloc[i]=v; direction.iloc[i]=1 if bull else -1
    return sar,direction


def _aroon(high, low, n=25):
    def up(x): return 100*(n-1-x.argmax())/(n-1) if len(x)==n else np.nan
    def dn(x): return 100*(n-1-x.argmin())/(n-1) if len(x)==n else np.nan
    return high.rolling(n,min_periods=n).apply(up,raw=True), low.rolling(n,min_periods=n).apply(dn,raw=True)


def _wma(series, period):
    weights=np.arange(1,period+1,dtype=float)
    return series.rolling(period,min_periods=period).apply(lambda x:float(np.dot(x,weights)/weights.sum()),raw=True)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy(); close=out.close.astype(float); high=out.high.astype(float); low=out.low.astype(float); open_=out.open.astype(float)
    volume=out.volume.astype(float) if "volume" in out else pd.Series(0.0,index=out.index)
    typical=(high+low+close)/3

    # Trend / moving averages
    for n in (5,9,10,20,21,34,50,55,89,100,144,200): out[f"ema{n}"]=_ema(close,n)
    for n in (20,50,100,200): out[f"sma{n}"]=close.rolling(n,min_periods=n).mean()
    out["hma20"]=_wma(2*_wma(close,10)-_wma(close,20),4)
    out["tema20"]=3*_ema(close,20)-3*_ema(_ema(close,20),20)+_ema(_ema(_ema(close,20),20),20)
    out["dema20"]=2*_ema(close,20)-_ema(_ema(close,20),20)
    out["ema_spread_pct"]=100*(out.ema20-out.ema50)/close.replace(0,np.nan)

    # RSI family
    out["rsi14"]=_rsi(close,14); out["rsi7"]=_rsi(close,7); out["rsi21"]=_rsi(close,21)
    out["stoch_rsi"]=(out.rsi14-out.rsi14.rolling(14,min_periods=14).min())/_safe_div(out.rsi14.rolling(14,min_periods=14).max()-out.rsi14.rolling(14,min_periods=14).min(),pd.Series(1,index=out.index))
    out["stoch_rsi"]*=100

    # MACD / PPO
    ef,es=_ema(close,12),_ema(close,26); out["macd"]=ef-es; out["macd_signal"]=_ema(out.macd,9); out["macd_hist"]=out.macd-out.macd_signal
    out["ppo"]=_safe_div(100*(ef-es),es); out["ppo_signal"]=_ema(out.ppo,9); out["ppo_hist"]=out.ppo-out.ppo_signal

    # Volatility
    tr=_true_range(high,low,close); out["tr"]=tr; out["atr14"]=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean(); out["atr_pct"]=100*out.atr14/close.replace(0,np.nan)
    out["natr14"]=out.atr_pct
    sd=close.rolling(20,min_periods=20).std(ddof=0); mid=close.rolling(20,min_periods=20).mean(); out["bb_mid"]=mid; out["bb_upper"]=mid+2*sd; out["bb_lower"]=mid-2*sd; out["bb_width"]=_safe_div(out.bb_upper-out.bb_lower,mid)
    out["bb_percent"]=_safe_div(close-out.bb_lower,out.bb_upper-out.bb_lower)
    out["std20_pct"]=100*sd/close.replace(0,np.nan)
    atr_base=out.atr14.rolling(50,min_periods=50).median(); out["volatility_ratio"]=_safe_div(out.atr14,atr_base)
    out["realized_vol20"]=close.pct_change().rolling(20,min_periods=20).std()*np.sqrt(365*24)*100
    out["realized_vol60"]=close.pct_change().rolling(60,min_periods=60).std()*np.sqrt(365*24)*100

    # ADX / DI / Aroon / trend strength
    out["adx14"],out["di_plus"],out["di_minus"]=_adx(high,low,close,14); out["dx14"]=100*(out.di_plus-out.di_minus).abs()/(out.di_plus+out.di_minus).replace(0,np.nan)
    out["aroon_up"],out["aroon_down"]=_aroon(high,low,25); out["aroon_osc"]=out.aroon_up-out.aroon_down
    out["vortex_plus"]=((high-low.shift(1)).abs()).rolling(14,min_periods=14).sum()/tr.rolling(14,min_periods=14).sum().replace(0,np.nan)
    out["vortex_minus"]=((low-high.shift(1)).abs()).rolling(14,min_periods=14).sum()/tr.rolling(14,min_periods=14).sum().replace(0,np.nan)
    out["vortex_diff"]=out.vortex_plus-out.vortex_minus

    # Stochastic / momentum oscillators
    hh=high.rolling(14,min_periods=14).max(); ll=low.rolling(14,min_periods=14).min(); rawk=100*(close-ll)/(hh-ll).replace(0,np.nan)
    out["stoch_k"]=rawk.rolling(3,min_periods=3).mean(); out["stoch_d"]=out.stoch_k.rolling(3,min_periods=3).mean()
    out["williams_r"]=-100*(hh-close)/(hh-ll).replace(0,np.nan); out["roc12"]=100*(close/close.shift(12)-1); out["roc24"]=100*(close/close.shift(24)-1)
    out["mom10"]=close-close.shift(10)
    tp_mean=typical.rolling(20,min_periods=20).mean(); mad=typical.rolling(20,min_periods=20).apply(lambda x:np.mean(np.abs(x-np.mean(x))),raw=True); out["cci20"]=(typical-tp_mean)/(0.015*mad.replace(0,np.nan))
    # Ultimate oscillator
    prev_close=close.shift(1); bp=close-pd.concat([low,prev_close],axis=1).min(axis=1); tr_u=pd.concat([high,prev_close],axis=1).max(axis=1)-pd.concat([low,prev_close],axis=1).min(axis=1)
    out["ultimate_osc"]=(4*bp.rolling(7,min_periods=7).sum()/tr_u.rolling(7,min_periods=7).sum().replace(0,np.nan)+2*bp.rolling(14,min_periods=14).sum()/tr_u.rolling(14,min_periods=14).sum().replace(0,np.nan)+bp.rolling(28,min_periods=28).sum()/tr_u.rolling(28,min_periods=28).sum().replace(0,np.nan))/7*100
    out["trix"]=_ema(_ema(_ema(close,15),15),15).pct_change(fill_method=None)*100
    # Fisher transform
    med=(high+low)/2; mn=med.rolling(10,min_periods=10).min(); mx=med.rolling(10,min_periods=10).max(); x=2*((med-mn)/(mx-mn).replace(0,np.nan)-.5); x=x.clip(-.999,.999); out["fisher10"]=0.5*np.log((1+x)/(1-x))
    out["awesome_osc"]=(_wma(typical,5)-_wma(typical,34))

    # CCI-derived DPO and KST
    out["dpo20"]=close-close.shift(11).rolling(20,min_periods=20).mean()
    def roc(n): return close.pct_change(n)*100
    out["kst"]=roc(10).rolling(10,min_periods=10).sum()+2*roc(15).rolling(10,min_periods=10).sum()+3*roc(20).rolling(10,min_periods=10).sum()+4*roc(30).rolling(15,min_periods=15).sum()

    # Keltner / Donchian / Supertrend / PSAR / Ichimoku
    ema_typ=_ema(typical,20); out["kc_mid"]=ema_typ; out["kc_upper"]=ema_typ+2*out.atr14; out["kc_lower"]=ema_typ-2*out.atr14
    out["donchian_high20"]=high.rolling(20,min_periods=20).max(); out["donchian_low20"]=low.rolling(20,min_periods=20).min(); out["donchian_mid20"]=(out.donchian_high20+out.donchian_low20)/2
    out["donchian_pos"]=_safe_div(close-out.donchian_low20,out.donchian_high20-out.donchian_low20)
    out["supertrend"],out["supertrend_dir"]=_supertrend(high,low,close,out.atr14,3.0); out["psar"],out["psar_dir"]=_psar(high,low)
    conv=(high.rolling(9,min_periods=9).max()+low.rolling(9,min_periods=9).min())/2; base=(high.rolling(26,min_periods=26).max()+low.rolling(26,min_periods=26).min())/2; spanb=(high.rolling(52,min_periods=52).max()+low.rolling(52,min_periods=52).min())/2; spana=(conv+base)/2
    out["ichimoku_conversion"]=conv; out["ichimoku_base"]=base; out["ichimoku_span_a"]=spana; out["ichimoku_span_b"]=spanb; out["ichimoku_cloud_top"]=pd.concat([spana,spanb],axis=1).max(axis=1); out["ichimoku_cloud_bottom"]=pd.concat([spana,spanb],axis=1).min(axis=1); out["ichimoku_bias"]=np.where(close>out.ichimoku_cloud_top,1,np.where(close<out.ichimoku_cloud_bottom,-1,0))

    # Defragment before the larger volume/flow block for Streamlit performance.
    out = out.copy()
    # Volume / money flow
    direction=np.sign(close.diff()).fillna(0); out["obv"]=(direction*volume.fillna(0)).cumsum(); mf=((close-low)-(high-close))/(high-low).replace(0,np.nan); out["cmf20"]=(mf*volume).rolling(20,min_periods=20).sum()/volume.rolling(20,min_periods=20).sum().replace(0,np.nan)
    pos=(typical*volume).where(typical.diff()>0,0).rolling(14,min_periods=14).sum(); neg=(typical*volume).where(typical.diff()<0,0).rolling(14,min_periods=14).sum(); ratio=pos/neg.replace(0,np.nan); out["mfi14"]=100-100/(1+ratio); out.loc[(neg==0)&(pos>0),"mfi14"]=100; out.loc[(pos==0)&(neg>0),"mfi14"]=0
    out["rel_volume20"]=volume/volume.rolling(20,min_periods=20).mean().replace(0,np.nan); out["vwap"]=(typical*volume).cumsum()/volume.replace(0,np.nan).cumsum()
    out["volume_z20"]=(volume-volume.rolling(20,min_periods=20).mean())/volume.rolling(20,min_periods=20).std(ddof=0).replace(0,np.nan)
    out["eom14"]=((high-low)*((high.diff()).abs()+(low.diff()).abs())/(2*volume.replace(0,np.nan))).rolling(14,min_periods=14).mean()
    out["force_index13"]=(close.diff()*volume).ewm(span=13,adjust=False,min_periods=13).mean()
    out["bull_power13"]=high-_ema(close,13); out["bear_power13"]=low-_ema(close,13)

    # Defragment again before price-action statistics.
    out = out.copy()
    # Price action / crypto-friendly statistics
    out["return1"] = close.pct_change(); out["log_return"] = np.log(close/close.shift(1)); out["range_pct"]=(high-low)/close.replace(0,np.nan)*100
    out["body_pct"]=(close-open_)/open_.replace(0,np.nan)*100; out["upper_wick_pct"]=(high-pd.concat([open_,close],axis=1).max(axis=1))/close*100; out["lower_wick_pct"]=(pd.concat([open_,close],axis=1).min(axis=1)-low)/close*100
    out["zscore20"]=(close-mid)/sd.replace(0,np.nan); out["skew20"]=out.log_return.rolling(20,min_periods=20).skew(); out["kurtosis20"]=out.log_return.rolling(20,min_periods=20).kurt()
    out["drawdown"] = close/close.cummax()-1
    # rolling high/low breakout distance
    out["distance_high20_pct"]=(close/out.donchian_high20-1)*100; out["distance_low20_pct"]=(close/out.donchian_low20-1)*100
    return out

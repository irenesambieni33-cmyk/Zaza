"""RE-ZERO application controller."""
import logging
import datetime as dt
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from analysis import analyze_multi_timeframe
from config import APP_NAME, CACHE_TTL_SECONDS, INSTRUMENTS
from timeframe_policy import EXECUTION_TIMEFRAMES
from data import fetch_instrument
from interface import apply_css, render_dashboard
from crypto_data import fetch_btc_snapshot
from timing import timing_assessment
from trade_manager import TradeManager
from weekend_market import weekend_policy
from macro_context import fetch_macro_events
from browser_notifications import render_notification_control
from performance import backtest_trade_plans
from validation_engine import validate_backtest
from version_info import VERSION, BUILD_STATUS
logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title=f"{APP_NAME} {VERSION}",page_icon="📊",layout="wide",initial_sidebar_state="expanded"); apply_css()
@st.cache_data(ttl=CACHE_TTL_SECONDS,show_spinner=False)
def load_market(instrument): return fetch_instrument(instrument)
def main():
    st.sidebar.header("⚙️ Paramètres")
    st.sidebar.caption(f"{APP_NAME} {VERSION} • {BUILD_STATUS}")
    instrument=st.sidebar.selectbox("Marché",list(INSTRUMENTS),index=2)
    execution_tf=st.sidebar.selectbox("⏱️ Timeframe d’exécution",EXECUTION_TIMEFRAMES,index=1,help="Le choix est respecté. RE-ZERO adapte automatiquement contexte, structure, setup et trigger.")
    capital=st.sidebar.number_input("Capital de référence",min_value=0.,value=1000.,step=100.)
    st.sidebar.caption("Risque 1%/trade • R:R minimum 1:2 • maximum 3 trades/jour")
    st.sidebar.success("🔐 MODE ANALYSE SÉCURISÉ")
    st.sidebar.subheader("🔔 Notifications")
    render_notification_control(True)
    monitor=st.sidebar.checkbox("Surveillance automatique",value=False)
    refresh=st.sidebar.select_slider("Fréquence de scan",options=[30,60,120,300],value=60,format_func=lambda x:f"{x}s")
    scan_start=st.sidebar.time_input("Début fenêtre",value=dt.time(14,0)); scan_end=st.sidebar.time_input("Fin fenêtre",value=dt.time(17,30))
    if st.sidebar.button("🔄 Actualiser les données"): load_market.clear(); st.rerun()
    wp=weekend_policy(instrument)
    if wp.get("weekend"): st.sidebar.info(f"📅 Week-end : {wp['status']}. {wp['note']}")
    if monitor: st_autorefresh(interval=refresh*1000,key="rezero_refresh"); load_market.clear(); st.sidebar.success(f"🟢 Scan toutes les {refresh}s")
    else: st.sidebar.caption("Surveillance automatique désactivée.")
    st.markdown(f'<div class="hero"><h1>{APP_NAME}</h1><div>{INSTRUMENTS[instrument]["label"]} • Exécution <b>{execution_tf}</b> • Maximum 3 trades/jour • R:R ≥ 1:2</div></div>',unsafe_allow_html=True)
    if "trade_manager" not in st.session_state: st.session_state.trade_manager=TradeManager()
    if not st.session_state.get("analysis_started",False):
        st.info("Configure le marché et le timeframe, puis démarre l’analyse.")
        if st.button("🚀 DÉBUTER L’ANALYSE",type="primary",width="stretch"): st.session_state.analysis_started=True; st.rerun()
        return
    try:
        with st.spinner(f"Analyse {execution_tf} + contexte multi-timeframe en cours…"): frames,warnings,used_proxy=load_market(instrument)
        if used_proxy: st.warning("XAU/USD : GC=F utilisé comme proxy futures, pas comme spot.")
        for k,v in warnings.items():
            if k!="global": st.caption(v)
        if not frames: st.error("Impossible de récupérer les données de marché."); return
        result=analyze_multi_timeframe(frames,execution_tf=execution_tf)
        macro=fetch_macro_events(days=7); crypto=fetch_btc_snapshot() if instrument=="BTC/USD" else None
        if st.sidebar.button(f"🧪 Validation statistique {execution_tf}"):
            bt=backtest_trade_plans(frames.get(execution_tf),execution_tf,horizon=16,max_samples=160,step=4,instrument=instrument)
            st.subheader(f"🧪 VALIDATION {execution_tf}")
            if bt.get("ok"):
                rows=bt.get("rows",[]); vr=validate_backtest(rows,n_trials=1) if rows else {"verdict":"ÉCHANTILLON TROP PETIT","robustness_score":0}
                a,b,c,d=st.columns(4); a.metric("Trades",bt.get("trades",0)); b.metric("Expectancy",f'{bt.get("expectancy_r",0):+.2f}R'); c.metric("Robustesse",f'{vr.get("robustness_score",0):.0f}/100'); d.metric("Verdict",vr.get("verdict","—"))
            else: st.warning(bt.get("reason","Validation indisponible."))
        price=next((float(frames[tf].close.iloc[-1]) for tf in [execution_tf,"M5","M15","H1","H4","D1"] if tf in frames and not frames[tf].empty),None)
        if price is None: st.error("Aucun prix exploitable."); return
        render_dashboard(instrument,price,result,capital,crypto_snapshot=crypto,monitor=monitor,custom_window=(scan_start.strftime("%H:%M"),scan_end.strftime("%H:%M")),trade_manager=st.session_state.trade_manager,macro_events=macro,execution_tf=execution_tf)
    except Exception:
        logging.exception("Unexpected application error"); st.error("Erreur interne pendant l’analyse. Le détail est disponible dans les logs.")
if __name__=="__main__": main()

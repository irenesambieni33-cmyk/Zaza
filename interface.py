"""RE-ZERO Streamlit dashboard, dynamic execution timeframe and safety-first presentation."""
from __future__ import annotations
import math
from typing import Dict
import plotly.graph_objects as go
import streamlit as st
from config import APP_NAME, APP_SUBTITLE, TIMEFRAMES
from timeframe_policy import profile_label
from risk import build_setup, build_step_up, risk_summary
from setup_quality import evaluate_setup_quality
from safety import safety_gate
from timing import timing_assessment
from alerts import build_alert, send_telegram
from performance import backtest_trade_plans
from liquidity import build_liquidity_map
from trade_manager import TradeManager
from macro_context import macro_assessment
from browser_notifications import notify_opportunity
from decision_engine import decide
from session_controller import session_status

def _fmt(v,digits=5):
    try:
        if v is None or not math.isfinite(float(v)): return "—"
        return f"{float(v):,.{digits}f}"
    except (TypeError,ValueError): return "—"

def decision_badge(d): return {"ACHAT":"🟢 ACHAT","VENTE":"🔴 VENTE","ATTENDRE":"🟠 ATTENDRE","AUCUN SETUP":"⚪ AUCUN SETUP"}.get(d,d)

def decision_card(d, execution_tf="M15"):
    st.markdown(f'''<div class="decision-card"><div class="decision-label">DÉCISION DU MOTEUR</div><div class="decision-value">{decision_badge(d)}</div><div class="decision-note">Exécution sélectionnée : <b>{execution_tf}</b>. La hiérarchie MTF est relative à ce choix.</div></div>''',unsafe_allow_html=True)

def apply_css():
    st.markdown("""<style>.block-container{max-width:1450px;padding-top:1rem;padding-bottom:3rem}.hero,.decision-card{padding:1.2rem 1.4rem;border:1px solid rgba(128,128,128,.22);border-radius:18px;margin-bottom:1rem}.decision-card{text-align:center;border-width:2px}.decision-label{font-size:.8rem;letter-spacing:.12em;opacity:.7;font-weight:700}.decision-value{font-size:2rem;font-weight:900;margin:.35rem}.decision-note{opacity:.75}</style>""",unsafe_allow_html=True)

def render_chart(tf_result:Dict, liquidity=None):
    df=tf_result.get("data")
    if df is None or df.empty: st.info("Pas assez de données pour le graphique."); return
    d=df.tail(180); fig=go.Figure(go.Candlestick(x=d.index,open=d.open,high=d.high,low=d.low,close=d.close,name="Bougies"))
    for col,name,width in [("ema20","EMA20",2.5),("ema50","EMA50",2.5),("sma200","SMA200",3)]:
        if col in d: fig.add_trace(go.Scatter(x=d.index,y=d[col],mode="lines",name=name,line=dict(width=width)))
    for z in (tf_result.get("zones") or {}).get("supports",[])[:3]: fig.add_hline(y=z["price"],line_dash="dot",annotation_text=f"Support {_fmt(z['price'])}")
    for z in (tf_result.get("zones") or {}).get("resistances",[])[:3]: fig.add_hline(y=z["price"],line_dash="dot",annotation_text=f"Résistance {_fmt(z['price'])}")
    for p in (liquidity or {}).get("pools",[])[:6]: fig.add_hline(y=p["price"],line_dash="dash",annotation_text=f"💧 {_fmt(p['price'])}")
    fig.update_layout(height=650,xaxis_rangeslider_visible=False,hovermode="x unified",margin=dict(l=20,r=20,t=30,b=20))
    st.plotly_chart(fig,width="stretch",config={"responsive":True,"displaylogo":False,"scrollZoom":True})

def render_dashboard(instrument,price,result,capital,crypto_snapshot=None,monitor=False,custom_window=None,trade_manager=None,macro_events=None,execution_tf="M15"):
    trade_manager=trade_manager or TradeManager(); policy=result.get("policy",{}) or {}; setup_tf=execution_tf
    st.markdown(f'<div class="hero"><h1>{APP_NAME}</h1><div>{APP_SUBTITLE}</div><small>{profile_label(execution_tf)}</small></div>',unsafe_allow_html=True)
    ss=session_status(instrument,custom_window=custom_window,trades_today=trade_manager.trades_today())
    a,b,c,d=st.columns(4); a.metric("Session",ss["status"]); b.metric("Temps restant",ss["time_remaining"]); c.metric("Trades aujourd’hui",f'{ss["trades_today"]}/{ss["max_trades"]}'); d.metric("Entrées restantes",ss["remaining_allowance"])
    st.caption(f'🕒 Fenêtre {ss["start"]}–{ss["end"]} • Entrées autorisées : {"OUI" if ss["can_enter"] else "NON"}')
    a,b,c,d=st.columns(4); a.metric("Instrument",instrument); b.metric("Prix",_fmt(price)); c.metric("Score",f'{result.get("score",0):+.1f}'); d.metric("Qualité scénario",f'{result.get("confidence",0):.0f}/100')

    macro=macro_assessment(instrument,macro_events or {"events":[]}); st.subheader("🌍 CONTEXTE MACRO"); a,b,c=st.columns(3); a.metric("Risque",macro.get("risk","NORMAL")); b.metric("Prochaine annonce",(macro.get("nearest") or {}).get("title","Aucune")); c.metric("Échéance",f'{macro.get("minutes_to_event"):.0f} min' if macro.get("minutes_to_event") is not None else "—")
    for x in macro.get("reasons",[]): st.caption("• "+x)

    st.subheader("🧭 ANALYSE MULTI-TIMEFRAME"); st.caption(result.get("explanation",""))
    cols=st.columns(min(6,max(1,len(result.get("timeframes",{})))))
    for col,tf in zip(cols,result.get("timeframes",{})):
        r=result["timeframes"][tf]
        with col:
            st.markdown(f"**{tf}**"); st.write("Direction:",r.get("direction","NEUTRE") if r.get("available") else "INDISPONIBLE"); st.write("Score:",f'{r.get("score",0):+.1f}'); st.caption(f'Qualité {r.get("confidence",0):.0f}/100 • {r.get("trend","—")}')
    er=result.get("timeframes",{}).get(execution_tf,{}) or {}; rg=er.get("regime",{}) or {}; dq=er.get("data_quality",{}) or {}
    flow=er.get("orderflow",{}) or {}; st.subheader("⚖️ PRESSION / ORDERFLOW")
    if flow.get("ok"):
        a,b,c=st.columns(3); a.metric("Acheteurs",f'{flow.get("buyers",0):.1f}%'); b.metric("Vendeurs",f'{flow.get("sellers",0):.1f}%'); c.metric("Biais",flow.get("bias","ÉQUILIBRE")); st.progress(int(max(0,min(100,flow.get("buyers",50)))))

    liquidity=build_liquidity_map(er.get("data") if er.get("available") else None,er.get("structure_data",{}),er.get("indicators",{}).get("atr14"),execution_tf=execution_tf)
    timing=timing_assessment(instrument,er,er.get("data") if er.get("available") else None,custom_window=custom_window,execution_tf=execution_tf)
    decision_guard=decide(result,rg,dq,macro.get("risk","NORMAL"),liquidity=liquidity); decision_card(result.get("decision"),execution_tf)
    st.subheader("🧠 GARDE DE DÉCISION"); a,b,c=st.columns(3); a.metric("Scénario",decision_guard.get("scenario","NEUTRE")); b.metric("Statut",decision_guard.get("status","REJETÉ")); c.metric("Données",f'{dq.get("score",0):.0f}/100')
    for x in decision_guard.get("hard_blocks",[]): st.error("⛔ "+x)
    for x in decision_guard.get("soft_warnings",[]): st.warning("⚠️ "+x)

    setup=None
    if trade_manager.active is None and ss["can_enter"] and decision_guard.get("status") in {"CANDIDAT","CANDIDAT FORT"} and result.get("decision") in {"ACHAT","VENTE"} and er.get("available"):
        setup=build_setup(er.get("price",price),er.get("indicators",{}).get("atr14"),er.get("structure_data",{}),result["decision"],er.get("zones",{}))
        if not setup.get("valid"): setup=None
    quality=evaluate_setup_quality(result,setup,liquidity)
    gate=safety_gate(setup if trade_manager.active is None else None,quality if trade_manager.active is None else {"approved":False},capital,open_risk_fraction=0.0)

    st.subheader("💧 LIQUIDITÉ")
    if liquidity.get("ok"):
        a,b,c=st.columns(3); a.metric("Pools",len(liquidity.get("pools",[]))); a2=liquidity.get("nearest") or {}; b.metric("Plus proche",_fmt(a2.get("price"))); c.metric("Événements sweep",len(liquidity.get("events",[])))
        if liquidity.get("pools"): st.dataframe({"Type":[p["type"] for p in liquidity["pools"][:8]],"Prix":[_fmt(p["price"]) for p in liquidity["pools"][:8]],"Touches":[p["touches"] for p in liquidity["pools"][:8]],"Force":[f'{p["strength"]:.0f}/100' for p in liquidity["pools"][:8]]},width="stretch",hide_index=True)
        for e in liquidity.get("events",[]): st.caption(f'⚡ SWEEP {e["side"]} à {_fmt(e["price"])} • reclaim={e["reclaim"]} • displacement={e["displacement"]}')
        st.caption(liquidity.get("note",""))
    else: st.info("Carte de liquidité indisponible.")

    st.subheader("⏱️ TIMING / VOLATILITÉ"); a,b,c,d=st.columns(4); a.metric("Fenêtre",timing.get("status","ATTENTE")); b.metric("Score",f'{timing.get("score",0):.0f}/100'); c.metric("Régime",timing.get("profile",{}).get("regime","INCONNU")); d.metric("Heure",timing.get("local_time","—"))
    st.caption(timing.get("note",""))

    st.subheader(f"📊 GRAPHIQUE {execution_tf}"); available=[tf for tf,r in result.get("timeframes",{}).items() if r.get("available")]; chart_tf=st.selectbox("Timeframe du graphique",available,index=available.index(execution_tf) if execution_tf in available else 0) if available else None
    if chart_tf: render_chart(result["timeframes"][chart_tf],liquidity if chart_tf==execution_tf else None)

    st.subheader(f"🎯 PLAN DE TRADE {execution_tf}")
    if setup: a,b,c,d,e=st.columns(5); a.metric("ENTRY",_fmt(setup["entry"])); b.metric("SL",_fmt(setup["sl"])); c.metric("TP1",_fmt(setup["tp1"])); d.metric("TP2",_fmt(setup["tp2"])); e.metric("R:R",f'1:{setup["rr1"]:.1f} / 1:{setup["rr2"]:.1f}')
    else: st.info("Aucun plan valide. RE-ZERO ne force pas de trade pour remplir un tableau, civilisation oblige.")

    st.subheader("🧠 QUALITÉ DU SETUP"); a,b,c=st.columns(3); a.metric("Score",f'{quality.get("score",0):.0f}/100'); b.metric("Classe",quality.get("grade","REJETÉ")); c.metric("Autorisation","OUI" if quality.get("approved") else "NON")
    for x in quality.get("reasons",[]): st.caption("• "+x)
    st.subheader("🛡️ SAFETY GATE"); st.write("Statut :", "🟢 VALIDÉ" if gate.get("approved") else "🔴 BLOQUÉ")
    for k,v in gate.get("checks",{}).items(): st.caption(f'{"✅" if v else "❌"} {k}')

    alert=build_alert(instrument,result,quality,gate,timing,setup) if trade_manager.active is None else {"active":False,"message":"Trade actif : aucune nouvelle alerte d’entrée."}
    notify_key=f'{instrument}|{execution_tf}|{alert.get("direction")}|{round(alert.get("quality",0))}|{(alert.get("setup") or {}).get("entry")}'
    notify_opportunity(alert,notify_key)
    st.subheader("🚨 ALERTES"); st.success(alert["message"]) if alert.get("active") else st.info(alert.get("message","Aucune alerte."))
    if alert.get("active") and monitor:
        if st.session_state.get("last_alert_key")!=notify_key:
            st.toast(alert["message"],icon="🚨"); st.session_state["last_alert_key"]=notify_key
            try:
                token=st.secrets.get("TELEGRAM_BOT_TOKEN",""); chat=st.secrets.get("TELEGRAM_CHAT_ID","")
                if token and chat: send_telegram(alert,token,chat)
            except Exception: pass

    if trade_manager.active is None and setup and quality.get("approved") and gate.get("approved") and alert.get("active"):
        rs=risk_summary(capital,setup["entry"],setup["sl"]); st.subheader("🔒 SUIVI PAPER"); st.caption("Aucun ordre broker réel n'est envoyé.")
        if st.button("🔒 J'AI PLACÉ CE TRADE — DÉMARRER LE SUIVI",type="primary",width="stretch"):
            opened=trade_manager.open(instrument,setup,rs["units"],quality,liquidity_note=(liquidity.get("nearest") or {}).get("type",""))
            if opened.get("ok"): st.toast("Trade PAPER pris.",icon="🔒"); st.rerun()
            else: st.error(opened.get("reason","Impossible d'ouvrir la position."))

    st.subheader("🔒 POSITION EN COURS")
    if trade_manager.active:
        t=trade_manager.active; sign=1 if t.direction=="ACHAT" else -1; r=sign*(float(t.current_price)-t.entry)/abs(t.entry-t.sl) if abs(t.entry-t.sl)>0 else 0
        a,b,c,d=st.columns(4); a.metric("Position",f'{t.direction} {t.symbol}'); b.metric("R",f'{r:+.2f}R'); c.metric("TP2",_fmt(t.tp2)); d.metric("SL",_fmt(t.sl)); st.success("Position verrouillée jusqu’à TP2 ou SL. Aucun nouveau trade n’est proposé.")
    else: st.caption("Aucune position active.")

    st.subheader("📈 STEP-UP");
    for step in build_step_up(setup).get("steps",[]): st.write(f'**{step["name"]}** • {step["trigger_text"]} {_fmt(step["trigger"])} • {step["action"]}')
    st.subheader("📊 PERFORMANCE PAPER"); perf=trade_manager.snapshot().get("performance",{}); a,b,c,d=st.columns(4); a.metric("Trades clôturés",perf.get("trades",0)); b.metric("Win rate",f'{perf.get("win_rate",0):.1f}%'); c.metric("Net P&L",f'{perf.get("net_pnl",0):+.2f}'); d.metric("Profit factor", "∞" if perf.get("profit_factor")==float("inf") else f'{perf.get("profit_factor",0):.2f}')
    st.subheader("🧩 STRUCTURE"); sd=er.get("structure_data",{}) or {}; a,b,c,d=st.columns(4); a.metric("HH",sd.get("hh",0)); b.metric("HL",sd.get("hl",0)); c.metric("LH",sd.get("lh",0)); d.metric("LL",sd.get("ll",0)); st.write("BOS:",", ".join(sd.get("bos",[])) or "Aucun récent"); st.write("CHoCH:",", ".join(sd.get("choch",[])) or "Aucun récent")
    st.subheader("📐 FIBONACCI"); fib=er.get("fib",{}); st.dataframe({"Niveau":list(fib.get("levels",{}).keys()),"Prix":[_fmt(v) for v in fib.get("levels",{}).values()]},width="stretch",hide_index=True) if fib.get("levels") else st.info("Pas assez de swings.")
    st.subheader("🧪 RÉGIME & DONNÉES"); a,b,c=st.columns(3); a.metric("Régime",rg.get("base","INCONNU")); b.metric("Volatilité",rg.get("volatility","—")); c.metric("Qualité données",f'{dq.get("score",0):.0f}/100')
    st.caption(rg.get("note",""));
    if dq.get("issues"): st.caption("Audit: "+" • ".join(dq["issues"][:5]))
    if setup: rs=risk_summary(capital,setup["entry"],setup["sl"]); st.subheader("💰 RISQUE"); a,b,c=st.columns(3); a.metric("Risque",f'{rs["risk_amount"]:,.2f}'); b.metric("Distance SL",_fmt(rs["distance"])); c.metric("Unités théoriques",f'{rs["units"]:,.2f}')
    st.caption("Score de qualité ≠ probabilité de gain. Les données publiques ne permettent pas de voir des ordres cachés. Aucun ordre broker réel n'est exécuté.")

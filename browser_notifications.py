"""Browser notification bridge.
Browser notifications require HTTPS and notification permission. Background push is provider-dependent;
RE-ZERO also supports Telegram through secrets when configured.
"""
from __future__ import annotations
import streamlit as st

def render_notification_control(enabled: bool=True):
    st.html(f'''<div style="font-family:Arial,sans-serif;padding:4px 0"><button id="rz-btn" style="padding:10px 14px;border-radius:10px;border:1px solid #888;background:#fff;cursor:pointer;font-weight:700">🔔 Activer RE-ZERO</button><div id="rz-status" style="margin-top:6px;font-size:13px;opacity:.75"></div></div><script>
const b=document.getElementById('rz-btn'),s=document.getElementById('rz-status');
function state(){{if(!('Notification' in window)){{s.textContent='❌ Notifications non supportées';return}} s.textContent='Permission: '+Notification.permission+' • HTTPS: '+(location.protocol==='https:'?'OK':'NON'); if(Notification.permission==='granted') b.textContent='🔔 Notifications activées';}}
b.onclick=async()=>{{try{{const p=await Notification.requestPermission();state();if(p==='granted')new Notification('RE-ZERO',{{body:'Notifications activées pour cette session.',tag:'rezero-enabled'}})}}catch(e){{s.textContent='❌ '+e}}}};state();
</script>''', unsafe_allow_javascript=True)

def notify_opportunity(alert:dict,key:str):
    if not alert.get('active'): return
    s=alert.get('setup',{}) or {}; title=f"RE-ZERO • {alert.get('instrument','')} {alert.get('direction','')}"; body=f"Qualité {alert.get('grade','')} {float(alert.get('quality',0)):.0f}/100 | Entry {s.get('entry','—')} | SL {s.get('sl','—')} | TP2 {s.get('tp2','—')}"
    st.html(f'''<script>try{{const k={key!r};if('Notification' in window&&Notification.permission==='granted'&&localStorage.getItem('rezero_alert')!==k){{new Notification({title!r},{{body:{body!r},tag:'rezero-opportunity',renotify:true}});localStorage.setItem('rezero_alert',k);}}}}catch(e){{}}</script>''', unsafe_allow_javascript=True)

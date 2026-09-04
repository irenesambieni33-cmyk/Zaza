"""Trading-session and daily trade-limit controller. Informational, no broker execution."""
from __future__ import annotations
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from typing import Dict
from config import MAX_TRADES_PER_DAY
from timing import in_window, LOCAL_TZ

DEFAULT_SESSION = {"EUR/USD":("14:00","17:30"),"XAU/USD":("14:00","17:30"),"BTC/USD":("14:00","18:00")}

def session_status(instrument:str, now:datetime|None=None, custom_window:tuple[str,str]|None=None, trades_today:int=0)->Dict:
    now=now or datetime.now(ZoneInfo(LOCAL_TZ)); window=custom_window or DEFAULT_SESSION.get(instrument,("14:00","17:30")); active=in_window(now,*window)
    end=datetime.combine(now.date(), time.fromisoformat(window[1]),tzinfo=now.tzinfo)
    if window[1] <= window[0] and now.time().strftime('%H:%M') >= window[0]: end += timedelta(days=1)
    remaining=max(0,int((end-now).total_seconds())) if active else 0
    left=max(0,MAX_TRADES_PER_DAY-int(trades_today))
    return {"active":active,"status":"ACTIVE" if active else "CLOSED","start":window[0],"end":window[1],"seconds_remaining":remaining,"time_remaining":f"{remaining//3600:02d}:{(remaining%3600)//60:02d}" if active else "—","trades_today":int(trades_today),"remaining_allowance":left,"max_trades":MAX_TRADES_PER_DAY,"can_enter":active and left>0}

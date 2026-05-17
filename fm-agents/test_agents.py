import json
from agents.all_agents import run_l5_sentiment

state = {
    "macro_context": {"domestic_floor_active": True},
    "news_headlines": ["Headline 1 'with quotes'", 'Headline 2 "with double quotes"'],
    "event_context": {},
    "symbol": "NIFTY 50"
}

try:
    print(run_l5_sentiment(state, None))
except Exception as e:
    print("Error:", e)

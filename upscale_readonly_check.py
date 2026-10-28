"""Upscale API read-only connectivity check. No order endpoints are called."""
import json,os,urllib.request,urllib.error
BASE="https://api.upscale.trade"
key=os.environ.get("UPSCALE_API_KEY","").strip()
if not key:raise SystemExit("Missing UPSCALE_API_KEY secret")
if key.lower().startswith("bearer "):raise SystemExit("Secret must contain raw API key, not Bearer prefix")
if not key.startswith("usk_"):raise SystemExit("API key format unexpected: expected usk_ prefix (key hidden)")
def get(path):
 req=urllib.request.Request(BASE+path,headers={"Authorization":"Bearer "+key,"Accept":"application/json"})
 try:
  with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)
 except urllib.error.HTTPError as e:
  raise RuntimeError(f"Upscale GET {path}: HTTP {e.code}; check key permissions, account API Trading, and IP restrictions (body hidden)") from None
accounts=get("/accounts/with-risk-status")
if not isinstance(accounts,list):raise RuntimeError("Unexpected accounts payload")
demos=[a for a in accounts if a.get("type")=="demo" and a.get("apiTrading") and a.get("status")=="active"]
if len(demos)!=1:raise RuntimeError(f"Expected exactly one active API-enabled demo account; found {len(demos)}. No orders sent.")
a=demos[0];account_id=a["accountId"]
positions=get(f"/positions/{account_id}/active")
markets=get(f"/v2/markets?accountId={account_id}")
risk=get(f"/accounts/{account_id}/risk-status")
def count(v):
 if isinstance(v,list):return len(v)
 if isinstance(v,dict):
  for k in ("items","data","positions","markets"):
   if isinstance(v.get(k),list):return len(v[k])
 return "unknown"
print(json.dumps({"status":"read_only_ok","account_type":"demo","account_status":a.get("status"),"api_trading":a.get("apiTrading"),"active_positions":count(positions),"available_markets":count(markets),"risk_status_retrieved":isinstance(risk,(dict,list)),"target_account_usd":10000,"position_notional_usd":2000,"max_positions":3,"orders_sent":0}))

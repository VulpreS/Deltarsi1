"""Paper-only prospective forward for preselected BTC BNB XRP 4h DeltaRSI; TON retired, GRAM requires separate contract.

Never retune on August-October 2026; it was previously inspected.
Policy selection completed 2026-10-31 UTC, so genuine forward begins
2026-11-01 00:00 UTC. Restores historical data from immutable GitHub Release.
Only daily 4h ZIPs newer than 2026-10-27 may be fetched.
No 48h cap and absolutely no live orders.
"""
import datetime as dt
import hashlib
import json
import os

import research_rules as rr
import forward_frozen as frozen
from train import ROOT, features

FROZEN_DATE="2026-10-31"
ASSETS=("BTCUSDT","BNBUSDT","XRPUSDT")
START=frozen.FORWARD_MS
COST=0.0018
INIT=5000.
NOTIONAL=840.
POLICIES={
    "BTCUSDT":dict(params=("strict_trend",4.0,5.0,(3.0,1.5),"zero_cross"),direction="both"),
    "BNBUSDT":dict(params=("strict",1.5,0.0,(3.0,1.5),"risk_only"),direction="both"),
    "XRPUSDT":dict(params=("expanded",2.5,5.0,(3.0,1.5),"risk_only"),direction="both"),
}


def replay(rows,sym,policy):
    p=policy["params"]
    direction=policy["direction"]
    d=rr.make_arrays(features(rows,sym))
    signals=rr.candidates(d,p[0])
    available=int(d["t"][-1])
    closed=[]
    opened=None
    pending=[]
    next_open_allowed=START
    for i,side in signals:
        t=int(d["t"][i+1])
        if t<START or t<next_open_allowed:
            continue
        if direction=="short_only" and side!=-1:
            continue
        if direction=="long_only" and side!=1:
            continue
        trade=rr.trade(d,i,side,d["n"],p)
        if not trade:
            continue
        trade["symbol"]=sym
        if trade["reason"]=="evaluation_boundary":
            opened=dict(symbol=sym,side="LONG" if side==1 else "SHORT",
                entry_utc=frozen.iso(t),signal_utc=frozen.iso(d["t"][i]),
                entry_price=trade["entry"],last_seen_bar=frozen.iso(available),
                mark_to_market_pct=round(100*trade["ret"],3),
                status="paper_open_not_realized")
            break
        closed.append(trade)
        next_open_allowed=int(trade["exit_ms"])+frozen.STEP
    return dict(closed_trades=closed,open_position=opened,pending=pending)


def main():
    now=dt.datetime.now(dt.timezone.utc)
    last_complete_day=now.date()-dt.timedelta(days=1)
    rr.COST_RT=COST
    sets={}
    inputs={}
    for sym in ASSETS:
        p=ROOT/"data"/(sym+".json")
        if not p.is_file():
            raise FileNotFoundError("Frozen historical release restore failed: "+str(p))
        contents=p.read_bytes()
        historic=json.loads(contents)
        if historic[-1][0]>=START:
            raise RuntimeError("Release baseline unexpectedly contains forward data: "+sym)
        all_rows,diag=frozen.extend_baseline(sym,historic,last_complete_day)
        sets[sym]=all_rows
        inputs[sym]=dict(baseline_sha256=hashlib.sha256(contents).hexdigest(),**diag)
    end=min(int(rows[-1][0]) for rows in sets.values())
    result=dict(experiment="prospective_BTC_BNB_XRP_frozen_delta_paper",
        as_of=now.isoformat(),run_id=os.environ.get("GITHUB_RUN_ID","local"),
        sha=os.environ.get("GITHUB_SHA","local"),policy_frozen_on=FROZEN_DATE,
        first_eligible_utc=frozen.iso(START),
        market_data_source="Binance USD-M 4h Vision archives; frozen release snapshot",
        previous_run_source="41231907011",
        data_through_utc=frozen.iso(end),
        execution="next open after fully closed 4h, OHLC conservative stop-first",
        cost_roundtrip=COST,notional_per_position=NOTIONAL,
        margin_notional_assumption="research fixed nominal USD, no leverage",
        starting_capital=INIT,not_a_combined_portfolio=True,
        rules={},reports={},data_quality=inputs,commissions_funding="0.18% RT fee + spread proxy; funding omitted",
        excluded_contracts={"TONUSDT":"DELlSTED 2026-06-23; subsequent candles zero volume, GRAMUSDT is separate from July 2"},
        warnings=[
            "Any result before 2026-11-01 is forbidden as a new prospective out-of-sample score",
            "Previously inspected Aug-Oct performance and thousands of candidates selected; needs further future validation",
            "No 48h maximum; no manual trade labels; no API trading or real orders",
            "Missing daily ZIP blocks processing; same-Binance monthly fallback allowed, NEVER bridge gaps",
            "Closed trades counted only after exit, open positions excluded from realized profitability",
            "No intrabar prop drawdown, leverage, funding or slippage compliance; research only",
        ])
    missing=any(diag["missing_days"] for diag in inputs.values())
    for sym,policy in POLICIES.items():
        rows=[r for r in sets[sym] if r[0]<=end]
        item=replay(rows,sym,policy)
        profits=[float(t["ret"]) for t in item["closed_trades"]]
        gain=sum(max(0.,r) for r in profits)
        loss=-sum(min(0.,r) for r in profits)
        result["rules"][sym]=dict(entry=policy["params"][0],direction=policy["direction"],
             stop_atr=policy["params"][1],take_atr=policy["params"][2],
             trail_activation_atr=policy["params"][3][0],
             trail_distance_atr=policy["params"][3][1],
             indicator_exit=policy["params"][4],max_hold_hours=None)
        result["reports"][sym]=dict(
            realized_usd=round(NOTIONAL*sum(profits),2),
            realized_account_pct=round(100*NOTIONAL*sum(profits)/INIT,3),
            trades_closed=len(profits),
            win_rate=round(sum(r>0 for r in profits)/len(profits),3) if profits else None,
            profit_factor=round(gain/loss,3) if loss else None,
            open_position=item["open_position"],
            closed_trades=item["closed_trades"],
            pending=item["pending"])
    result["status"]=(
        "incomplete_historical_gap" if missing else
        "waiting_for_future_candles" if end+frozen.STEP<=START else
        "forward_reporting")
    (ROOT/"OTHER_COINS_FORWARD.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
    headline=dict(status=result["status"],as_of=result["as_of"],
        data_through=result["data_through_utc"],
        new_bars={k:v["new_bars"] for k,v in inputs.items()},
        missing={k:v["missing_days"][:2] for k,v in inputs.items()},
        results={k:dict(closed=v["trades_closed"],account_pct=v["realized_account_pct"],
                        open=bool(v["open_position"])) for k,v in result["reports"].items()})
    print("OTHER_COINS_FORWARD",json.dumps(headline,ensure_ascii=False),flush=True)
    lines=["# DeltaRSI: frozen paper forward BTC / BNB / XRP / TON","",
      f"Исследование {result['run_id']}, состояние {result['status']}. Последняя непрерывная свеча: {result['data_through_utc']}.",
      "Заморозка правил: 31.10.2026. Настоящий prospective период начинается 01.11.2026 00:00 UTC.",
      "Раньше ноября новые сделки не учитываются; ручные сделки — отдельный тест.",
      "Никакого 48h удержания, ордеров на проп-счёт не отправляем.","",
      "| Монета | Закрытых сделок | Результат счёта 5000$ | Открыта бумажная позиция |",
      "|---|---:|---:|---|"]
    for sym,v in result["reports"].items():
        lines.append(f"| {sym.replace('USDT','')} | {v['trades_closed']} | "
           f"{v['realized_account_pct']:+.3f}% | {'да' if v['open_position'] else 'нет'} |")
    lines+=["","Сигналы в этом форварде не оптимизируются по августу–октябрю.",
       "Если архив отсутствует, проверка блокируется без интерполяции котировок.",
       "Артефакты содержат полные свечные метаданные, правила и сделки."]
    (ROOT/"OTHER_COINS_FORWARD.md").write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    main()

# HANDOFF_CONTEXT.md — передача контекста новому диалогу
Дата: 2026-10-29. Проект: VulpreS/Deltarsi1. Язык общения: русский.
**ПЕРВЫМ ДЕЛОМ** в новом диалоге прочитай этот файл и `experiments/BACKTEST_REQUIREMENTS.md` через подключённый GitHub. Не заставляй пользователя повторять условия. Действуй как самостоятельный исследователь: меняй код, запускай GitHub Actions, дожидайся завершения, читай логи и артефакты, сообщай результаты, не выдумывай цифры.

## 1. Цель
Создать и испытать алгоритмическую криптостратегию на проп-счёте Upscale, с приоритетом прохождения обоих challenge этапов как можно быстрее (ручной ориентир пользователя ~14 дней), без нарушения рисков, и устойчивостью на разных рынках. Не смешивать скорость прохождения и просто прибыльность. Пользователь предпочитает закрытые свечи, 4h сигналы и 5m исполнение; обсуждались также 15m/1h/6h/8h/1d. В новой 5m серии исходная Delta НЕ меняется, оптимизируется исполнение.

## 2. Единый источник требований
`experiments/BACKTEST_REQUIREMENTS.md` — ОБЯЗАТЕЛЬНЫЙ нормативный документ; включает Upscale, 21founded, Bybit, Binance, TradingView, Coinglass, GitHub, лимиты, капитал, комиссии, методологию, риски, тестовые метрики и технические ограничения. Не считать неуточнённые правила платформы подтверждёнными. При новых уточнениях обновлять регламент.

**КРИТИЧЕСКИЕ последние исправления пользователя:**
1. DeltaRSI **ОДНА**, «исторической» и «новой» версий пользователь не имеет; в его Pine неверные ЗАГОЛОВКИ параметров. Нельзя судить о математике по заголовкам. Нужен parity audit ФАКТИЧЕСКОГО Pine тела и Python. Python `CausalDelta` сейчас считает SMA21 -> Wilder RSI12 -> EMA7 -> логарифмическая нормализация, что не совпадает с ранее словами описанной RSI27-EMA7. Не менять сигнал молча и не выдавать утверждения без проверки.
2. Дивергенции, «2–3 волны», свечные фитили НЕ ФОРМАЛИЗОВАНЫ и НИГДЕ в бэктестах не учитывались; пользователь просил не приписывать им результаты и не включать автоматически.
3. В нынешней 5m серии пользователь просил использовать ту же Delta, что в предыдущих тестах: `experiments.pine_vs_codex.run.pine_events`.
4. Пользователь требует самостоятельной работы: **запустить GitHub Actions, дождаться завершения и сразу вернуть результаты**; не просить его писать «готово». Если среда не позволяет ждать в фоне, не обещать фонового ожидания; в рамках доступного вызова проверить состояние, логи и артефакты.

## 3. Платформа и портфель — кратко
- Upscale: стартовый $5000 challenge, demo $10000 отдельно; daily drawdown 5%, total 10%; stage1 +5% и 3 дня >=0.5%; stage2 +8% и 5 дней >=0.5%; 00 UTC reset как рабочая гипотеза; 30% consistency зависит от конкретного тарифа и требует проверки; funded payout ориентир 14 дней/5 дней >=0.5%.
- Боты/API, переносы, новости разрешены по словам пользователя; правила 21founded НЕ проверены и не наследуются от Upscale.
- Не более 3 одновременных позиций на счёт. «10–15% на сделку» означает МАРЖУ, а «стоп 5%» — процент движения ЦЕНЫ, не риск капитала. Исследовался $1000 notional; это отдельное предположение, не то же самое, что 10–15% margin.
- Базовая вселенная 8: BTC ETH ICP TON BNB ZEC XRP LINK. Сравнивать 1 счёт на 8 монет, 2 отдельных счёта и BTC/ETH 30/30.
- Стоимость в последнем 5m движке: FEE=.00008 на сторону, SPREAD=.0002 roundtrip, FUNDING=.00015 каждые 8h (все funding списываются положительно — упрощение). Исторически обсуждались комиссии .08% на сторону; ставки проверять по тарифу.
- Не использовать результаты как готовые для реального API: есть известные проблемы с 60-second rule, фазовыми reset, funding и прочим, перечислены в регламенте.

## 4. Структура кода и реальные тесты
- `experiments/five_min_90d/run.py`: 5m OHLC исполнение; закрытые 4h сигналы из `pine_events`; Binance USDT-M архивы; 90d **2026-04-02 ... 2026-06-30**; 8 монет; 4h ATR SL/TP; 48h time exit; conservative stop-first. В 2026-10-29 добавлены параметры `simulate(raw,signals,group,params=None,start=START,end=END,be_trigger=None,max_hold=48)`. Обратить внимание: BE и hold в портфельном тесте единые, не per-asset.
- `experiments/five_min_90d/optimize.py`: 60d train/30d untouched OOS; по монетам сетка 8 SL/TP * 3 BE/hold = 24 кандидата; портфель сравнивает оптимизированные SL/TP с единым BE+1% и hold48h. Отчёт `experiments/five_min_90d/optimized_results.json` создаётся во время Action и загружается как artifact, **не обязательно коммитится в репозиторий**.
- `.github/workflows/five-min-optimize.yml`: `workflow_dispatch` и push по файлу оптимизатора; workflow запускает `python -u experiments/five_min_90d/optimize.py` и публикует artifact `five-min-optimized-results`.
- `.github/workflows/five-min-90d.yml`: первоначальный 5m baseline.
- `experiments/pine_vs_codex/run.py`: `pine_events`, оттенки и входы.
- `causal_4h_parity_audit.py`: `CausalDelta` с фактической формулой, требующей сверки с Pine.
- `experiments/max_strategy_grid/pine_baseline_2026-10-29.json`: исходные SL/TP ATR по монетам.
- `experiments/two_accounts_opposite_exit/run.py`: раздельные счета, альтернативные выходы.
- `data/*_1h.csv`: локальные свечи части активов.
- Репозиторий: https://github.com/VulpreS/Deltarsi1

## 5. Последние подтверждённые результаты
### 5m baseline, run 40875870216
https://github.com/VulpreS/Deltarsi1/actions/runs/40875870216
Один $5000 счёт на 8 монет: stage1 за 71 день (2026-06-12), stage2 не пройден; equity $5265.32, DD 4.858%, 55 сделок, no breach. Два счёта: A BTC ETH TON ZEC XRP — stage1 за 71 день, DD 5.074%, 41 сделка; B ICP BNB LINK — stage1 за 75 дней, DD 5.004%, 26 сделок. Ни один не funded.

### 5m optimized, run 40877563971, SUCCESS
https://github.com/VulpreS/Deltarsi1/actions/runs/40877563971
На полном 90d, один счёт: baseline stage1 71 день, 55 сделок, DD 4.858%, $5265.32; optimized stage1 60 дней (2026-06-01), 70 сделок, DD 3.146%, $5227.72; stage2 не пройден ни там, ни там. В независимые последние 30d: baseline stage1 за 21 день, DD 4.7%, optimized stage1 НЕ пройден, DD 3.146%. Поэтому «быстрее на полном периоде» НЕ означает устойчиво быстрее OOS.
Выбранные на train монетные (SL_ATR, TP_ATR, BE, hold):
BTC (2.5,2.5,off,48h)
ETH (1.5,2.5,off,48h)
ICP (2.5,2.5,+1.5%,72h)
TON (1,1.5,off,48h)
BNB (3.5,5,off,48h)
ZEC (1.5,2.5,+1.5%,72h)
XRP (1.5,2.5,off,48h)
LINK (2.5,2.5,+1%,48h)
**ВАЖНО:** портфельный optimized прогон применил эти SL/TP, но BE+1% и 48h ЕДИНЫЕ для всех, поэтому не тестировал точные индивидуальные настройки выше.
Отдельно обнаружено: `net_pnl` при фазовом reset не всегда соответствует текущей equity, phase ledger нужен.

### 1h исследования, workflow 40865207096
244d: 83/127 разбиений 2 счетов прошли оба этапа; последние 90d: 0/127 оба, 18/127 один; последние 30d: 0/127 оба. Нельзя переносить оптимистичные выводы с train на новые режимы.

## 6. КАК АССИСТЕНТУ САМОМУ ЗАПУСКАТЬ И АНАЛИЗИРОВАТЬ GITHUB ACTIONS
В ChatGPT доступен GitHub connector через `functions.exec`, инструменты `tools.mcp__GitHub__...`. **Не нужно просить пользователя вручную запускать workflow**, если GitHub connector имеет право записывать код, а workflow срабатывает по push. ВАЖНО: отдельный dispatch инструмент может отсутствовать; можно создать/обновить файл, на который подписан `on.push.paths`, либо при наличии доступного Actions write endpoint запустить workflow_dispatch. Проверить права и триггер.
Шаг 1: найти инструменты и их сигнатуры:
```js
text(ALL_TOOLS.filter(x=>x.name.startsWith("mcp__GitHub__")&&/fetch_file|update_file|create_file|workflow|fetch$/.test(x.name)).map(x=>x.name+" "+x.description.slice(0,350)).join("\n\n"))
```
Шаг 2: прочитать файл:
```js
const r=await tools.mcp__GitHub__fetch_file({repository_full_name:"VulpreS/Deltarsi1",path:"experiments/five_min_90d/optimize.py"});
text(r.result.content);text(r.result.sha);
```
Шаг 3: обновить файл с известным SHA (полученным из fetch_file):
```js
const p="experiments/five_min_90d/optimize.py";
const r=await tools.mcp__GitHub__fetch_file({repository_full_name:"VulpreS/Deltarsi1",path:p});
const updated=r.result.content.replace("old","new"); // реальное изменение!
text(await tools.mcp__GitHub__update_file({repository_full_name:"VulpreS/Deltarsi1",path:p,sha:r.result.sha,content:updated,message:"Describe experiment"}));
```
Шаг 4: найти run ID после push:
```js
const r=await tools.mcp__GitHub__fetch({url:"https://api.github.com/repos/VulpreS/Deltarsi1/actions/runs?per_page=100"});
const runs=JSON.parse(r.result.content).workflow_runs;
text(runs.filter(x=>x.name==="Five minute stop take optimization").map(x=>({id:x.id,status:x.status,conclusion:x.conclusion,url:x.html_url,head_sha:x.head_sha})));
```
Сопоставить `head_sha` с коммитом, не взять старый run.
Шаг 5: дождаться выполнения — повторно опрашивать состояние в доступных вызовах, не объявлять завершённым пока `status=completed` и `conclusion=success`:
```js
const r=await tools.mcp__GitHub__fetch_workflow_run_jobs({repo_full_name:"VulpreS/Deltarsi1",run_id:40877563971});
text(r.result.jobs.map(j=>({id:j.id,status:j.status,conclusion:j.conclusion})));
```
Шаг 6: прочитать логи job:
```js
const l=await tools.mcp__GitHub__fetch_workflow_job_logs({repo_full_name:"VulpreS/Deltarsi1",job_id:123460204710});
text(l.result.content.split("\n").filter(x=>/SELECT |COMPARE |RESULT|Traceback|Error:/.test(x)).join("\n"));
```
Шаг 7: при необходимости получить артефакты:
```js
const a=await tools.mcp__GitHub__fetch_workflow_run_artifacts({repo_full_name:"VulpreS/Deltarsi1",run_id:40877563971});
text(a);
```
Для ZIP есть `mcp__GitHub__download_workflow_artifact` (сигнатуру узнать через ALL_TOOLS). При недоступности артефактов можно извлечь JSON из stdout или сделать отдельный workflow step, печатающий summary в лог. Не выдавать локальный `results.json` за закоммиченный, если это лишь Actions artifact.
Шаг 8: анализировать честно: сколько этапов пройдено и когда, qualifying days, DD, breach, trades, fees/funding, раздельные train/OOS/full; сравнить baseline с оптимизированным на ОДИНАКОВЫХ датах и капитализации; показать, какие правила реально включены в портфель; выявить ошибки модели.
Шаг 9: если failure — получить лог, исправить код, перезапустить, дождаться успешного завершения; не оставлять пользователю задачу дебага.

**Для человека в браузере GitHub:** открыть репозиторий -> вкладка Actions -> слева workflow `Five minute stop take optimization` -> Run workflow -> branch main -> Run workflow. Открыть run -> job `optimize` -> логи, искать `SELECT`, `COMPARE`, `Traceback`. Внизу страницы run -> Artifacts -> `five-min-optimized-results` -> ZIP -> `optimized_results.json`. Красный крест = ошибка, зелёная галочка = успешное выполнение. Для первичного теста `Five minute 90d` — соответствующий workflow. Можно открыть прямые ссылки на run из раздела 5.

## 7. Что делать следующим
- При новом запросе продолжить исследование без повторного согласования параметров, но проверить фактический Pine-код для parity (если доступен в репозитории).
- Исправить 5m движок: 60-second rule, phase ledger, корректная совокупная прибыль, раздельные индивидуальные BE/hold, корректный risk accounting, funding. Не изменять сразу несколько факторов без контрольного baseline.
- Запустить портфельный тест точных per-coin BE/hold и сравнить с едиными правилами на OOS.
- По возможности протестировать 15m execution на тех же 4h сигналах и датах.
- Все изменения требований записывать в `BACKTEST_REQUIREMENTS.md`.


## 8. Актуальный стоп-аудит 4h DeltaRSI — 2026-10-29
- Подробный отчёт: `experiments/five_min_90d/stops_4h/RESEARCH_REPORT_2026-10-29.md`. GitHub Actions успешный: https://github.com/VulpreS/Deltarsi1/actions/runs/40902897903, artifact `delta-4h-stop-loss-histogram-investigation` (CSV/JSON всех 24 стопов и 1–12 следующих закрытых 4h свечей). Код `experiments/five_min_90d/analyze_4h_stops.py`.
- Реплей 4h сигналов / 5m исполнения, 8 монет, один $5000 счёт, прошлые per-coin SL/TP/BE/hold, SL max 5% цены clamp, 0.08% комиссии на сторону, 0.04% спред roundtrip, 90d 2026-04-02—2026-06-30: 64 сделки, PF5.29, DD3.689%, модельные этапы 21 и 67 дней.
- Результат: **только 3 исходных SL** BTC (−$51.95, long 2026-06-05), XRP (−$41.78, long 2026-06-05), BNB (−$29.43, short 2026-05-04/06); плюс **21 BE-стоп** (ZEC10, ICP6, LINK5), каждый около −$2 издержек при +0.08%/side и +0.04% roundtrip spread. 17 TP и 23 time.
- BNB short: после стопа синяя гистограмма снова нарастала 5×4h, до входа в 12 свечах цена не вернулась. BTC/XRP лонги открылись одновременно, их красная Delta продолжала затухать после стопа, цена вернулась к входу только через 10/11 следующих 4h свечей и не достигала первоначального TP в 12. Нельзя обобщать причины по трем случаям.
- BE: медианная наблюдавшаяся MFE ~2.847%, **9/21 BE закрылись до первого нового закрытия 4h свечи после входа**. В следующие 5×4h свечей 15/21 имели хотя бы одно закрытие >+0.5% цены в сторону исходной сделки от входа, но только 5/21 коснулись исходного TP за 12 свечей. Это ретроспективные, НЕ причинные входные признаки.
- BE-only fixed sensitivity на том же 4h: исходный BE — оба этапа 67 дней, OOS stage1 22 дня; BE с фиксацией +0.5% цены — оба этапа также 67 дней, OOS stage1 18 дней, полная прибыль фаз почти без изменений; отключение BE — оба этапа 78 дней, просадка больше; BE триггер +3% — 72 дня. Нельзя выбирать OOS-победителя по уже просмотренному OOS.
- **Направление следующего исследования:** не менять Delta или придумывать новую стратегию; проверить причины BE-потерь и прибыльный lock/частичный TP, далее подтвердить стоп-сценарии и корреляцию BTC/XRP на 180–365d, без look-ahead, с новыми OOS и учётом правил Upscale.


## 9. Годовой подбор частичных тейков 4h DeltaRSI — 2026-10-29
- Код `experiments/five_min_90d/optimize_partial_take_4h.py`; расширен `experiments/five_min_90d/run.py` опциональными `partials` с корректным уменьшением объёма и расходов по каждой фиксации. 8 монет BTC ETH ICP TON BNB ZEC XRP LINK; 4h сигнал, 5m исполнение, исходные per-coin SL/TP/BE/hold, $5000 счёт, 3 позиции, stop clamp 5% цены, 0.08% fee/side+0.04% roundtrip spread.
- Непрерывный год **2025-07-01..2026-06-30**, 112 Binance USDT-M 5m ZIP (14 месяцев × 8, включая прогрев); проверка сплошных свечей. **117 схем частичных TP**. Train Jul-Dec 2025, validation Jan-Mar 2026 + непрерывная 9mo screen на риск, финал Apr-Jun 2026 без подбора по нему (но этот период ранее неоднократно исследован).
- GitHub Actions success https://github.com/VulpreS/Deltarsi1/actions/runs/40905804869; full artifact id **12912075935**, отчёт `experiments/five_min_90d/partial_annual/ANNUAL_RESEARCH_REPORT_2026-10-29.md`.
- Выбранная по train+validation схема: **частичный TP 15% исходного объёма на +1.5% цены, ещё 30% на +3% цены, оставшиеся 55% по старым правилам**. Для шорта симметрично. Год: этап1 лишь на 318-й день, этап2 через 35 дней (оба на день353), DD9.284%, PF1.448, 254 trades, моделируемый cumulative phase PNL+$893.76, без breach.
- Контроль без partials на год: breach 2025-11-26 (общий лимит10%). Предложенный пользователем пример +0.5%:15%, +1.5%:20%: breach 2026-01-15. Альтернатива с меньшей DD: +1.5%:25%, +3%:35% — 2 этапа те же 353 дней, DD8.645%, PNL фаз+$831.12.
- Отдельный последний Q2 Apr-Jun 2026 с новым $5000: без partials оба этапа 68 дней и $981.77 фаз; выбранный частичный 15/30 — те же 68 дней и $899.07, DD3.496% против3.689%.
- КРИТИЧЕСКИ ВАЖНО: высокая доходность Q2 не переносится на весь год; первая половина года в минусе даже у выбранного варианта. Частичная фиксация помогает выжить, но не даёт стабильного быстрого челленджа. Для real Upscale параметры не утверждены, риски платформы не полностью верифицированы.

# Сравнение 5m / 15m / 4h — DeltaRSI, 8 монет, Upscale $5 000

Дата запуска: 2026-10-29. Исполненный GitHub Actions: https://github.com/VulpreS/Deltarsi1/actions/runs/40884942989
Статус: **completed / success**; SHA запуска: `37bd1f9c90743cbbca8d02a185251d872671f2e6`.
Артефакт: `eight-assets-5m-15m-4h` (JSON `three_tf_results.json`), доступен в конце страницы запуска.
Исходный код: `experiments/five_min_90d/compare_three_timeframes.py`.

## Универсум
**BTC, ETH, ICP, TON, BNB, ZEC, XRP, LINK**, фьючерсы USDT.
Данные: Binance USD-M 5m, архивы за февраль–июнь 2026, пересэмплированы в закрытые 15m, 1h и 4h по одному источнику.
Тестовая история: UTC 2026-04-02 00:00 — 2026-07-01 00:00 (90 дней). Train: первые 60 дней; OOS: последние 30 дней.
Счёт Upscale $5 000, $1 000 notional на открытую сделку, максимум 3 позиции. Замороженные per-asset SL/TP в ATR(4h), BE и hold.
Режим «clamp»: стоп не дальше 5% цены от входа. Комиссия 0,08% **за сторону**, спред 0,04% **за оборот**, funding 0,015% каждые 8h (приближение).
Сигнал `CausalDelta` и точная цветовая функция `pine_shade`; 4h-сигнал — исходный `pine_events`. Это математическая реализация, использовавшаяся в прошлых тестах, НЕ сертифицированный parity с фактическим телом Pine.
Дивергенции/волны/подтверждения фитилями не формализованы и не включались.

## A: Сигналы 5m, 15m, 4h; одно и то же исполнение на 5m

| Signal TF | Signals / 90d (8 монет) | Trades full | WR full | PF full | DD full | Stage 1 full | Stage 2 full | Breach full |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 5m | 3649 | 140 | 30,00% | 0,741 | 11,806% | нет | нет | общий лимит, 2026-05-19 |
| 15m | 1189 | 185 | 33,51% | 0,852 | 12,688% | нет | нет | общий лимит, 2026-06-15 |
| 4h | 74 | 64 | 53,12% | 5,290 | 3,689% | день 21 (2026-04-23) | день 67 (2026-06-08) | нет |

У 5m и 15m full-период заканчивается преждевременно при модели breach; WR/PF и количество сделок относятся к сделкам до остановки. Отдельная OOS с новым $5 000 стартом:

| Signal TF | 30d OOS Trades | WR | PF | Max DD | Phase 1 | Phase 2 | Breach |
|---|---:|---:|---:|---:|---|---|---|
| 5m | 98 | 27,55% | 0,810 | 9,103% | нет | нет | нет |
| 15m | 79 | 26,58% | 0,747 | 11,638% | нет | нет | нет (total limit проверяется от initial, DD peak-to-trough) |
| 4h | 24 | 41,67% | 3,531 | 3,937% | день 22 | нет | нет |

**Важно:** SL/TP/BE/hold подбирались прежде на 4h-сигналах; переносить их на 5m/15m без отдельного train-only выбора не значит доказать, что младшие TF в принципе не работают. К тому же отдельная 5m RSI+RVGI стратегия здесь НЕ тестировалась: это исключительно **DeltaRSI** на трёх таймфреймах.

## Б: один и тот же 4h-сигнал, исполнение 5m, 15m, 4h

| Execution TF | Full 90d Trades | WR | PF | DD | Stage 1 | Stage 2 | Both stages |
|---|---:|---:|---:|---:|---|---|---|
| 5m | 64 | 53,12% | 5,290 | 3,689% | день 21 | +46 дней | день 67 |
| 15m | 64 | 53,12% | 5,290 | 3,690% | день 21 | +46 дней | день 67 |
| 4h | 62 | 54,84% | 3,470 | 4,112% | день 44 | +34 дня | день 78 |

Out of sample (последние 30 дней, с новым исходным капиталом):

| Execution TF | Trades | WR | PF | Max DD | Stage 1 | Stage 2 |
|---|---:|---:|---:|---:|---|---|
| 5m | 24 | 41,67% | 3,531 | 3,937% | день 22 | нет |
| 15m | 24 | 41,67% | 3,531 | 3,937% | день 22 | нет |
| 4h | 22 | 50,00% | 5,407 | 4,236% | нет | нет |

## C: Validity and limitations

- Both comparisons use identical assets/period/capital/cost/closed-bar policy. Signal TF and execution TF are isolated in separate comparisons; these are NOT interchangeable descriptions.
- 5m/15m higher-frequency signal experiments are hypotheses, not a reconstruction of user's separate RSI/RVGI 5m bot. Per-asset SL/TP parameters are held constant, optimized previously on 4h signal trains.
- 15m/4h OHLC aggregates hide intrabar SL/TP order; stop-first conservative and positive exits deferred to next execution candle. This delays 4h wins more strongly than 5m wins; 4h-execution underperformance cannot be attributed entirely to timing efficiency.
- This is research, not verification of Upscale actual phase pass. 60-second execution restriction is approximated rather than implemented with ticks; 30% consistency, mark-price DD, phase transitions and funding are not fully venue verified.
- The shorter TF tests generate thousands of signals and frequently hit the 3-position cap; transaction costs and missed signals matter.
- OOS dates had been inspected in earlier runs; strict new unseen-forward validation is still required. No independent reoptimization of 5m/15m strategies.
- Price stop max 5% is realized as **clamp**, not rejection; user manual structure-based stops are NOT replicated.
- No live orders. No divergence, waves, or price-wick visual filters.

## Next experiment

Keep three distinct hypotheses: (1) Delta signal TF 4h with 5m execution as baseline; (2) separately train 5m/15m Delta SL/TP/BE/holding policies on first 60 days and assess 30 days OOS without fitting; (3) compare to user's separate RSI+RVGI 5m strategy only after matching its exact source implementation. Audit the Pine body and platform-compliance timing before live use.

# Crypto Signal Bot: market tracking with measurable signals

A Telegram bot that tracks Turkish-lira crypto pairs on BtcTurk, raises rule-based signals and **records what happened after every signal**, so a rule's usefulness is measured and not assumed.

> **Monitoring only.** The bot never places orders and has no exchange credentials. It uses public market-data endpoints only. Signals are hypotheses under test, not trading advice.

## Why it exists
Most hobby signal bots show a signal and move on. This one is built around one question: *after costs, inflation and the market's own move, did the signal actually add anything?* Every signal is logged with its forward returns, and the backtest and the live bot share the same trigger logic.

## Data sources
- **BtcTurk public API**: hourly and daily candles from the graph endpoint, plus ticker and exchange info. The endpoint caps a request by window width (about 11,000 hourly candles), not by date, so the downloader requests 400-day windows. History goes back to 2014 for BTCTRY.
- **USDTTRY** from the same exchange, used as the lira-inflation deflator
- **BTCTRY**, used as the market benchmark
- Extra commands for BIST equities (`borsapy`) and gold/FX prices (public endpoints)

## Signal logic
Rules live in `kurallar/` and are deliberately simple. The point is the measurement around them.

| Rule | Thesis | Trigger | Thresholds |
|---|---|---|---|
| `MOM_1W` | 1-week momentum continues | 7-day return > X % | 5 / 10 / 15 |
| `REV_1D` | sharp drops bounce | 24-hour drop > X % | 5 / 8 / 12 |

Forward horizons: 1, 7 and 30 days, which gives **2 × 3 × 3 = 18 trials**. The trial count is fixed up front in [`docs/HYPOTHESIS.md`](docs/HYPOTHESIS.md) and printed with every metrics run, so multiple-comparison risk stays visible.

**Trigger state machine** (`sistem/tetikleme.py`): a rule moves ARMED → FIRED and re-arms only after its condition has turned false *and* the cooldown has passed. A condition that stays true fires once, not once per cooldown. The backtest and the live scanner run the same class.

**Return decomposition** (`backtest/metrikler.py`): every 7-day result is split into four parts:

```
raw return
 − round-trip commission (0.40 %)
 − currency effect (USDTTRY)
 − market effect (BTCTRY)
 = NET
```

**Bias controls**
- lookahead: every price lookup uses `open_time <= t` (`index_at_or_before`), and a test checks that truncating the data at `t` changes nothing before `t`
- walk-forward: the threshold is picked on the train slice and judged on the test slice, with a maximum allowed degradation
- survivorship: BtcTurk has no historical symbol list, so the bot keeps a daily snapshot of listed pairs from now on (`daily_snapshot`)
- delisted symbols (e.g. MATIC → POL) are detected via `exchangeinfo` at start-up

## Results so far (backtest, not live)
Run on 2018-07-10 → 2026-09-01 hourly data, 9 pairs, 12,963 signals. The start date is bounded by the deflator's history.

- All signals combined: 7-day **NET −0.30 %**, t = −2.68. As a group, the rules do not beat the market after costs.
- `REV_1D_12` (24 h drop > 12 %) is the only rule that passes the pre-registered bar on the full sample: NET +1.94 %, t = +3.17, n = 570.
- Walk-forward: 4 of 18 symbol/family combinations held up out of sample. Two of the four are `REV_1D_12` on separate pairs. Test-slice sample sizes are small (22–160).

With 18 trials × 9 pairs, a few good-looking combinations are expected by chance. Live measurement of the forward returns is what the bot is collecting now.

## Architecture

```
bot.py                  Telegram app + three jobs:
                        ├─ live scan (hourly, catch-up mode: missed hours are replayed)
                        ├─ price alarms (every 60 s)
                        └─ daily market snapshot
kurallar/               rule definitions
sistem/                 trigger state machine, live scan, follow-up price checks, subscribers
backtest/               event study, metrics with return decomposition, walk-forward
data/                   BtcTurk client, downloader, deflator, data-health checks
migrasyon.py            idempotent SQLite migrations
komutlar/               Telegram command handlers
servis/                 example systemd unit
```

Storage is SQLite. Every backtest run writes under its own `run_id`, and the follow-up job fills `price_1d/7d/30d` for live signals from stored candles.

## Stack
Python · python-telegram-bot (job-queue) · pandas · SQLite · requests · BtcTurk public REST API

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env            # add TELEGRAM_BOT_TOKEN from @BotFather
python database.py              # create tables + apply migrations
python data/veri_indir.py       # download historical candles
python bot.py
```

Backtest and evaluation:

```bash
python backtest/olay_calismasi.py   # event study → signal_log
python backtest/rapor.py            # metrics with return decomposition
python backtest/walk_forward.py     # walk-forward threshold selection
```

Tests (offline, temporary database):

```bash
python test_tetikleme.py
python test_lookahead.py
python test_kontrol_job.py
python test_abone.py
```

## Bot commands
`/start` subscribe · `/fiyat BTC` price · `/fiyatlar` all prices · `/sinyaller` recent signals · `/istatistik` stats · `/alarm_kur`, `/alarm_listesi`, `/alarm_sil` price alarms · `/portfoy_ekle`, `/portfoy_goster`, `/portfoy_sil` portfolio tracking · `/bist`, `/bistliste` BIST · `/altin`, `/altindoviz` gold and FX

All parameters, including the ones still under review (walk-forward tolerance, scan intervals), are in `config.py`.

The code identifiers and comments are in Turkish.

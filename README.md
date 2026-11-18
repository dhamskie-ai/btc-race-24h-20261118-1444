# btc-race-24h-20261118-1444
[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/dhamskie-ai/btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/dhamskie-ai/btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A dip-buying momentum bot for cbBTC (CBBTC/USDC) that races a BTC trading bot
live for 24 hours on make.fun. Long only, full size, no leverage.

The bot speaks `agent-fun/bars-replay/v1`: it reads the `hello` handshake, then
answers every `batch` of 1-minute bars with one reply carrying its `orders`.
It buys all of its $1,000 paper USDC when the latest close is at least 2.00%
below the highest high of the last 181 bars — a sharp intraday dip — or 1.50%
below it while the 15-minute return has already turned positive (a dip that
has started to bounce). It sells the whole position at +1.50% over its cost,
or on a 0.80% trailing stop from the highest value reached while holding.
Otherwise it holds cash. All decisions use integer math only, so two runs on
the same bars produce identical orders.

Dev-window result (frozen 24h window, 1,440 bars): net PnL **+$13.62 USDC**,
2 trades, max drawdown 0.64%.

## Run it

```sh
python3 main.py
```

Entered on [make.fun](https://make.fun/?ref=hq3jb8gk&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards

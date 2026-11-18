"""Dip-buy momentum bot for cbBTC (CBBTC/USDC), make.fun btc-race-24h-20261118-1444.

Speaks agent-fun/bars-replay/v1: the harness sends one hello line, then one
batch line per 1-minute bar, then done. The bot answers every batch with
exactly one reply line echoing its seq, carrying the orders decided on that
bar. An order decided on a batch fills at the next bar's open (latency 1 bar).

Strategy (long only, full size, integer math throughout, fully deterministic):
  - Entry: buy all cash when the latest close is at least 2.00% below the
    highest high of the last 181 bars (a sharp intraday dip), or at least
    1.50% below it while the 15-minute return is already positive (a dip
    that has started to bounce). Fees plus slippage plus pool impact cost
    roughly 30-40 bps a round trip, so only a real dip is worth buying.
  - Exit: sell the whole position when it is worth 1.50% over its cost
    (take profit), or when it falls 0.80% below the highest value it
    reached while held (trailing stop).
  - Everything else: hold cash. No shorts, no leverage, no randomness, no
    network, no wall clock, no files. Caps, fees, scales and the warm-up
    length are read from the hello message, never hard-coded.

Backtest on the frozen dev window (1,440 bars): net PnL +$13.62 USDC,
2 trades, max drawdown 0.64% (local replay; see BUILD_LOG.md).
"""

import json
import sys

# Strategy parameters (basis points).
LOOKBACK_BARS = 181        # bars whose highs define the dip reference
DIP_BPS = 200              # primary entry: close this far below the high
DIP2_BPS = 150             # secondary entry: close this far below the high
BOUNCE_BPS = 20            # secondary entry: 15-bar return at least this
BOUNCE_BARS = 15           # bars back for the bounce check
TAKE_PROFIT_BPS = 150      # exit: position worth this far over its cost
TRAIL_BPS = 80             # exit: position this far below its peak value
MAX_SLIPPAGE_BPS = 100     # 1% past the close the order was decided on
SYMBOL = "CBBTC"


def main():
    src = sys.stdin.buffer
    out = sys.stdout

    hello = None
    warmup_bars = 0
    min_notional = 1_000_000
    quote_scale = 6
    price_scale = 5
    qty_scale = 8

    closes = []            # closes of the bars seen, oldest first
    highs = []             # highs of the bars seen, oldest first
    cash = 0
    qty = 0
    cost = 0
    peak_value = 0         # highest position value seen while holding
    next_id = 1

    def value_at(price):
        return qty * price * (10 ** quote_scale) // (10 ** (qty_scale + price_scale))

    while True:
        raw = src.readline()
        if not raw:
            return 1
        line = raw.decode("utf-8").strip()
        if not line:
            continue
        msg = json.loads(line)
        kind = msg.get("type")

        if kind == "hello":
            if msg.get("protocol") != "agent-fun/bars-replay/v1":
                return 1
            hello = msg
            warmup_bars = int(msg.get("warmup_bars") or 0)
            fees = msg.get("fees") or {}
            min_notional = int(fees.get("min_notional_quote_units") or 1_000_000)
            capital = msg.get("capital") or {}
            quote_scale = int(capital.get("quote_scale") or 6)
            for s in msg.get("symbols") or []:
                if s.get("symbol") == SYMBOL:
                    price_scale = int(s.get("price_scale") or 5)
                    qty_scale = int(s.get("qty_scale") or 8)
            account = msg.get("capital") or {}
            cash = int(msg["capital"]["quote_units"])
            continue

        if kind == "done":
            return 0

        if kind != "batch" or hello is None:
            return 1

        seq = msg["seq"]
        # Fold the batch's bars into history; only CBBTC exists here.
        fresh = False
        for bar in msg.get("bars") or []:
            if bar.get("symbol") != SYMBOL:
                continue
            closes.append(int(bar["c"]))
            highs.append(int(bar["h"]))
            fresh = True
        # The account the harness reports is authoritative.
        account = msg.get("account") or {}
        cash = int(account.get("cash_quote_units") or 0)
        qty = 0
        cost = 0
        for pos in account.get("positions") or []:
            if pos.get("symbol") == SYMBOL:
                qty = int(pos.get("qty") or 0)
                cost = int(pos.get("cost_quote_units") or 0)
        if qty == 0:
            peak_value = 0

        orders = []
        # Only decide on a batch that carried a fresh bar, and never during
        # the warm-up: orders decided there are rejected.
        if fresh and seq >= warmup_bars and closes:
            close = closes[-1]
            if qty > 0 and cost > 0:
                pos_value = value_at(close)
                if pos_value > peak_value:
                    peak_value = pos_value
                if pos_value * 10000 >= cost * (10000 + TAKE_PROFIT_BPS):
                    orders.append({
                        "side": "sell",
                        "client_id": "o%d" % next_id,
                        "symbol": SYMBOL,
                        "qty": str(qty),
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    })
                    next_id += 1
                elif (peak_value > 0
                        and pos_value * 10000 <= peak_value * (10000 - TRAIL_BPS)):
                    orders.append({
                        "side": "sell",
                        "client_id": "o%d" % next_id,
                        "symbol": SYMBOL,
                        "qty": str(qty),
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    })
                    next_id += 1
            elif qty == 0 and cash >= min_notional:
                if len(highs) >= LOOKBACK_BARS and len(closes) > BOUNCE_BARS:
                    high = max(highs[-LOOKBACK_BARS:])
                    buy = close * 10000 <= high * (10000 - DIP_BPS)
                    if not buy:
                        bounce = ((close - closes[-1 - BOUNCE_BARS]) * 10000
                                  >= closes[-1 - BOUNCE_BARS] * BOUNCE_BPS)
                        buy = (close * 10000 <= high * (10000 - DIP2_BPS)
                               and bounce)
                    if buy:
                        orders.append({
                            "side": "buy",
                            "client_id": "o%d" % next_id,
                            "symbol": SYMBOL,
                            "notional_quote_units": str(cash),
                            "max_slippage_bps": MAX_SLIPPAGE_BPS,
                        })
                        next_id += 1

        out.write(json.dumps(
            {"type": "reply", "seq": seq, "orders": orders},
            separators=(",", ":")) + "\n")
        out.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())

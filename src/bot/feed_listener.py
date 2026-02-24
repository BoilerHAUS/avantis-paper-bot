from __future__ import annotations

import argparse
import asyncio
import os
import signal
import time
from typing import Any

from avantis_trader_sdk import FeedClient

from .candles import CandleBuilder
from .storage import candles_path
from .utils import jsonl_append


def _default_ws_url() -> str:
    ws = os.environ.get("AVANTIS_WS_URL")
    if not ws:
        raise SystemExit(
            "Missing AVANTIS_WS_URL. Set it to the Avantis/Pyth websocket endpoint (wss://...)."
        )
    return ws


def _ts_now() -> int:
    return int(time.time())


async def main_async(pair: str, tf_min: int) -> None:
    ws_url = _default_ws_url()

    builder = CandleBuilder(tf_min=tf_min)
    out_path = candles_path(pair, tf_min)

    def on_ws_error(e: Exception) -> None:
        print(f"[feed] websocket error: {e}")

    def on_ws_close(e: Exception) -> None:
        print(f"[feed] websocket closed: {e}")

    feed = FeedClient(ws_url, on_error=on_ws_error, on_close=on_ws_close)

    def on_price(data: Any) -> None:
        # The SDK docs don't fully specify payload shape; we handle common cases.
        ts = None
        price = None

        if isinstance(data, dict):
            ts = data.get("timestamp") or data.get("ts") or data.get("publish_time")
            price = data.get("price") or data.get("p")

        # Some feeds may provide objects; try attributes.
        if ts is None and hasattr(data, "timestamp"):
            ts = getattr(data, "timestamp")
        if price is None and hasattr(data, "price"):
            price = getattr(data, "price")

        if ts is None:
            ts = _ts_now()
        # normalize ts to seconds
        try:
            ts = int(ts)
            if ts > 10_000_000_000:  # ms
                ts = ts // 1000
        except Exception:
            ts = _ts_now()

        try:
            price_f = float(price)
        except Exception:
            return

        closed = builder.on_tick(ts, price_f)
        if closed:
            jsonl_append(out_path, closed.as_dict())
            print(
                f"[candle] closed {pair} {tf_min}m @ {closed.start_ts} o={closed.o} h={closed.h} l={closed.l} c={closed.c} ticks={closed.ticks}"
            )

    print(f"[feed] connecting ws={ws_url} pair={pair} tf={tf_min}m -> {out_path}")
    feed.register_price_feed_callback(pair, on_price)

    # The feed loop runs until cancelled.
    await feed.listen_for_price_updates()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="ETH/USD")
    ap.add_argument("--tf-min", type=int, default=15)
    args = ap.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop = asyncio.Event()

    def _handle(*_: Any) -> None:
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle)
        except NotImplementedError:
            pass

    async def runner() -> None:
        task = asyncio.create_task(main_async(args.pair, args.tf_min))
        await stop.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    loop.run_until_complete(runner())


if __name__ == "__main__":
    main()

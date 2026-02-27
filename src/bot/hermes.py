from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

import httpx


def _ts_now() -> int:
    return int(time.time())


@dataclass
class HermesPrice:
    ts: int
    price: float


class HermesClient:
    """Minimal client for Pyth Hermes.

    We use Hermes as a reliable, public price source to build candles for paper trading.

    - Discover price feed id by symbol query (e.g. "ETH/USD")
    - Subscribe via SSE streaming endpoint

    Notes:
    - Hermes emits SSE events with lines like `data: {...}`.
    - Payload shapes can vary; we defensively extract timestamp/price fields.
    """

    def __init__(self, base_url: str = "https://hermes.pyth.network"):
        self.base_url = base_url.rstrip("/")

    async def resolve_price_id(self, symbol: str) -> str:
        # Hermes supports searching price feeds by query.
        # Example: GET /v2/price_feeds?query=ETH%2FUSD
        url = f"{self.base_url}/v2/price_feeds"
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, params={"query": symbol})
            r.raise_for_status()
            data = r.json()

        if not isinstance(data, list) or not data:
            raise RuntimeError(f"Hermes: no price feeds found for query={symbol!r}")

        # Prefer an exact symbol match if present.
        for it in data:
            if isinstance(it, dict):
                attrs = it.get("attributes")
                if isinstance(attrs, dict) and attrs.get("symbol") == symbol:
                    pid = it.get("id")
                    if isinstance(pid, str) and pid:
                        return pid

        pid = data[0].get("id") if isinstance(data[0], dict) else None
        if not isinstance(pid, str) or not pid:
            raise RuntimeError(f"Hermes: could not extract price id for query={symbol!r}")
        return pid

    async def stream_price(self, price_id: str) -> AsyncIterator[HermesPrice]:
        # SSE stream endpoint.
        # Most deployments expose: /v2/updates/price/stream?ids[]=<id>
        url = f"{self.base_url}/v2/updates/price/stream"
        params = {"ids[]": price_id}

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url, params=params) as r:
                r.raise_for_status()

                async for line in r.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue
                    raw = line[len("data:") :].strip()
                    if not raw:
                        continue

                    try:
                        payload = json.loads(raw)
                    except Exception:
                        continue

                    hp = _extract_price(payload)
                    if hp is not None:
                        yield hp


def _extract_price(payload: Any) -> Optional[HermesPrice]:
    """Best-effort extraction of timestamp+price from Hermes payload."""

    # Common Hermes payload: {"binary": ..., "parsed": [{"price": {"price": "...", "expo": -8, "publish_time": 123}}]}
    ts = None
    price = None

    expo = None

    if isinstance(payload, dict):
        parsed = payload.get("parsed")
        if isinstance(parsed, list) and parsed:
            item = parsed[0]
            if isinstance(item, dict):
                p = item.get("price")
                if isinstance(p, dict):
                    ts = p.get("publish_time") or p.get("timestamp")
                    price = p.get("price")
                    expo = p.get("expo")

        # Fallbacks if shape differs
        ts = ts or payload.get("publish_time") or payload.get("timestamp") or payload.get("ts")
        price = price or payload.get("price")
        expo = expo or payload.get("expo")

    if ts is None:
        ts = _ts_now()

    try:
        ts_i = int(ts)
        if ts_i > 10_000_000_000:  # ms
            ts_i //= 1000
    except Exception:
        ts_i = _ts_now()

    try:
        # Hermes often returns price as string (integer, fixed-point with expo)
        p_int = float(price)
    except Exception:
        return None

    # If expo is present, apply it (Pyth fixed-point)
    if expo is not None:
        try:
            expo_i = int(expo)
            price_f = p_int * (10**expo_i)
        except Exception:
            price_f = p_int
    else:
        price_f = p_int

    return HermesPrice(ts=ts_i, price=float(price_f))

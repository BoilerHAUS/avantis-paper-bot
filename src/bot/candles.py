from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import floor
from typing import Optional


@dataclass
class Candle:
    start_ts: int  # unix seconds, bucket start
    tf_sec: int
    o: float
    h: float
    l: float
    c: float
    ticks: int = 0

    def as_dict(self) -> dict:
        return {
            "start_ts": self.start_ts,
            "tf_sec": self.tf_sec,
            "o": self.o,
            "h": self.h,
            "l": self.l,
            "c": self.c,
            "ticks": self.ticks,
        }


class CandleBuilder:
    """Builds OHLC candles from price ticks.

    Notes:
      - Uses tick-count as volume proxy (ticks).
      - Buckets by tf_sec aligned to epoch.
    """

    def __init__(self, tf_min: int):
        if tf_min <= 0:
            raise ValueError("tf_min must be > 0")
        self.tf_sec = tf_min * 60
        self._cur: Optional[Candle] = None

    def _bucket_start(self, ts: int) -> int:
        return int(floor(ts / self.tf_sec) * self.tf_sec)

    def on_tick(self, ts: int, price: float) -> Optional[Candle]:
        """Consume a tick and return a CLOSED candle if the tick rolls the bucket."""
        b = self._bucket_start(ts)

        if self._cur is None:
            self._cur = Candle(start_ts=b, tf_sec=self.tf_sec, o=price, h=price, l=price, c=price, ticks=1)
            return None

        # same bucket
        if b == self._cur.start_ts:
            self._cur.h = max(self._cur.h, price)
            self._cur.l = min(self._cur.l, price)
            self._cur.c = price
            self._cur.ticks += 1
            return None

        # bucket advanced → close previous, start new
        closed = self._cur
        self._cur = Candle(start_ts=b, tf_sec=self.tf_sec, o=price, h=price, l=price, c=price, ticks=1)
        return closed

    @staticmethod
    def iso(ts: int) -> str:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

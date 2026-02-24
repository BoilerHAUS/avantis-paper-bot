from __future__ import annotations

from math import sqrt


def sma(xs: list[float], n: int) -> float | None:
    if n <= 0 or len(xs) < n:
        return None
    return sum(xs[-n:]) / n


def stdev(xs: list[float], n: int) -> float | None:
    if n <= 1 or len(xs) < n:
        return None
    m = sum(xs[-n:]) / n
    v = sum((x - m) ** 2 for x in xs[-n:]) / (n - 1)
    return sqrt(v)


def zscore(xs: list[float], n: int) -> float | None:
    m = sma(xs, n)
    s = stdev(xs, n)
    if m is None or s is None or s == 0:
        return None
    return (xs[-1] - m) / s


def atr(high: list[float], low: list[float], close: list[float], n: int) -> float | None:
    if len(close) < n + 1:
        return None
    trs: list[float] = []
    for i in range(-n, 0):
        h = high[i]
        l = low[i]
        pc = close[i - 1]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    return sum(trs) / n

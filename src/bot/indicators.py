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


def adx(high: list[float], low: list[float], close: list[float], n: int = 14) -> float | None:
    if len(close) < (n * 2 + 1):
        return None

    trs: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []

    for i in range(1, len(close)):
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]

        pdm = up_move if up_move > down_move and up_move > 0 else 0.0
        mdm = down_move if down_move > up_move and down_move > 0 else 0.0

        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        trs.append(tr)
        plus_dm.append(pdm)
        minus_dm.append(mdm)

    # Wilder-style rolling sums (simplified)
    tr_n = sum(trs[:n])
    pdm_n = sum(plus_dm[:n])
    mdm_n = sum(minus_dm[:n])

    dxs: list[float] = []
    for i in range(n, len(trs)):
        tr_n = tr_n - (tr_n / n) + trs[i]
        pdm_n = pdm_n - (pdm_n / n) + plus_dm[i]
        mdm_n = mdm_n - (mdm_n / n) + minus_dm[i]

        if tr_n <= 0:
            continue

        pdi = 100.0 * (pdm_n / tr_n)
        mdi = 100.0 * (mdm_n / tr_n)
        den = pdi + mdi
        if den <= 0:
            continue
        dx = 100.0 * abs(pdi - mdi) / den
        dxs.append(dx)

    if len(dxs) < n:
        return None

    return sum(dxs[-n:]) / n

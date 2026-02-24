"""Paper execution engine (v0.1).

Simulates:
- market fills with vol-based slippage (simple model)
- a single position at a time (v0.1)

SL/TP triggering between cycles will come next.
"""

from __future__ import annotations

from dataclasses import asdict
from math import copysign
from typing import Optional

from .models import OrderPlan, PaperState, Position


def apply_slippage(price: float, slip_bps: float, side: str) -> float:
    """Move price against us by slip_bps."""
    direction = 1.0 if side == "long" else -1.0
    # For longs we pay higher, for shorts we sell lower
    return price * (1.0 + direction * (slip_bps / 10_000.0))


def open_position(state: PaperState, plan: OrderPlan, fill_price: float, ts: int) -> PaperState:
    pos = Position(
        side=plan.side or "long",
        notional_usd=plan.target_notional_usd,
        collateral_usd=plan.collateral_usd,
        leverage=plan.leverage,
        entry_price=fill_price,
        avg_price=fill_price,
        stop_loss=plan.stop_loss,
        take_profit=plan.take_profit,
        opened_ts=ts,
    )
    state.position = pos
    return state


def close_position(state: PaperState, fill_price: float) -> PaperState:
    pos = state.position
    if not pos:
        return state

    # PnL approx in USD using notional and price move
    # notional ~ position_size * entry_price; assume linear.
    if pos.side == "long":
        pnl = pos.notional_usd * (fill_price / pos.avg_price - 1.0)
    else:
        pnl = pos.notional_usd * (pos.avg_price / fill_price - 1.0)

    state.equity += pnl
    state.daily_pnl += pnl
    state.position = None
    return state


def scale_position(state: PaperState, plan: OrderPlan, fill_price: float) -> PaperState:
    pos = state.position
    if not pos:
        return state

    target = plan.target_notional_usd
    if target <= pos.notional_usd:
        return state

    add = target - pos.notional_usd
    # Weighted avg
    new_avg = (pos.avg_price * pos.notional_usd + fill_price * add) / (pos.notional_usd + add)
    pos.avg_price = new_avg
    pos.notional_usd = target
    pos.collateral_usd = plan.collateral_usd
    pos.leverage = plan.leverage
    pos.stop_loss = plan.stop_loss
    pos.take_profit = plan.take_profit
    return state


def execute_paper(state: PaperState, plan: OrderPlan, last_price: float, slip_bps: float, ts: int) -> PaperState:
    """Execute the plan at a simulated market fill."""
    state.last_price = last_price

    if plan.action == "hold":
        return state

    if plan.action == "close":
        if state.position:
            fill = apply_slippage(last_price, slip_bps, side=state.position.side)
            return close_position(state, fill)
        return state

    if plan.action == "open":
        if plan.side is None:
            return state
        fill = apply_slippage(last_price, slip_bps, side=plan.side)
        return open_position(state, plan, fill, ts)

    if plan.action == "flip":
        # close existing
        if state.position:
            fill_close = apply_slippage(last_price, slip_bps, side=state.position.side)
            state = close_position(state, fill_close)
        # open new
        if plan.side is None:
            return state
        fill_open = apply_slippage(last_price, slip_bps, side=plan.side)
        return open_position(state, plan, fill_open, ts)

    if plan.action == "scale":
        if not state.position or plan.side is None:
            return state
        fill = apply_slippage(last_price, slip_bps, side=plan.side)
        return scale_position(state, plan, fill)

    return state

"""Paper execution engine (v0.2).

Adds basic in-position trade management:
- partial take-profit (50% at 1.5R via plan.take_profit)
- trailing stop on remaining size (distance captured at entry)
- stop-loss enforcement each cycle
"""

from __future__ import annotations

from .models import OrderPlan, PaperState, Position


def apply_slippage(price: float, slip_bps: float, side: str) -> float:
    direction = 1.0 if side == "long" else -1.0
    return price * (1.0 + direction * (slip_bps / 10_000.0))


def _realize_pnl(pos: Position, fill_price: float, close_notional: float) -> float:
    if close_notional <= 0 or pos.avg_price <= 0:
        return 0.0
    close_notional = min(close_notional, pos.notional_usd)
    if pos.side == "long":
        return close_notional * (fill_price / pos.avg_price - 1.0)
    return close_notional * (pos.avg_price / fill_price - 1.0)


def open_position(state: PaperState, plan: OrderPlan, fill_price: float, ts: int) -> PaperState:
    trail_distance = abs(fill_price - plan.stop_loss) if plan.stop_loss is not None else None
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
        initial_notional_usd=plan.target_notional_usd,
        partial_taken=False,
        trail_distance=trail_distance,
    )
    state.position = pos
    return state


def close_position(state: PaperState, fill_price: float, close_notional: float | None = None) -> PaperState:
    pos = state.position
    if not pos:
        return state

    amount = pos.notional_usd if close_notional is None else min(close_notional, pos.notional_usd)
    pnl = _realize_pnl(pos, fill_price, amount)
    state.equity += pnl
    state.daily_pnl += pnl

    pos.notional_usd -= amount
    if pos.notional_usd <= 1e-9:
        state.position = None
    else:
        # Keep leverage roughly consistent after partial close.
        if pos.leverage > 0:
            pos.collateral_usd = pos.notional_usd / pos.leverage
        state.position = pos
    return state


def scale_position(state: PaperState, plan: OrderPlan, fill_price: float) -> PaperState:
    pos = state.position
    if not pos:
        return state

    target = plan.target_notional_usd
    if target <= pos.notional_usd:
        return state

    add = target - pos.notional_usd
    new_avg = (pos.avg_price * pos.notional_usd + fill_price * add) / (pos.notional_usd + add)
    pos.avg_price = new_avg
    pos.notional_usd = target
    pos.collateral_usd = plan.collateral_usd
    pos.leverage = plan.leverage
    pos.stop_loss = plan.stop_loss
    pos.take_profit = plan.take_profit
    if pos.initial_notional_usd is None:
        pos.initial_notional_usd = target
    return state


def _manage_position(state: PaperState, last_price: float, slip_bps: float) -> PaperState:
    pos = state.position
    if not pos:
        return state

    # 1) hard stop
    if pos.stop_loss is not None:
        if (pos.side == "long" and last_price <= pos.stop_loss) or (pos.side == "short" and last_price >= pos.stop_loss):
            fill = apply_slippage(last_price, slip_bps, side=pos.side)
            return close_position(state, fill)

    # 2) one-time partial at TP (50%)
    if not pos.partial_taken and pos.take_profit is not None:
        hit_tp = (pos.side == "long" and last_price >= pos.take_profit) or (pos.side == "short" and last_price <= pos.take_profit)
        if hit_tp:
            fill = apply_slippage(last_price, slip_bps, side=pos.side)
            close_amt = (pos.initial_notional_usd or pos.notional_usd) * 0.5
            close_amt = min(close_amt, pos.notional_usd)
            state = close_position(state, fill, close_notional=close_amt)
            if state.position:
                state.position.partial_taken = True
            return state

    # 3) trailing stop on remaining half
    pos = state.position
    if not pos:
        return state
    if pos.partial_taken and pos.trail_distance and pos.trail_distance > 0:
        if pos.side == "long":
            new_stop = last_price - pos.trail_distance
            pos.stop_loss = max(pos.stop_loss or new_stop, new_stop)
        else:
            new_stop = last_price + pos.trail_distance
            pos.stop_loss = min(pos.stop_loss or new_stop, new_stop)
        state.position = pos

    return state


def execute_paper(state: PaperState, plan: OrderPlan, last_price: float, slip_bps: float, ts: int) -> PaperState:
    state.last_price = last_price

    # Always enforce in-position management first.
    state = _manage_position(state, last_price=last_price, slip_bps=slip_bps)

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
        if state.position:
            fill_close = apply_slippage(last_price, slip_bps, side=state.position.side)
            state = close_position(state, fill_close)
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

from __future__ import annotations

from bot.models import MarketRegime
from bot.strategies import REGIME_CLASSIFIER_SCHEMA_VERSION, StrategyConfig, analyze_signal, classify_regime


def _candles_from_closes(closes: list[float], *, tf_sec: int = 900) -> list[dict]:
    candles: list[dict] = []
    for idx, close in enumerate(closes):
        candles.append(
            {
                "start_ts": 1_700_100_000 + idx * tf_sec,
                "tf_sec": tf_sec,
                "o": close - 0.4,
                "h": close + 0.8,
                "l": close - 0.8,
                "c": close,
            }
        )
    return candles


def test_regime_classifier_detects_stable_trend_up_window() -> None:
    closes = [100.0 + i * 1.1 for i in range(80)]

    result = classify_regime(_candles_from_closes(closes))

    assert result.schema_version == REGIME_CLASSIFIER_SCHEMA_VERSION
    assert result.label is MarketRegime.TREND_UP
    assert result.confidence >= 0.45
    assert result.probabilities["trend_up"] == result.confidence
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-6
    assert result.stand_down is False


def test_regime_classifier_detects_range_window() -> None:
    closes = [100.0 + ((i % 4) - 1.5) * 0.55 for i in range(80)]

    result = classify_regime(_candles_from_closes(closes))

    assert result.label is MarketRegime.RANGE
    assert result.probabilities["range"] >= 0.35
    assert result.features["trend_strength"] < 0.35


def test_regime_classifier_marks_transition_as_stand_down() -> None:
    closes = [100.0 + i * 0.8 for i in range(45)]
    closes.extend(136.0 - (i * 0.15) for i in range(20))
    closes.extend(133.0 + ((i % 3) - 1) * 0.2 for i in range(15))

    result = classify_regime(_candles_from_closes(closes))
    analysis = analyze_signal(_candles_from_closes(closes))

    assert result.label is MarketRegime.TRANSITION
    assert result.stand_down is True
    assert 0.0 <= result.uncertainty_score <= 1.0
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-6
    assert analysis.regime.label is MarketRegime.TRANSITION
    assert analysis.regime.stand_down is True


def test_regime_boundary_churn_is_bounded_and_measured() -> None:
    cfg = StrategyConfig()
    closes = [100.0 + i * 0.9 for i in range(55)]
    closes.extend(149.5 - i * 0.8 for i in range(35))
    candles = _candles_from_closes(closes)

    labels = [
        classify_regime(candles[idx - 60 : idx], cfg).label.value
        for idx in range(60, len(candles) + 1)
    ]
    churn = sum(1 for prev, cur in zip(labels, labels[1:]) if prev != cur)

    assert "trend_up" in labels
    assert "transition" in labels
    assert "trend_down" in labels
    assert 2 <= churn <= 8

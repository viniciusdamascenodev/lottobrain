import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.analysis.pipeline import build_frequency_summary, generate_predictions


def test_build_frequency_summary_counts_numbers():
    history = [
        {"numbers": [1, 2, 3, 4, 5, 6]},
        {"numbers": [1, 2, 3, 4, 5, 7]},
        {"numbers": [10, 11, 12, 13, 14, 15]},
    ]

    summary = build_frequency_summary(history)

    assert summary["1"] == 2
    assert summary["2"] == 2
    assert summary["15"] == 1


def test_generate_predictions_returns_structured_output():
    history = [
        {"numbers": [1, 2, 3, 4, 5, 6]},
        {"numbers": [1, 2, 3, 4, 5, 7]},
        {"numbers": [10, 11, 12, 13, 14, 15]},
    ]

    result = generate_predictions(history, "mega_sena", top_n=2)

    assert len(result["predictions"]) == 2
    assert all(len(item["numbers"]) == 6 for item in result["predictions"])
    assert all(item["probability"] > 0 for item in result["predictions"])

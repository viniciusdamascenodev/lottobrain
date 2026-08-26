import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.analysis.pipeline import (
    compute_basic_stats,
    generate_predictions,
    load_history,
    train_models,
)

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def run_analysis(lottery_key: str) -> dict:
    history = load_history(lottery_key)
    if not history:
        history = [{"numbers": [1, 2, 3, 4, 5, 6]}]

    stats = compute_basic_stats(history)
    predictions = generate_predictions(history, lottery_key)
    models = train_models(history, lottery_key)

    report = {
        "lottery": lottery_key,
        "stats": stats,
        "predictions": predictions,
        "models": models,
    }

    with (REPORTS_DIR / f"{lottery_key}_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    return report


if __name__ == "__main__":
    for lottery in ["mega_sena", "lotofacil", "mais_milionaria", "mega_millions", "powerball", "euro_millions"]:
        print(run_analysis(lottery)["lottery"])

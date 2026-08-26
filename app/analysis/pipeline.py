import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_history(lottery_key: str) -> List[Dict]:
    path = RAW_DIR / lottery_key / f"{lottery_key}_resultados.json"
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_frequency_summary(history: List[Dict]) -> Dict[str, int]:
    counts = Counter()
    for item in history:
        numbers = item.get("numbers") or item.get("bolas") or []
        for number in numbers:
            counts[str(number)] += 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def compute_basic_stats(history: List[Dict]) -> Dict[str, float]:
    if not history:
        return {"average_gap": 0.0, "draw_count": 0.0, "most_common_count": 0.0}

    numbers = [num for item in history for num in (item.get("numbers") or [])]
    return {
        "average_gap": round(float(mean([abs(numbers[i] - numbers[i + 1]) for i in range(len(numbers) - 1)])) if len(numbers) > 1 else 0.0, 2),
        "draw_count": float(len(history)),
        "most_common_count": float(max(Counter(numbers).values(), default=0)),
    }


def generate_predictions(history: List[Dict], lottery_key: str, top_n: int = 5) -> Dict[str, object]:
    frequency = build_frequency_summary(history)
    ranked = sorted(frequency.items(), key=lambda item: item[1], reverse=True)
    top_numbers = [int(num) for num, _ in ranked[:10]]

    predictions = []
    for idx, number in enumerate(top_numbers[:top_n], start=1):
        predictions.append({
            "numbers": [number, number + 1, number + 2, number + 3, number + 4, number + 5],
            "probability": round(0.5 + (idx / 10), 3),
            "model": "frequency-based",
        })

    return {
        "lottery": lottery_key,
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "predictions": predictions,
    }


def build_dataset(history: List[Dict], lottery_key: str) -> pd.DataFrame:
    rows = []
    for idx, item in enumerate(history):
        numbers = item.get("numbers") or []
        if len(numbers) < 6:
            continue
        feature_row = {"draw_id": idx}
        for position, number in enumerate(numbers[:6], start=1):
            feature_row[f"n{position}"] = number
        rows.append(feature_row)

    df = pd.DataFrame(rows)
    df.to_parquet(PROCESSED_DIR / f"{lottery_key}_dataset.parquet", index=False)
    return df


def train_models(history: List[Dict], lottery_key: str) -> Dict[str, object]:
    df = build_dataset(history, lottery_key)
    if df.empty:
        return {"models": [], "dataset_rows": 0}

    if len(df) < 3:
        return {
            "models": [{
                "name": "fallback-frequency",
                "accuracy": 0.0,
                "description": "Modelo alternativo usado quando há poucos dados históricos para treinamento.",
            }],
            "dataset_rows": int(len(df)),
        }

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    target = df["n6"]
    features = df[[col for col in df.columns if col.startswith("n") and col != "n6"]]
    X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    return {
        "models": [{
            "name": "LogisticRegression",
            "accuracy": round(float(accuracy_score(y_test, preds)), 3),
            "description": "Modelo simples baseado em features de posição.",
        }],
        "dataset_rows": int(len(df)),
    }

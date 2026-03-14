"""
Train the ML level predictor on synthetic data and save the model.

Usage (from the pulse-final directory):
    python -m ml.train

Generates 1000 synthetic users across 3 archetypes, trains a
Logistic Regression classifier, and saves it to ml/models/level_predictor.pkl.
"""

import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from ml.features import FEATURE_COLUMNS

MODEL_PATH = Path(__file__).parent / "models" / "level_predictor.pkl"
LEVELS = ["novice", "basic", "advanced"]
RNG = np.random.default_rng(42)


def _topic_scores(base_score: float, n: int) -> list[float]:
    """Generate 7 per-topic scores correlated with base_score."""
    scores = base_score + RNG.normal(0, 0.1, size=(n, 7))
    return np.clip(scores, 0.0, 1.0)


def generate_synthetic_data(n_samples: int = 1000) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic training data for 3 user archetypes.

    Novice   (label 0): low score, slow answers, high skip count, few lessons
    Basic    (label 1): medium score, medium speed, some skips, some lessons
    Advanced (label 2): high score, fast answers, no skips, many lessons
    """
    n_per_class = n_samples // 3
    # Make up the remainder in novice
    counts = [n_per_class + (n_samples - 3 * n_per_class), n_per_class, n_per_class]

    rows = []
    labels = []

    archetypes = [
        # (label, score_range, time_range_ms, skip_range, correct_range, lessons_range)
        (0, (0.0,  0.39), (10000, 20000), (3, 10), (0.2, 0.5),  (0,  3)),
        (1, (0.4,  0.69), ( 4000,  9000), (0,  4), (0.5, 0.75), (2,  8)),
        (2, (0.7,  1.0 ), ( 1000,  4000), (0,  1), (0.75, 1.0), (5, 15)),
    ]

    for (label, s_range, t_range, skip_range, cr_range, l_range), n in zip(archetypes, counts):
        base_scores = RNG.uniform(*s_range, size=n)
        topic_sc = _topic_scores(base_scores.mean(), n)  # shape (n, 7)
        avg_times = RNG.uniform(*t_range, size=n)
        skip_counts = RNG.integers(*skip_range, size=n)
        total_answers = RNG.integers(10, 50, size=n)
        correct_rates = RNG.uniform(*cr_range, size=n)
        lesson_counts = RNG.integers(*l_range, size=n)

        for i in range(n):
            row = [
                base_scores[i],       # onboarding_score
                *topic_sc[i],         # topic_stocks … topic_market_logic (7)
                avg_times[i],         # avg_time_ms
                correct_rates[i],     # correct_rate
                float(total_answers[i]),  # total_answers
                float(skip_counts[i]),    # skip_count
                float(lesson_counts[i]),  # lessons_completed
            ]
            rows.append(row)
            labels.append(label)

    X = np.array(rows)
    y = np.array(labels)
    # Shuffle
    idx = RNG.permutation(len(y))
    return X[idx], y[idx]


def train():
    print("Generating synthetic data…")
    X, y = generate_synthetic_data(n_samples=1200)
    print(f"  {len(X)} samples, {X.shape[1]} features")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])

    print("Training Logistic Regression…")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"  Accuracy: {acc:.2%}")
    print(classification_report(y_test, y_pred, target_names=LEVELS))

    # Feature importances (coefficients from LogisticRegression)
    clf = model.named_steps["clf"]
    print("Feature coefficients (per class):")
    for class_idx, level in enumerate(LEVELS):
        top = sorted(
            zip(FEATURE_COLUMNS, clf.coef_[class_idx]),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:5]
        print(f"  {level}: " + ", ".join(f"{f}={v:+.2f}" for f, v in top))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"\nModel saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()

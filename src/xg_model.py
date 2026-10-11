"""
xG Model — trains an Expected Goals model on StatsBomb open data.

Expected Goals (xG) estimates the probability that a given shot becomes a goal,
based on the characteristics of the shot. This module pulls shots from a set of
StatsBomb matches, engineers features, trains a gradient-boosted model,
validates it (ROC-AUC, Brier, log-loss, reliability curve), reports feature
importances, and saves the model + a metrics.json for the web app.

Usage:
    python src/xg_model.py          # train, validate, save model + metrics + plots
"""

import os
import math
import json
import warnings
import pickle

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

from statsbombpy import sb
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split
from sklearn.calibration import calibration_curve
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

# StatsBomb pitch is 120 x 80. Goal at x=120, centred on y=40, posts at 36 & 44.
GOAL_X, GOAL_Y = 120.0, 40.0
POST_1, POST_2 = 36.0, 44.0

_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(_HERE, "..", "models")
OUTPUT_DIR = os.path.join(_HERE, "..", "output")
MODEL_PATH = os.path.join(MODEL_DIR, "xg_model.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")

# Theme (shared with the rest of the app)
BG, FG, MUTED = "#12161c", "#e8edf2", "#8a97a6"
ACCENT, ACCENT2, LINE = "#4ea1ff", "#ffd34e", "#3a4350"


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
def shot_features(x, y):
    """Geometric features for a shot taken from location (x, y)."""
    dx, dy = GOAL_X - x, GOAL_Y - y
    distance = math.hypot(dx, dy)
    a = math.hypot(GOAL_X - x, POST_1 - y)
    b = math.hypot(GOAL_X - x, POST_2 - y)
    goal_width = POST_2 - POST_1
    cos_angle = (a**2 + b**2 - goal_width**2) / (2 * a * b + 1e-9)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    angle = math.acos(cos_angle)  # radians; wider = better chance
    return distance, angle


FEATURES = [
    "distance", "angle", "header", "volley", "first_time",
    "open_play", "from_corner", "from_free_kick", "from_counter",
    "under_pressure",
]
# Human-readable labels for the feature-importance chart
FEATURE_LABELS = {
    "distance": "Distance to goal", "angle": "Shot angle", "header": "Header",
    "volley": "Volley", "first_time": "First-time shot", "open_play": "Open play",
    "from_corner": "From corner", "from_free_kick": "From free kick",
    "from_counter": "From counter", "under_pressure": "Under pressure",
}


def _shot_row(s, match_id=None):
    loc = s.get("location")
    if not isinstance(loc, list) or len(loc) < 2:
        return None
    x, y = loc[0], loc[1]
    distance, angle = shot_features(x, y)
    body = s.get("shot_body_part")
    technique = s.get("shot_technique")
    pp = s.get("play_pattern")
    stype = s.get("shot_type")
    return {
        "match_id": match_id, "x": x, "y": y,
        "distance": distance, "angle": angle,
        "header": 1 if body == "Head" else 0,
        "volley": 1 if technique == "Volley" else 0,
        "first_time": 1 if s.get("shot_first_time") is True else 0,
        "open_play": 1 if stype == "Open Play" else 0,
        "from_corner": 1 if pp == "From Corner" else 0,
        "from_free_kick": 1 if pp == "From Free Kick" else 0,
        "from_counter": 1 if pp == "From Counter" else 0,
        "under_pressure": 1 if s.get("under_pressure") is True else 0,
        "statsbomb_xg": s.get("shot_statsbomb_xg"),
        "is_goal": 1 if s.get("shot_outcome") == "Goal" else 0,
    }


def build_shot_dataset(competitions):
    rows = []
    for comp_id, season_id in competitions:
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as e:
            print(f"  skip comp {comp_id}/{season_id}: {e}")
            continue
        for match_id in matches["match_id"].tolist():
            try:
                events = sb.events(match_id=match_id)
            except Exception:
                continue
            shots = events[events["type"] == "Shot"]
            for _, s in shots.iterrows():
                r = _shot_row(s, match_id)
                if r:
                    rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Validation plots
# ---------------------------------------------------------------------------
def _reliability_plot(y_test, p_test, path):
    frac_pos, mean_pred = calibration_curve(y_test, p_test, n_bins=10, strategy="quantile")
    fig, ax = plt.subplots(figsize=(6, 6), facecolor=BG)
    ax.set_facecolor(BG)
    ax.plot([0, 1], [0, 1], "--", color=MUTED, lw=1.2, label="Perfect calibration")
    ax.plot(mean_pred, frac_pos, "-o", color=ACCENT, lw=2, markersize=7,
            markeredgecolor="white", label="Our xG model")
    ax.set_xlabel("Predicted goal probability (xG)", color=FG, fontsize=11)
    ax.set_ylabel("Actual goal frequency", color=FG, fontsize=11)
    ax.set_title("Calibration — does xG mean what it says?", color=FG, fontsize=13, pad=10)
    ax.tick_params(colors=MUTED)
    for sp in ax.spines.values():
        sp.set_color(LINE)
    ax.legend(facecolor=BG, edgecolor=LINE, labelcolor=FG, fontsize=10)
    ax.grid(alpha=0.12)
    fig.savefig(path, dpi=130, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def _importance_plot(model, X_test, y_test, path):
    result = permutation_importance(model, X_test, y_test, n_repeats=8,
                                    random_state=42, scoring="roc_auc")
    imp = sorted(zip(FEATURES, result.importances_mean), key=lambda z: z[1])
    labels = [FEATURE_LABELS[f] for f, _ in imp]
    vals = [v for _, v in imp]
    fig, ax = plt.subplots(figsize=(7, 6), facecolor=BG)
    ax.set_facecolor(BG)
    ax.barh(labels, vals, color=ACCENT2)
    ax.set_title("What drives the model (permutation importance)", color=FG, fontsize=13, pad=10)
    ax.set_xlabel("Drop in ROC-AUC when shuffled", color=MUTED, fontsize=10)
    ax.tick_params(colors=FG)
    for sp in ax.spines.values():
        sp.set_color(LINE)
    ax.grid(alpha=0.12, axis="x")
    fig.savefig(path, dpi=130, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    return {FEATURE_LABELS[f]: round(float(v), 4) for f, v in imp}


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------
INGESTED_SHOTS = os.path.join(_HERE, "..", "data", "shots.parquet")


def train(competitions, use_ingested=True):
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Prefer the big locally-ingested corpus (src/ingest.py) when available —
    # it's far larger than pulling a handful of competitions over the API.
    if use_ingested and os.path.exists(INGESTED_SHOTS):
        import pandas as _pd
        df = _pd.read_parquet(INGESTED_SHOTS)
        print(f"Training from ingested dataset ({os.path.basename(INGESTED_SHOTS)})...")
        print(f"  {len(df):,} shots, {int(df['is_goal'].sum()):,} goals "
              f"({df['is_goal'].mean()*100:.1f}% conversion), "
              f"{df['match_id'].nunique():,} matches")
    else:
        print("Building shot dataset from StatsBomb open data (API)...")
        df = build_shot_dataset(competitions)
        print(f"  collected {len(df):,} shots, {df['is_goal'].sum():,} goals "
              f"({df['is_goal'].mean()*100:.1f}% conversion)")

    X = df[FEATURES].values
    y = df["is_goal"].values
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)

    model = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_depth=4,
        l2_regularization=1.0, random_state=42)
    model.fit(X_train, y_train)

    p_test = model.predict_proba(X_test)[:, 1]
    auc = float(roc_auc_score(y_test, p_test))
    brier = float(brier_score_loss(y_test, p_test))
    ll = float(log_loss(y_test, p_test))

    print("\n=== Validation (held-out 25%) ===")
    print(f"  ROC-AUC:     {auc:.4f}   (pro xG ~0.78-0.82)")
    print(f"  Brier:       {brier:.4f}   (lower = better calibrated)")
    print(f"  Log loss:    {ll:.4f}")
    print(f"  Predicted goals: {p_test.sum():.1f}  |  Actual: {int(y_test.sum())}")

    # Plots
    calib_png = os.path.join(OUTPUT_DIR, "model_calibration.png")
    imp_png = os.path.join(OUTPUT_DIR, "model_importance.png")
    _reliability_plot(y_test, p_test, calib_png)
    importances = _importance_plot(model, X_test, y_test, imp_png)
    print(f"  saved calibration plot  -> {calib_png}")
    print(f"  saved importance plot   -> {imp_png}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": model, "features": FEATURES}, f)

    metrics = {
        "n_shots": int(len(df)),
        "n_goals": int(df["is_goal"].sum()),
        "conversion_pct": round(float(df["is_goal"].mean() * 100), 1),
        "roc_auc": round(auc, 4),
        "brier": round(brier, 4),
        "log_loss": round(ll, 4),
        "predicted_goals_test": round(float(p_test.sum()), 1),
        "actual_goals_test": int(y_test.sum()),
        "feature_importance": importances,
        "training_competitions": competitions,
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved model   -> {os.path.abspath(MODEL_PATH)}")
    print(f"Saved metrics -> {os.path.abspath(METRICS_PATH)}")
    return model, df


def load_model():
    with open(MODEL_PATH, "rb") as f:
        bundle = pickle.load(f)
    return bundle["model"], bundle["features"]


def predict_xg(model, features, x, y, **kwargs):
    distance, angle = shot_features(x, y)
    row = {
        "distance": distance, "angle": angle,
        "header": kwargs.get("header", 0), "volley": kwargs.get("volley", 0),
        "first_time": kwargs.get("first_time", 0),
        "open_play": kwargs.get("open_play", 1),
        "from_corner": kwargs.get("from_corner", 0),
        "from_free_kick": kwargs.get("from_free_kick", 0),
        "from_counter": kwargs.get("from_counter", 0),
        "under_pressure": kwargs.get("under_pressure", 0),
    }
    X = np.array([[row[f] for f in features]])
    return float(model.predict_proba(X)[:, 1][0])


# Default training set — all in StatsBomb's free open data
TRAIN_COMPS = [
    (43, 3),    # FIFA World Cup 2018
    (11, 90),   # La Liga 2020/2021
    (2, 27),    # Premier League 2015/2016
    (37, 90),   # FA WSL 2020/2021
]

if __name__ == "__main__":
    train(TRAIN_COMPS)

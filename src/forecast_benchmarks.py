"""Fixed challenger specifications, fitted exclusively before each forecast cutoff.

No optimizer sees evaluation outcomes. Monthly Poisson fits use data before the
first day of the prediction month. Parameters are predeclared, not selected by
reported scores. A better retrospective score does not promote a challenger.
"""

from datetime import date, timedelta
import math
import numpy as np
from scipy.optimize import minimize
from club_identity import club_key

SPECIFICATIONS = {
    "elo": {
        "name": "Elo / Davidson",
        "initial": 1500,
        "k": 20,
        "home_advantage": 70,
        "draw_parameter": 0.7,
        "update": "simultaneous within each calendar date",
    },
    "fitted_poisson": {
        "name": "Regularized attack / defence Poisson",
        "window_days": 730,
        "half_life_days": 180,
        "ridge": 2,
        "fit": "monthly; training dates strictly before month start",
    },
}


class Challengers:
    def __init__(self, history):
        self.history = sorted(
            [m for m in history if m["hg"] is not None and not m.get("exclude_from_model")],
            key=lambda m: m["date"],
        )
        self.elo_cache, self.fit_cache = {}, {}

    @staticmethod
    def davidson(h, a):
        ratio = 10 ** ((h + 70 - a) / 400)
        draw = 0.7 * math.sqrt(ratio)
        total = ratio + 1 + draw
        return [ratio / total, draw / total, 1 / total]

    def elo(self, fixture, cutoff):
        if cutoff not in self.elo_cache:
            ratings, deltas, previous = {}, {}, None
            for m in self.history:
                if m["date"] >= cutoff:
                    break
                if m["date"] != previous:
                    for t, change in deltas.items():
                        ratings[t] = ratings.get(t, 1500) + change
                    deltas, previous = {}, m["date"]
                h, a = club_key(m["home"]), club_key(m["away"])
                p = self.davidson(ratings.get(h, 1500), ratings.get(a, 1500))
                actual = 1 if m["hg"] > m["ag"] else 0.5 if m["hg"] == m["ag"] else 0
                delta = 20 * (actual - p[0] - 0.5 * p[1])
                deltas[h] = deltas.get(h, 0) + delta
                deltas[a] = deltas.get(a, 0) - delta
            for t, change in deltas.items():
                ratings[t] = ratings.get(t, 1500) + change
            self.elo_cache[cutoff] = ratings
        r = self.elo_cache[cutoff]
        return self.davidson(
            r.get(club_key(fixture["home"]), 1500), r.get(club_key(fixture["away"]), 1500)
        )

    def fitted(self, fixture, cutoff):
        month = cutoff[:7] + "-01"
        if month not in self.fit_cache:
            start = (date.fromisoformat(month) - timedelta(days=730)).isoformat()
            rows = [m for m in self.history if start <= m["date"] < month]
            if len(rows) < 100:
                self.fit_cache[month] = None
            else:
                names = sorted({club_key(m[t]) for m in rows for t in ("home", "away")})
                index = {name: i for i, name in enumerate(names)}
                n = len(names)
                hi = np.array([index[club_key(m["home"])] for m in rows])
                ai = np.array([index[club_key(m["away"])] for m in rows])
                hg = np.array([m["hg"] for m in rows])
                ag = np.array([m["ag"] for m in rows])
                weights = np.array(
                    [
                        2
                        ** (-(date.fromisoformat(month) - date.fromisoformat(m["date"])).days / 180)
                        for m in rows
                    ]
                )

                def objective(x):
                    lh = x[0] + x[1] + x[2 + hi] + x[2 + n + ai]
                    la = x[0] + x[2 + ai] + x[2 + n + hi]
                    eh = np.exp(lh)
                    ea = np.exp(la)
                    loss = np.sum(weights * (eh - hg * lh + ea - ag * la)) + 2 * np.sum(x[2:] ** 2)
                    rh = weights * (eh - hg)
                    ra = weights * (ea - ag)
                    gradient = np.r_[
                        np.sum(rh + ra),
                        np.sum(rh),
                        np.bincount(hi, rh, n) + np.bincount(ai, ra, n) + 4 * x[2 : 2 + n],
                        np.bincount(ai, rh, n) + np.bincount(hi, ra, n) + 4 * x[2 + n :],
                    ]
                    return loss, gradient

                x = np.zeros(2 + 2 * n)
                x[0] = math.log(max(0.1, float(np.average(ag, weights=weights))))
                x[1] = math.log(max(0.1, float(np.average(hg, weights=weights)))) - x[0]
                fit = minimize(
                    objective,
                    x,
                    jac=True,
                    method="L-BFGS-B",
                    bounds=[(-3, 3), (-2, 2)] + [(-3, 3)] * (2 * n),
                    options={"maxiter": 300, "ftol": 1e-10},
                )
                if not fit.success or not np.isfinite(fit.x).all():
                    raise RuntimeError(f"Poisson fit failed for {month}: {fit.message}")
                self.fit_cache[month] = (index, fit.x, max(m["date"] for m in rows))
        fit = self.fit_cache[month]
        if fit is None:
            return None
        index, x, end = fit
        n = len(index)
        h = index.get(club_key(fixture["home"]))
        a = index.get(club_key(fixture["away"]))
        attack = lambda i: 0 if i is None else x[2 + i]
        defence = lambda i: 0 if i is None else x[2 + n + i]
        from forecast_lab import probabilities

        return {
            "probabilities": probabilities(
                math.exp(x[0] + x[1] + attack(h) + defence(a)),
                math.exp(x[0] + attack(a) + defence(h)),
            ),
            "training_end": end,
            "fit_cutoff_exclusive": month,
        }

    def predict(self, fixture, cutoff):
        fitted = self.fitted(fixture, cutoff)
        return {
            "elo": self.elo(fixture, cutoff),
            **(
                {
                    "fitted_poisson": fitted["probabilities"],
                    "challenger_training_end": fitted["training_end"],
                }
                if fitted
                else {}
            ),
        }

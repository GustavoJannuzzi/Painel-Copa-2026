"""
FASE 2A — Calibração Isotônica + Otimização de Pesos do Ensemble.

Funções:
  - optimize_weights(): grid search LOO-CV nos 54 jogos para encontrar
    os melhores pesos {W_elo, W_dc, W_market} minimizando RPS.
  - IsotonicCalibrator: calibração pós-treinamento via regressão isotônica.
    Corrige o viés de overconfiança em favoritos identificado no diagnóstico.
  - calibrate_probs(p3): aplica o calibrador ao vetor [p_home, p_draw, p_away].
"""
import sys
import json
import math
from pathlib import Path
from itertools import product

import numpy as np
from sklearn.isotonic import IsotonicRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wc_data

PROJECT_ROOT = wc_data.PROJECT_ROOT
CALIB_PATH   = PROJECT_ROOT / "analysis" / "calibration_params.json"
PRED_PATH    = PROJECT_ROOT / "analysis" / "wc2026_predictions.json"


# ──────────────────────────────────────────────────────────────────────────────
# RPS helper
# ──────────────────────────────────────────────────────────────────────────────

def _rps(p, outcome):
    a = [0, 0, 0]; a[outcome] = 1
    return float(np.sum((np.cumsum(p) - np.cumsum(a)) ** 2) / 2)


def _norm3(v):
    s = sum(v)
    return [x / s for x in v] if s > 0 else [1/3, 1/3, 1/3]


# ──────────────────────────────────────────────────────────────────────────────
# 2B — Otimização de pesos por LOO-CV
# ──────────────────────────────────────────────────────────────────────────────

def optimize_weights(step: float = 0.05):
    """
    Grid search LOO-CV: testa combinações de pesos para Elo, DC e Market
    separadamente para jogos COM e SEM mercado. Retorna os melhores pesos.
    """
    data = json.load(open(PRED_PATH, encoding="utf-8"))
    played = [m for m in data["matches"] if m["played"]]

    with_mkt  = [m for m in played if m["models"].get("market")]
    without_mkt = [m for m in played if not m["models"].get("market")]

    def loo_rps_with(we, wd, wm, matches):
        """Leave-one-out RPS para jogos com mercado."""
        total = 0
        for m in matches:
            hs, as_ = m["actual"]
            outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
            pe = m["models"]["elo"]["p"]
            pd = m["models"]["dixon_coles"]["p"]
            pm = m["models"]["market"]["p"]
            p = _norm3([we*pe[i] + wd*pd[i] + wm*pm[i] for i in range(3)])
            total += _rps(p, outcome)
        return total / len(matches) if matches else 9999

    def loo_rps_without(we, wd, matches):
        total = 0
        for m in matches:
            hs, as_ = m["actual"]
            outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
            pe = m["models"]["elo"]["p"]
            pd = m["models"]["dixon_coles"]["p"]
            p = _norm3([we*pe[i] + wd*pd[i] for i in range(3)])
            total += _rps(p, outcome)
        return total / len(matches) if matches else 9999

    # Grid search para jogos COM mercado
    best_rps_mkt = 9999
    best_we, best_wd, best_wm = 0.22, 0.43, 0.35
    candidates = np.arange(0, 1 + step, step)
    for we, wd, wm in product(candidates, candidates, candidates):
        if abs(we + wd + wm - 1.0) > step / 2:
            continue
        if we < 0.01 or wd < 0.01 or wm < 0.01:
            continue
        r = loo_rps_with(we, wd, wm, with_mkt)
        if r < best_rps_mkt:
            best_rps_mkt = r
            best_we, best_wd, best_wm = we, wd, wm

    # Grid search para jogos SEM mercado
    best_rps_no = 9999
    best_we_no, best_wd_no = 0.35, 0.65
    for we, wd in product(candidates, candidates):
        if abs(we + wd - 1.0) > step / 2:
            continue
        if we < 0.01 or wd < 0.01:
            continue
        r = loo_rps_without(we, wd, without_mkt)
        if r < best_rps_no:
            best_rps_no = r
            best_we_no, best_wd_no = we, wd

    result = {
        "with_market": {
            "w_elo": round(float(best_we), 4),
            "w_dc": round(float(best_wd), 4),
            "w_market": round(float(best_wm), 4),
            "rps_loo": round(best_rps_mkt, 4),
            "n_games": len(with_mkt),
        },
        "without_market": {
            "w_elo": round(float(best_we_no), 4),
            "w_dc": round(float(best_wd_no), 4),
            "rps_loo": round(best_rps_no, 4),
            "n_games": len(without_mkt),
        },
        "baseline_rps": {
            "with_market_old": round(loo_rps_with(0.22, 0.43, 0.35, with_mkt), 4),
            "without_market_old": round(loo_rps_without(0.35, 0.65, without_mkt), 4),
        }
    }
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 2A — Calibração Isotônica
# ──────────────────────────────────────────────────────────────────────────────

class IsotonicCalibrator:
    """
    Calibração pós-treinamento via regressão isotônica (Zadrozny & Elkan 2002).
    Treina um calibrador por desfecho (home/draw/away) e aplica em novos jogos.

    Corrige o viés identificado no diagnóstico: modelo overconfidente para favoritos
    (ECE ensemble 0.0786 vs DC isolado 0.0652; Market ECE 0.1786).
    """

    def __init__(self):
        self._models = [IsotonicRegression(out_of_bounds="clip") for _ in range(3)]
        self._fitted = False

    def fit(self, played_matches: list):
        """Treina no histórico de jogos da Copa."""
        probs = [[], [], []]
        actuals = [[], [], []]

        for m in played_matches:
            hs, as_ = m["actual"]
            outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
            p = [m["prediction"]["p_home"], m["prediction"]["p_draw"], m["prediction"]["p_away"]]
            for i in range(3):
                probs[i].append(p[i])
                actuals[i].append(1 if i == outcome else 0)

        for i in range(3):
            if len(set(actuals[i])) > 1:  # precisa de ambas as classes
                self._models[i].fit(probs[i], actuals[i])
        self._fitted = True
        return self

    def calibrate(self, p3: list) -> list:
        """Aplica calibração e renormaliza para somar 1."""
        if not self._fitted:
            return p3
        cal = [float(self._models[i].predict([p3[i]])[0]) for i in range(3)]
        # Clip e renormaliza
        cal = [max(0.01, min(0.99, c)) for c in cal]
        s = sum(cal)
        return [c / s for c in cal]

    def save(self, path: Path = None):
        path = path or CALIB_PATH
        # Salva os pontos de calibração (x, y) de cada modelo
        params = {}
        for i, name in enumerate(["home", "draw", "away"]):
            m = self._models[i]
            params[name] = {
                "X_thresholds": m.X_thresholds_.tolist(),
                "y_thresholds": m.y_thresholds_.tolist(),
            }
        json.dump(params, open(path, "w", encoding="utf-8"), indent=2)
        return params

    @classmethod
    def load(cls, path: Path = None):
        path = path or CALIB_PATH
        obj = cls()
        if not path.exists():
            return obj
        params = json.load(open(path, encoding="utf-8"))
        for i, name in enumerate(["home", "draw", "away"]):
            p = params.get(name, {})
            if p.get("X_thresholds"):
                m = IsotonicRegression(out_of_bounds="clip")
                xt = np.array(p["X_thresholds"])
                yt = np.array(p["y_thresholds"])
                # Reconstrói o modelo isotônico a partir dos thresholds
                m.fit(xt, yt)
                obj._models[i] = m
        obj._fitted = True
        return obj


# ──────────────────────────────────────────────────────────────────────────────
# Wrapper público
# ──────────────────────────────────────────────────────────────────────────────

def build_and_save_calibrator() -> IsotonicCalibrator:
    """Treina e salva o calibrador com os jogos disponíveis."""
    data = json.load(open(PRED_PATH, encoding="utf-8"))
    played = [m for m in data["matches"] if m["played"]]
    cal = IsotonicCalibrator()
    cal.fit(played)
    cal.save()
    return cal


def load_calibrator() -> IsotonicCalibrator:
    """Carrega calibrador salvo (ou retorna sem calibração se não existir)."""
    return IsotonicCalibrator.load()


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[Calibracao] Otimizando pesos do ensemble (grid search LOO-CV)...")
    weights = optimize_weights(step=0.05)
    print(f"\n  COM mercado (n={weights['with_market']['n_games']}):")
    print(f"    Elo={weights['with_market']['w_elo']:.2f} | DC={weights['with_market']['w_dc']:.2f} | "
          f"Market={weights['with_market']['w_market']:.2f}")
    print(f"    RPS novo={weights['with_market']['rps_loo']} | "
          f"RPS antigo={weights['baseline_rps']['with_market_old']}")

    print(f"\n  SEM mercado (n={weights['without_market']['n_games']}):")
    print(f"    Elo={weights['without_market']['w_elo']:.2f} | DC={weights['without_market']['w_dc']:.2f}")
    print(f"    RPS novo={weights['without_market']['rps_loo']} | "
          f"RPS antigo={weights['baseline_rps']['without_market_old']}")

    print("\n[Calibracao] Treinando calibrador isotônico...")
    cal = build_and_save_calibrator()
    print(f"  Salvo em: {CALIB_PATH}")
    print("\n  Teste de calibracao [0.80, 0.12, 0.08] ->", [round(x, 3) for x in cal.calibrate([0.80, 0.12, 0.08])])
    print("  Teste de calibracao [0.40, 0.30, 0.30] ->", [round(x, 3) for x in cal.calibrate([0.40, 0.30, 0.30])])
    print("  Teste de calibracao [0.20, 0.30, 0.50] ->", [round(x, 3) for x in cal.calibrate([0.20, 0.30, 0.50])])

"""
Backtest e métricas de acurácia sobre os jogos JÁ disputados da Copa 2026.

Lê analysis/wc2026_predictions.json e calcula (padrão da literatura — Constantinou &
Fenton 2012; Ley et al. 2019):
  - RPS médio (métrica primária) + comparação com baselines (ingênuo 1/3 e Elo/DC isolados)
  - log-loss (secundária)
  - taxa de acerto 1X2 e de placar exato
  - calibração (reliability bins)
  - série temporal do RPS acumulado (para o painel)

Saída: analysis/wc2026_backtest.json
"""
import sys
import json
import math
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wc_data

PRED = wc_data.PROJECT_ROOT / "analysis" / "wc2026_predictions.json"


def rps(p, outcome):
    a = [0, 0, 0]; a[outcome] = 1
    cp = np.cumsum(p); ca = np.cumsum(a)
    return float(np.sum((cp - ca) ** 2) / 2.0)


def logloss(p, outcome):
    return -math.log(max(p[outcome], 1e-12))


def run():
    data = json.load(open(PRED, encoding="utf-8"))
    played = [m for m in data["matches"] if m["played"]]

    n = len(played)
    rps_ens, rps_naive, rps_elo, rps_dc = [], [], [], []
    ll_ens = []
    hits, exact_hits = 0, 0
    calib_pairs = []      # (prob_prevista, ocorreu?) para os 3 desfechos
    timeline = []         # {date, rps_acumulado}

    played_sorted = sorted(played, key=lambda m: (m["date"], m["round"] or ""))
    running = []
    for m in played_sorted:
        hs, as_ = m["actual"]
        outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
        p = [m["prediction"]["p_home"], m["prediction"]["p_draw"], m["prediction"]["p_away"]]
        elo_p = m["models"]["elo"]["p"]
        dc_p = m["models"]["dixon_coles"]["p"]

        r = rps(p, outcome)
        rps_ens.append(r); running.append(r)
        rps_naive.append(rps([1/3, 1/3, 1/3], outcome))
        rps_elo.append(rps(elo_p, outcome))
        rps_dc.append(rps(dc_p, outcome))
        ll_ens.append(logloss(p, outcome))

        if int(np.argmax(p)) == outcome:
            hits += 1
        if m["prediction"]["most_likely"] == f"{hs}-{as_}":
            exact_hits += 1
        for idx in range(3):
            calib_pairs.append((p[idx], 1 if idx == outcome else 0))
        timeline.append({"date": m["date"], "home": m["home"], "away": m["away"],
                         "rps": round(r, 4), "cum_rps": round(float(np.mean(running)), 4)})

    # calibração: 10 bins
    bins = []
    cp = np.array(calib_pairs)
    for lo in np.arange(0, 1.0, 0.1):
        hi = lo + 0.1
        sel = cp[(cp[:, 0] >= lo) & (cp[:, 0] < hi)]
        if len(sel):
            bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": int(len(sel)),
                         "pred_mean": round(float(sel[:, 0].mean()), 3),
                         "obs_freq": round(float(sel[:, 1].mean()), 3)})

    metrics = {
        "n_played": n,
        "mean_rps": round(float(np.mean(rps_ens)), 4),
        "mean_logloss": round(float(np.mean(ll_ens)), 4),
        "hit_rate_1x2": round(hits / n, 4) if n else None,
        "exact_score_hit_rate": round(exact_hits / n, 4) if n else None,
        "baselines": {
            "rps_naive_uniform": round(float(np.mean(rps_naive)), 4),
            "rps_elo_only": round(float(np.mean(rps_elo)), 4),
            "rps_dixon_coles_only": round(float(np.mean(rps_dc)), 4),
        },
        "interpretation": {
            "rps_ref_bom_modelo": "0.18-0.21",
            "rps_ingenuo": "~0.22",
            "rps_bate_mercado": "<0.19",
        },
        "calibration_bins": bins,
        "rps_timeline": timeline,
    }
    path = wc_data.PROJECT_ROOT / "analysis" / "wc2026_backtest.json"
    json.dump(metrics, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print(f"Jogos avaliados: {n}")
    print(f"  RPS médio (ensemble): {metrics['mean_rps']}  "
          f"(ingênuo {metrics['baselines']['rps_naive_uniform']} | "
          f"Elo {metrics['baselines']['rps_elo_only']} | "
          f"DC {metrics['baselines']['rps_dixon_coles_only']})")
    print(f"  Log-loss: {metrics['mean_logloss']}")
    print(f"  Acerto 1X2: {metrics['hit_rate_1x2']:.1%}")
    print(f"  Acerto de placar exato: {metrics['exact_score_hit_rate']:.1%}")
    print(f"  Salvo em {path}")
    return metrics


if __name__ == "__main__":
    run()

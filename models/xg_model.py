"""
Modelo baseado em Expected Goals (xG)
Ref: Rathke (2017), Spearman et al. (2018), Mead et al. (2023 - PLOS ONE)

O xG é consistentemente a variável mais importante na literatura recente.
Substitui gols reais como input dos modelos Poisson — mais estável e preditivo.
"""

import numpy as np
from scipy.stats import poisson
from typing import Dict, List, Tuple
import json


# --- Dados de xG da Copa 2026 ---
# Fontes: xGscore.io, Sofascore, analistas de apostas

XG_DATA = {
    "brasil": {
        "vs_marrocos": {
            "xG_scored": 1.35,   # xG gerado pelo Brasil vs Marrocos
            "xG_conceded": 0.78, # xG gerado por Marrocos vs Brasil
            "result": "1-1",
            "actual_goals": 1,
            "actual_conceded": 1,
        },
        # Estimativas de xG em qualificatórias (aproximadas por desempenho)
        "recent_xG_scored": [1.8, 2.1, 1.5, 2.4, 1.9, 1.2, 2.8, 0.9, 3.1, 1.6],
        "recent_xG_conceded": [0.6, 0.4, 0.8, 0.3, 0.5, 0.9, 0.4, 1.1, 0.7, 0.5],
    },
    "haiti": {
        "vs_escocia": {
            "xG_scored": 1.05,   # Haiti criou mais do que placar sugere
            "xG_conceded": 0.80,
            "result": "0-1",
            "actual_goals": 0,
            "actual_conceded": 1,
        },
        "recent_xG_scored": [0.6, 0.4, 0.8, 0.3, 0.7, 0.5, 0.4, 0.9, 0.5, 0.6],
        "recent_xG_conceded": [1.4, 2.1, 1.0, 1.6, 0.9, 1.8, 1.3, 2.0, 1.2, 1.5],
    }
}

# Mercado de apostas: xG esperado para Brasil × Haiti (agregado por sportsbooks)
MARKET_XG_ESTIMATE = {
    "brasil": 2.31,
    "haiti":  0.28,
}


def time_weighted_avg(values: List[float], decay: float = 0.85) -> float:
    """Média ponderada por recência (jogos mais recentes têm mais peso)."""
    n = len(values)
    weights = [decay ** (n - i - 1) for i in range(n)]
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)


def luck_adjustment(
    xG: float,
    actual_goals: float,
    weight_xg: float = 0.7,
) -> float:
    """
    Ajuste de 'sorte': combina xG e gols reais, dando mais peso ao xG.

    Ref: Mead et al. (PLOS ONE 2023) — xG predictions with 70% weight outperform pure goals.
    """
    return weight_xg * xG + (1 - weight_xg) * actual_goals


def defensive_adjustment(
    opponent_avg_xG_conceded: float,
    global_avg_xG: float = 1.2,
) -> float:
    """Fator de ajuste pela qualidade defensiva do adversário."""
    return opponent_avg_xG_conceded / global_avg_xG


def score_matrix(lam: float, mu: float, max_goals: int = 8) -> np.ndarray:
    """Matriz de probabilidades de placar via Poisson independente."""
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            matrix[x][y] = poisson.pmf(x, lam) * poisson.pmf(y, mu)
    matrix /= matrix.sum()
    return matrix


def run_model(data: Dict = None) -> Dict:
    """Executa o modelo xG completo."""

    if data is None:
        data = XG_DATA

    # --- Brasil ---
    # xG recente ponderado por recência
    br_xG_hist = data["brasil"]["recent_xG_scored"] + [data["brasil"]["vs_marrocos"]["xG_scored"]]
    br_xGC_hist = data["brasil"]["recent_xG_conceded"] + [data["brasil"]["vs_marrocos"]["xG_conceded"]]
    br_xG_weights = [0.85 ** (len(br_xG_hist) - i - 1) for i in range(len(br_xG_hist))]

    # Dar mais peso ao jogo da Copa
    br_xG_weights[-1] *= 2.0
    br_xGC_weights = br_xG_weights.copy()

    br_xG_avg  = sum(v * w for v, w in zip(br_xG_hist, br_xG_weights)) / sum(br_xG_weights)
    br_xGC_avg = sum(v * w for v, w in zip(br_xGC_hist, br_xGC_weights)) / sum(br_xGC_weights)

    # --- Haiti ---
    ht_xG_hist  = data["haiti"]["recent_xG_scored"] + [data["haiti"]["vs_escocia"]["xG_scored"]]
    ht_xGC_hist = data["haiti"]["recent_xG_conceded"] + [data["haiti"]["vs_escocia"]["xG_conceded"]]
    ht_xG_weights = [0.85 ** (len(ht_xG_hist) - i - 1) for i in range(len(ht_xG_hist))]
    ht_xG_weights[-1] *= 2.0
    ht_xGC_weights = ht_xG_weights.copy()

    ht_xG_avg  = sum(v * w for v, w in zip(ht_xG_hist, ht_xG_weights)) / sum(ht_xG_weights)
    ht_xGC_avg = sum(v * w for v, w in zip(ht_xGC_hist, ht_xGC_weights)) / sum(ht_xGC_weights)

    # --- Taxa esperada de gols (Brasil ataca vs. Defesa do Haiti) ---
    # Brasil xG esperado = Brasil xG médio × (Haiti xG concedido / média global)
    global_avg = 1.2

    lam = br_xG_avg * (ht_xGC_avg / global_avg)  # Brasil marca
    mu  = ht_xG_avg * (br_xGC_avg / global_avg)  # Haiti marca

    # Ajuste de sorte: primeira rodada foi outlier para o Haiti (1.05 xG, 0 gols)
    # Isso sugere que o Haiti é melhor do que o placar indica, mas ainda muito inferior ao Brasil
    haiti_luck_adjustment = (ht_xG_hist[-1] - data["haiti"]["vs_escocia"]["actual_goals"]) / 10
    lam = max(0.3, lam)
    mu  = max(0.1, mu + haiti_luck_adjustment * 0.3)

    # Suavização com estimativa do mercado (peso 20% para mercado)
    lam_final = 0.80 * lam + 0.20 * MARKET_XG_ESTIMATE["brasil"]
    mu_final  = 0.80 * mu  + 0.20 * MARKET_XG_ESTIMATE["haiti"]

    # Gerar distribuição de placar
    matrix = score_matrix(lam_final, mu_final)

    # Probabilidades 1X2
    n = matrix.shape[0]
    p_home_win = sum(matrix[i][j] for i in range(n) for j in range(n) if i > j)
    p_draw     = sum(matrix[i][i] for i in range(n))
    p_away_win = sum(matrix[i][j] for i in range(n) for j in range(n) if j > i)

    # Top placares
    top_scores = sorted(
        [{"score": f"{i}-{j}", "prob": round(float(matrix[i][j]), 4)} for i in range(n) for j in range(n)],
        key=lambda s: s["prob"], reverse=True
    )[:8]

    return {
        "model": "Expected Goals (xG-based Poisson)",
        "home_team": "Brasil",
        "away_team": "Haiti",
        "xG_averages": {
            "brasil_attack_xG": round(br_xG_avg, 2),
            "haiti_defense_xGC": round(ht_xGC_avg, 2),
            "haiti_attack_xG":  round(ht_xG_avg, 2),
            "brasil_defense_xGC": round(br_xGC_avg, 2),
        },
        "expected_goals": {
            "brasil": round(lam_final, 2),
            "haiti":  round(mu_final, 2),
        },
        "probabilities": {
            "home_win": round(p_home_win, 4),
            "draw":     round(p_draw, 4),
            "away_win": round(p_away_win, 4),
        },
        "top_scores": top_scores,
        "note": "xG Copa ponderado por recência + ajuste por defesa + suavização com mercado (20%)",
    }


if __name__ == "__main__":
    result = run_model()
    print(json.dumps(result, indent=2, ensure_ascii=False))

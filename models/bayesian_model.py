"""
Modelo Bayesiano Hierárquico para Predição de Gols
Ref: Baio & Blangiardo (2010), Rue & Salvesen (2000)

Versão analítica (sem MCMC) usando aproximação normal para priors conjugados.
"""

import numpy as np
from scipy.stats import poisson, norm
from typing import Dict, List, Tuple
import json


def gamma_poisson_posterior(
    prior_alpha: float,
    prior_beta: float,
    observed_goals: List[int],
    time_weights: List[float] = None,
) -> Tuple[float, float]:
    """
    Atualiza prior Gamma com observações Poisson (conjugado).

    Prior: λ ~ Gamma(α, β)
    Likelihood: Y_i ~ Poisson(λ)
    Posterior: λ | data ~ Gamma(α + Σy_i, β + n)

    Returns: (posterior_mean, posterior_variance)
    """
    if time_weights is None:
        time_weights = [1.0] * len(observed_goals)

    # Ponderação por recência (Dixon-Coles time-weighting)
    weighted_goals = sum(g * w for g, w in zip(observed_goals, time_weights))
    effective_n = sum(time_weights)

    alpha_post = prior_alpha + weighted_goals
    beta_post  = prior_beta  + effective_n

    posterior_mean     = alpha_post / beta_post
    posterior_variance = alpha_post / (beta_post ** 2)

    return posterior_mean, posterior_variance


def strength_adjusted_rate(
    team_attack_mean: float,
    opponent_defense_mean: float,
    global_avg: float = 1.2,
) -> float:
    """
    Taxa esperada ajustada pela força relativa de ataque vs. defesa do adversário.

    Dixon-Coles notation: λ_ij = μ × α_i × β_j
    α_i = team_attack / global_avg   (>1 = strong attack)
    β_j = opponent_defense / global_avg  (<1 = strong defense = fewer goals conceded)
    """
    alpha = team_attack_mean / global_avg
    beta  = opponent_defense_mean / global_avg
    return alpha * beta * global_avg


def score_probabilities(
    lam: float,
    mu: float,
    lam_var: float = 0.1,
    mu_var: float = 0.1,
    max_goals: int = 8,
) -> np.ndarray:
    """
    Gera distribuição de placar com incerteza nos parâmetros (variância posterior).
    Integra sobre λ e μ via Monte Carlo (1000 amostras da posterior).
    """
    rng = np.random.default_rng(42)
    n_samples = 2000
    matrix = np.zeros((max_goals + 1, max_goals + 1))

    for _ in range(n_samples):
        lam_s = max(0.01, rng.normal(lam, np.sqrt(lam_var)))
        mu_s  = max(0.01, rng.normal(mu,  np.sqrt(mu_var)))

        for x in range(max_goals + 1):
            for y in range(max_goals + 1):
                matrix[x][y] += poisson.pmf(x, lam_s) * poisson.pmf(y, mu_s)

    matrix /= n_samples
    matrix /= matrix.sum()
    return matrix


def credible_interval(mean: float, variance: float, level: float = 0.80) -> Tuple[float, float]:
    """Intervalo de credibilidade para λ da posterior Gamma."""
    std = np.sqrt(variance)
    z = norm.ppf((1 + level) / 2)
    return (max(0, mean - z * std), mean + z * std)


# Dados observados para o framework
# Gols marcados por jogo (ponderados por importância: Copa > Eliminatórias > Amistoso)
BRAZIL_OBSERVED_ATTACK = {
    "wc2026": [1],          # vs Marrocos
    "qualifiers_2025": [4, 1, 2, 2, 3, 1, 4, 0, 5, 2],  # Últimas 10 partidas
    "weights_wc": [1.5],
    "weights_qual": [1.2, 1.2, 1.2, 1.2, 1.2, 1.0, 1.0, 1.0, 1.0, 0.8],
}

BRAZIL_OBSERVED_DEFENSE = {
    "wc2026": [1],
    "qualifiers_2025": [0, 0, 1, 0, 1, 1, 0, 1, 0, 0],
    "weights_wc": [1.5],
    "weights_qual": [1.2, 1.2, 1.2, 1.2, 1.2, 1.0, 1.0, 1.0, 1.0, 0.8],
}

HAITI_OBSERVED_ATTACK = {
    "wc2026": [0],          # vs Escócia
    "qualifiers_2025": [1, 0, 2, 0, 1, 0, 0, 1, 0, 2],
    "weights_wc": [1.5],
    "weights_qual": [1.2, 1.2, 1.0, 1.0, 1.0, 0.8, 0.8, 0.8, 0.6, 0.6],
}

HAITI_OBSERVED_DEFENSE = {
    "wc2026": [1],
    "qualifiers_2025": [2, 3, 1, 2, 0, 2, 1, 3, 1, 2],
    "weights_wc": [1.5],
    "weights_qual": [1.2, 1.2, 1.0, 1.0, 1.0, 0.8, 0.8, 0.8, 0.6, 0.6],
}


def run_model(
    brazil_data: Dict = None,
    haiti_data: Dict = None,
) -> Dict:
    """Executa o modelo Bayesiano hierárquico."""

    if brazil_data is None:
        brazil_data = {
            "attack": BRAZIL_OBSERVED_ATTACK,
            "defense": BRAZIL_OBSERVED_DEFENSE,
        }
    if haiti_data is None:
        haiti_data = {
            "attack": HAITI_OBSERVED_ATTACK,
            "defense": HAITI_OBSERVED_DEFENSE,
        }

    # Prior não-informativo moderado: Gamma(2, 1.5) → mean=1.33, var=0.89
    PRIOR_ALPHA = 2.0
    PRIOR_BETA  = 1.5

    # --- Brasil Ataque ---
    br_att_goals  = brazil_data["attack"]["wc2026"] + brazil_data["attack"]["qualifiers_2025"]
    br_att_weights = brazil_data["attack"]["weights_wc"] + brazil_data["attack"]["weights_qual"]
    br_att_mean, br_att_var = gamma_poisson_posterior(PRIOR_ALPHA, PRIOR_BETA, br_att_goals, br_att_weights)

    # --- Brasil Defesa (gols sofridos → menor é melhor) ---
    br_def_goals  = brazil_data["defense"]["wc2026"] + brazil_data["defense"]["qualifiers_2025"]
    br_def_weights = brazil_data["defense"]["weights_wc"] + brazil_data["defense"]["weights_qual"]
    br_def_mean, br_def_var = gamma_poisson_posterior(PRIOR_ALPHA, PRIOR_BETA, br_def_goals, br_def_weights)

    # --- Haiti Ataque ---
    ht_att_goals  = haiti_data["attack"]["wc2026"] + haiti_data["attack"]["qualifiers_2025"]
    ht_att_weights = haiti_data["attack"]["weights_wc"] + haiti_data["attack"]["weights_qual"]
    ht_att_mean, ht_att_var = gamma_poisson_posterior(PRIOR_ALPHA, PRIOR_BETA, ht_att_goals, ht_att_weights)

    # --- Haiti Defesa ---
    ht_def_goals  = haiti_data["defense"]["wc2026"] + haiti_data["defense"]["qualifiers_2025"]
    ht_def_weights = haiti_data["defense"]["weights_wc"] + haiti_data["defense"]["weights_qual"]
    ht_def_mean, ht_def_var = gamma_poisson_posterior(PRIOR_ALPHA, PRIOR_BETA, ht_def_goals, ht_def_weights)

    # Taxa ajustada de gols esperados
    lam = strength_adjusted_rate(br_att_mean, ht_def_mean)  # Brasil marca
    mu  = strength_adjusted_rate(ht_att_mean, br_def_mean)  # Haiti marca

    lam_var = br_att_var + ht_def_var
    mu_var  = ht_att_var + br_def_var

    # Distribuição de placar com incerteza nos parâmetros
    matrix = score_probabilities(lam, mu, lam_var, mu_var)

    # Probabilidades 1X2
    n = matrix.shape[0]
    p_home_win = sum(matrix[i][j] for i in range(n) for j in range(n) if i > j)
    p_draw     = sum(matrix[i][i] for i in range(n))
    p_away_win = sum(matrix[i][j] for i in range(n) for j in range(n) if j > i)

    # Top placares
    scores = [
        {"score": f"{i}-{j}", "prob": round(float(matrix[i][j]), 4)}
        for i in range(n) for j in range(n)
    ]
    top_scores = sorted(scores, key=lambda s: s["prob"], reverse=True)[:8]

    # Intervalos de credibilidade 80%
    ci_brazil = credible_interval(lam, lam_var, 0.80)
    ci_haiti  = credible_interval(mu,  mu_var,  0.80)

    return {
        "model": "Bayesiano Hierárquico (Baio & Blangiardo)",
        "home_team": "Brasil",
        "away_team": "Haiti",
        "posterior_attack": {
            "brasil": {"mean": round(br_att_mean, 3), "variance": round(br_att_var, 4)},
            "haiti":  {"mean": round(ht_att_mean, 3), "variance": round(ht_att_var, 4)},
        },
        "posterior_defense": {
            "brasil": {"mean": round(br_def_mean, 3), "variance": round(br_def_var, 4)},
            "haiti":  {"mean": round(ht_def_mean, 3), "variance": round(ht_def_var, 4)},
        },
        "expected_goals": {
            "brasil": round(lam, 2),
            "haiti":  round(mu,  2),
        },
        "credible_intervals_80pct": {
            "brasil_goals": [round(ci_brazil[0], 2), round(ci_brazil[1], 2)],
            "haiti_goals":  [round(ci_haiti[0], 2),  round(ci_haiti[1], 2)],
        },
        "probabilities": {
            "home_win": round(p_home_win, 4),
            "draw":     round(p_draw, 4),
            "away_win": round(p_away_win, 4),
        },
        "top_scores": top_scores,
    }


if __name__ == "__main__":
    result = run_model()
    print(json.dumps(result, indent=2, ensure_ascii=False))

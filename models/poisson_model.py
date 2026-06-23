"""
Dixon-Coles Poisson Bivariado
Ref: Dixon & Coles (1997) - Modelling Association Football Scores and Inefficiencies in the Football Betting Market
"""

import numpy as np
from scipy.stats import poisson
from scipy.optimize import minimize
from typing import Dict, Tuple, List
import json


def tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    """Fator de correção Dixon-Coles para placares baixos (0-0, 1-0, 0-1, 1-1)."""
    if x == 0 and y == 0:
        return 1 - lam * mu * rho
    elif x == 0 and y == 1:
        return 1 + lam * rho
    elif x == 1 and y == 0:
        return 1 + mu * rho
    elif x == 1 and y == 1:
        return 1 - rho
    return 1.0


def dixon_coles_prob(x: int, y: int, lam: float, mu: float, rho: float = -0.1) -> float:
    """P(X=x, Y=y) pelo modelo Dixon-Coles."""
    return (
        tau(x, y, lam, mu, rho)
        * poisson.pmf(x, lam)
        * poisson.pmf(y, mu)
    )


def score_matrix(lam: float, mu: float, rho: float = -0.1, max_goals: int = 8) -> np.ndarray:
    """Matriz de probabilidades para todos os placares até max_goals × max_goals."""
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            matrix[x][y] = dixon_coles_prob(x, y, lam, mu, rho)
    # Normalizar para somar 1
    matrix /= matrix.sum()
    return matrix


def match_probabilities(matrix: np.ndarray) -> Dict[str, float]:
    """Calcula P(home win), P(draw), P(away win) a partir da matriz."""
    n = matrix.shape[0]
    home_win = np.sum([matrix[i][j] for i in range(n) for j in range(n) if i > j])
    draw      = np.sum([matrix[i][i] for i in range(n)])
    away_win  = np.sum([matrix[i][j] for i in range(n) for j in range(n) if j > i])
    return {"home_win": home_win, "draw": draw, "away_win": away_win}


def top_scores(matrix: np.ndarray, top_n: int = 10) -> List[Dict]:
    """Retorna os placares mais prováveis com suas probabilidades."""
    scores = []
    n = matrix.shape[0]
    for x in range(n):
        for y in range(n):
            scores.append({"home": x, "away": y, "prob": matrix[x][y]})
    return sorted(scores, key=lambda s: s["prob"], reverse=True)[:top_n]


def apply_contextual_factors(lam: float, mu: float, factors: Dict) -> Tuple[float, float]:
    """Aplica modificadores contextuais às taxas de gol."""
    lam_adj = lam
    mu_adj  = mu

    # Jogador chave ausente
    if factors.get("home_key_player_out"):
        lam_adj *= 0.88  # -12% ataque

    if factors.get("away_key_player_out"):
        mu_adj *= 0.88

    # Forma recente (0.9 = má forma, 1.1 = boa forma)
    lam_adj *= factors.get("home_form_factor", 1.0)
    mu_adj  *= factors.get("away_form_factor", 1.0)

    # Fadiga (dias de descanso)
    home_rest = factors.get("home_rest_days", 4)
    away_rest = factors.get("away_rest_days", 4)
    if home_rest < 3:
        lam_adj *= 0.95
    if away_rest < 3:
        mu_adj  *= 0.95

    return lam_adj, mu_adj


def run_model(
    home_attack: float,
    away_attack: float,
    home_defense: float,
    away_defense: float,
    rho: float = -0.1,
    contextual_factors: Dict = None,
    team_home: str = "Brasil",
    team_away: str = "Adversário",
) -> Dict:
    """
    Executa o modelo Dixon-Coles completo.

    Args:
        home_attack:  Taxa média de gols marcados pelo time da casa
        away_attack:  Taxa média de gols marcados pelo visitante
        home_defense: Taxa média de gols sofridos pelo time da casa
        away_defense: Taxa média de gols sofridos pelo visitante
        rho:          Parâmetro de correlação Dixon-Coles (tipicamente -0.1 a 0.0)
        contextual_factors: Dict com modificadores contextuais
    """
    if contextual_factors is None:
        contextual_factors = {}

    # Lambda e mu baseados em força relativa
    lam = home_attack * (1 / home_defense) if home_defense > 0 else home_attack
    mu  = away_attack * (1 / away_defense) if away_defense > 0 else away_attack

    # Normalizar para médias razoáveis (Copa do Mundo ~1.2 gols/time/jogo)
    world_cup_avg = 1.2
    lam = lam * world_cup_avg
    mu  = mu  * world_cup_avg

    # Aplicar fatores contextuais
    lam, mu = apply_contextual_factors(lam, mu, contextual_factors)

    # Calcular matriz e probabilidades
    matrix = score_matrix(lam, mu, rho)
    probs  = match_probabilities(matrix)
    top    = top_scores(matrix)

    # Placar mais provável
    best = top[0]

    return {
        "model": "Dixon-Coles Poisson",
        "home_team": team_home,
        "away_team": team_away,
        "expected_goals": {"home": round(lam, 2), "away": round(mu, 2)},
        "most_likely_score": f"{best['home']}-{best['away']} ({best['prob']:.1%})",
        "probabilities": {k: round(v, 4) for k, v in probs.items()},
        "top_scores": [
            {"score": f"{s['home']}-{s['away']}", "probability": round(s["prob"], 4)}
            for s in top[:8]
        ],
        "rho": rho,
    }


if __name__ == "__main__":
    # Exemplo de execução — substitua pelos dados reais
    result = run_model(
        home_attack=1.8,   # Gols marcados por jogo (Brasil na Copa 2026)
        away_attack=1.1,   # Gols marcados por jogo (Adversário)
        home_defense=0.9,  # Gols sofridos por jogo (Brasil)
        away_defense=1.4,  # Gols sofridos por jogo (Adversário)
        rho=-0.1,
        contextual_factors={
            "home_form_factor": 1.05,
            "away_form_factor": 0.95,
            "home_rest_days": 4,
            "away_rest_days": 3,
        },
        team_home="Brasil",
        team_away="TBD",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

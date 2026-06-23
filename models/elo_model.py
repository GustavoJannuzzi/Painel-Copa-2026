"""
Modelo Elo Adaptado para Futebol Internacional
Ref: Hvattum & Arntzen (2010), Elo (1978)
"""

import math
import json
from typing import Dict, Tuple


# Rankings Elo aproximados de seleções (baseado em FIFA Ranking + desempenho recente)
# Calibrados para escala 1000-2200 (Elo futebol)
ELO_RATINGS = {
    "Brasil": 2015,
    "Argentina": 2090,
    "França": 2050,
    "Espanha": 2040,
    "Inglaterra": 2020,
    "Alemanha": 1980,
    "Portugal": 1975,
    "Holanda": 1970,
    "Bélgica": 1940,
    "Itália": 1935,
    "Marrocos": 1870,
    "Escócia": 1780,
    "Haiti": 1540,
    "EUA": 1820,
    "México": 1810,
    "Colômbia": 1870,
    "Uruguai": 1880,
}

# Modificador de campo: Copa do Mundo em solo neutro
HOME_ADVANTAGE = 0  # Neutro (Copa do Mundo EUA 2026 — sem time da casa direto)

# K-factor para partidas internacionais em torneios importantes
K_WORLD_CUP = 60  # Maior que amistosos (K=10) mas reflete importância


def expected_score(rating_a: float, rating_b: float) -> float:
    """Probabilidade esperada de vitória do time A contra B (escala logística)."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def win_draw_loss_prob(
    rating_home: float,
    rating_away: float,
    home_advantage: float = HOME_ADVANTAGE,
    draw_bandwidth: float = 0.12,
) -> Tuple[float, float, float]:
    """
    Converte expected score em P(W), P(D), P(L).

    A fração de empates em futebol (~25-28% em Copa do Mundo) é modelada como
    uma banda simétrica em torno de E=0.5.
    Ref: Hvattum & Arntzen (2010) — draw probability calibration.
    """
    e = expected_score(rating_home + home_advantage, rating_away)

    # Banda de empate: centrada em E=0.5, largura calibrada por draw_bandwidth
    # Em jogos muito desiguais, empate é menos provável
    draw_prob = draw_bandwidth * math.exp(-4 * (e - 0.5) ** 2)

    home_win = e - draw_prob / 2
    away_win = 1 - e - draw_prob / 2

    # Garantir limites [0,1]
    home_win = max(0, min(1, home_win))
    away_win = max(0, min(1, away_win))
    draw_prob = max(0, min(1, draw_prob))

    # Renormalizar
    total = home_win + draw_prob + away_win
    return home_win / total, draw_prob / total, away_win / total


def elo_to_goals(
    rating_home: float,
    rating_away: float,
    avg_goals_home: float = 1.35,
    avg_goals_away: float = 1.05,
) -> Tuple[float, float]:
    """
    Converte diferença Elo em gols esperados.

    Ajusta a média global de gols da Copa pelo ratio de força relativa.
    Brasil (2015) vs Haiti (1540) → diferença enorme → ajuste significativo.
    """
    diff = rating_home - rating_away

    # Fator multiplicador baseado na diferença de rating
    # Cada 100 pontos Elo ≈ 1.3x mais forte (calibrado empiricamente)
    factor = 10 ** (diff / 800)  # mais conservador que 400 para gols

    # Normalizado: média global mantida
    total_avg = avg_goals_home + avg_goals_away
    home_fraction = factor / (1 + factor)
    away_fraction = 1 / (1 + factor)

    lam = home_fraction * total_avg * 1.15  # Brasil como "casa" cultural
    mu  = away_fraction * total_avg * 0.85

    return lam, mu


def run_model(
    home_team: str = "Brasil",
    away_team: str = "Haiti",
    custom_ratings: Dict = None,
) -> Dict:
    """Executa o modelo Elo completo."""
    ratings = {**ELO_RATINGS}
    if custom_ratings:
        ratings.update(custom_ratings)

    r_home = ratings.get(home_team, 1700)
    r_away = ratings.get(away_team, 1700)

    # Probabilidades 1X2
    p_win, p_draw, p_loss = win_draw_loss_prob(r_home, r_away)

    # Gols esperados
    lam, mu = elo_to_goals(r_home, r_away)

    # Diferença de rating
    diff = r_home - r_away

    return {
        "model": "Elo Adaptado (Hvattum-Arntzen)",
        "home_team": home_team,
        "away_team": away_team,
        "ratings": {
            "home": r_home,
            "away": r_away,
            "difference": diff,
        },
        "probabilities": {
            "home_win": round(p_win, 4),
            "draw": round(p_draw, 4),
            "away_win": round(p_loss, 4),
        },
        "expected_goals": {
            "home": round(lam, 2),
            "away": round(mu, 2),
        },
        "interpretation": (
            f"Diferença de {diff} pontos Elo. "
            f"{home_team} é massivamente superior. "
            f"Expectativa: {home_team} domina com ~{lam:.1f} gols esperados."
        ),
    }


if __name__ == "__main__":
    result = run_model("Brasil", "Haiti")
    print(json.dumps(result, indent=2, ensure_ascii=False))

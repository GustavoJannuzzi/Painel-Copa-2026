"""
Motor de ratings Elo de seleções (estilo World Football Elo) + calibração Elo->gols.

- Percorre TODA a história (Kaggle) cronologicamente, exceto a Copa 2026.
- K-factor por importância da competição; multiplicador por saldo de gols; mando de campo.
- Calibra empiricamente o mapeamento (diferença de Elo) -> (gols esperados de cada time)
  por mínimos quadrados nos jogos recentes.
- Depois aplica os resultados REAIS da Copa 2026 (openfootball) em ordem, guardando o
  rating PRÉ-JOGO de cada partida (para previsão sem vazamento) e o rating atual.
"""
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wc_data

INIT_RATING = 1500.0
HOME_ADV = 65.0  # vantagem de mando (não aplicada em campo neutro)

# K-factor por tipo de competição (World Football Elo)
K_BY_COMP = {
    "FIFA World Cup": 60, "Confederations Cup": 50,
    "Copa América": 50, "UEFA Euro": 50, "African Cup of Nations": 50,
    "AFC Asian Cup": 50, "Gold Cup": 45,
    "FIFA World Cup qualification": 40, "UEFA Euro qualification": 35,
    "African Cup of Nations qualification": 35, "AFC Asian Cup qualification": 30,
    "Copa América qualification": 35,
    "UEFA Nations League": 40, "CONCACAF Nations League": 30,
    "Friendly": 20,
}
DEFAULT_K = 30


def k_factor(tournament: str) -> float:
    return K_BY_COMP.get(tournament, DEFAULT_K)


def goal_mult(gd: int) -> float:
    gd = abs(gd)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


def expected(dr: float) -> float:
    """Expectativa de pontos do mandante dado dr = R_home - R_away (+ mando)."""
    return 1.0 / (10 ** (-dr / 400.0) + 1.0)


def _update(ratings, home, away, hs, as_, neutral, tournament):
    rh = ratings.get(home, INIT_RATING)
    ra = ratings.get(away, INIT_RATING)
    adv = 0.0 if neutral else HOME_ADV
    dr = rh - ra + adv
    we = expected(dr)
    w = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
    k = k_factor(tournament) * goal_mult(hs - as_)
    delta = k * (w - we)
    ratings[home] = rh + delta
    ratings[away] = ra - delta


def build():
    """Retorna dict com ratings atuais, ratings pré-jogo por fixture e função de calibração."""
    hist = wc_data.load_history()
    # exclui Copa 2026 do Kaggle (será aplicada via openfootball, mais atual)
    hist = hist[~((hist["tournament"] == "FIFA World Cup") & (hist["date"].dt.year == 2026))]

    ratings = {}
    calib = []  # (dr_prem), hs, as_  -> para calibrar Elo->gols (jogos desde 2015)
    for r in hist.itertuples(index=False):
        rh = ratings.get(r.home_team, INIT_RATING)
        ra = ratings.get(r.away_team, INIT_RATING)
        adv = 0.0 if r.neutral else HOME_ADV
        if r.date >= pd.Timestamp("2015-01-01"):
            calib.append((rh - ra + adv, r.home_score, r.away_score))
        _update(ratings, r.home_team, r.away_team, r.home_score, r.away_score, r.neutral, r.tournament)

    # --- calibração Elo -> gols esperados ---
    calib = np.array(calib, dtype=float)
    dr = calib[:, 0]
    sup = calib[:, 1] - calib[:, 2]            # saldo (home - away)
    tot = calib[:, 1] + calib[:, 2]            # total de gols
    # supremacia esperada ~ beta * dr  (linear pela origem)
    beta = float(np.sum(dr * sup) / np.sum(dr * dr))
    mean_total = float(np.mean(tot))
    calib_params = {"beta_sup_per_elo": beta, "mean_total_goals": mean_total,
                    "n_calib": int(len(calib))}

    pretournament = dict(ratings)

    # --- aplica resultados reais da Copa 2026 (openfootball), em ordem de data ---
    fixtures = sorted(wc_data.load_wc2026_fixtures(), key=lambda f: (f["date"] or "", f["round"] or ""))
    prematch = {}  # (date, home, away) -> (rh, ra) ANTES do jogo
    teams = wc_data.real_teams()
    for f in fixtures:
        h, a = f["home"], f["away"]
        if h not in teams or a not in teams:
            continue  # placeholder de mata-mata ainda não definido
        prematch[(f["date"], h, a)] = (ratings.get(h, INIT_RATING), ratings.get(a, INIT_RATING))
        if f["played"]:
            _update(ratings, h, a, f["home_score"], f["away_score"], True, "FIFA World Cup")

    return {
        "ratings_now": ratings,
        "ratings_pretournament": pretournament,
        "prematch": prematch,
        "calib": calib_params,
    }


def elo_lambdas(rh: float, ra: float, neutral: bool, calib: dict):
    """Converte ratings em (lambda_home, lambda_away) via calibração empírica."""
    adv = 0.0 if neutral else HOME_ADV
    dr = rh - ra + adv
    sup = calib["beta_sup_per_elo"] * dr
    total = calib["mean_total_goals"]
    lam_h = max(0.08, (total + sup) / 2.0)
    lam_a = max(0.08, (total - sup) / 2.0)
    return lam_h, lam_a


if __name__ == "__main__":
    res = build()
    rn = res["ratings_now"]
    teams = wc_data.real_teams()
    top = sorted(((t, rn[t]) for t in teams if t in rn), key=lambda x: x[1], reverse=True)
    print("Calibração:", res["calib"])
    print("\nTop 15 seleções da Copa 2026 por Elo (atual):")
    for i, (t, r) in enumerate(top[:15], 1):
        print(f"  {i:>2}. {t:<16} {r:7.1f}")
    print("\nExemplo de lambdas (Brasil vs Escócia, neutro):")
    lh, la = elo_lambdas(rn.get("Brazil"), rn.get("Scotland"), True, res["calib"])
    print(f"  Brasil xG={lh:.2f}  Escócia xG={la:.2f}")
    # salva ratings
    out = {"generated": True, "calib": res["calib"],
           "ratings": {t: round(rn[t], 1) for t in teams if t in rn}}
    (wc_data.PROJECT_ROOT / "analysis").mkdir(exist_ok=True)
    json.dump(out, open(wc_data.PROJECT_ROOT / "analysis" / "elo_ratings.json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

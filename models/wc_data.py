"""
Carregador de dados para o motor de previsão da Copa 2026.

Fontes:
  - data/raw/kaggle/results.csv      -> histórico de seleções (1872-2026) p/ treino e Elo
  - data/raw/openfootball/worldcup_2026.json -> fixtures e resultados REAIS da Copa 2026
  - data/raw/odds_api/odds_soccer_fifa_world_cup.json -> odds de mercado (quando houver)

Responsável por: normalização de nomes, filtro de jogos válidos, pesos de treino
(importância da competição × decaimento temporal) e a lista das 48 seleções reais.
"""
import json
import math
from pathlib import Path
from datetime import datetime

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"

# Nome no openfootball/odds -> nome canônico no results.csv
NAME_MAP = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Turkey": "Turkey",
    "Czech Republic": "Czech Republic",
    "South Korea": "South Korea",
    "DR Congo": "DR Congo",
    "Ivory Coast": "Ivory Coast",
    "Cape Verde": "Cape Verde",
}

# Peso de importância por tipo de torneio (estilo Ley et al. 2019 — força com peso)
COMPETITION_WEIGHT = {
    "FIFA World Cup": 60,
    "Copa América": 40, "UEFA Euro": 40, "African Cup of Nations": 40,
    "AFC Asian Cup": 40, "Gold Cup": 35, "CONCACAF Championship": 35,
    "Confederations Cup": 45,
    "FIFA World Cup qualification": 30,
    "UEFA Euro qualification": 25, "African Cup of Nations qualification": 22,
    "AFC Asian Cup qualification": 20, "Copa América qualification": 25,
    "UEFA Nations League": 28, "CONCACAF Nations League": 22,
    "Friendly": 10,
}
DEFAULT_WEIGHT = 18
HALFLIFE_DAYS = 365 * 2.5  # decaimento temporal (meia-vida ~2,5 anos)


def norm(team: str) -> str:
    return NAME_MAP.get(team, team)


def comp_weight(tournament: str) -> float:
    return COMPETITION_WEIGHT.get(tournament, DEFAULT_WEIGHT)


# ------------------------------------------------------------------ histórico
def load_history() -> pd.DataFrame:
    """Todos os jogos com placar, ordenados por data. Para Elo (cronológico)."""
    df = pd.read_csv(RAW / "kaggle" / "results.csv")
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    df["date"] = pd.to_datetime(df["date"])
    df["home_team"] = df["home_team"].map(norm)
    df["away_team"] = df["away_team"].map(norm)
    df["neutral"] = df["neutral"].astype(str).str.upper().eq("TRUE")
    return df.sort_values("date").reset_index(drop=True)


def training_set(ref_date: str = "2026-06-10", since: str = "2015-01-01") -> pd.DataFrame:
    """
    Jogos para FITAR o Dixon-Coles: janela recente, SEM os jogos da Copa 2026
    (evita leakage no backtest). Acrescenta peso = importância × decaimento temporal.
    """
    df = load_history()
    ref = pd.Timestamp(ref_date)
    mask = (df["date"] >= pd.Timestamp(since)) & (df["date"] <= ref)
    # remove a própria Copa 2026
    mask &= ~((df["tournament"] == "FIFA World Cup") & (df["date"].dt.year == 2026))
    df = df[mask].copy()
    age = (ref - df["date"]).dt.days
    df["w_time"] = age.map(lambda d: 0.5 ** (d / HALFLIFE_DAYS))
    df["w_comp"] = df["tournament"].map(comp_weight)
    df["weight"] = df["w_time"] * df["w_comp"]
    return df.reset_index(drop=True)


# ------------------------------------------------------------------ Copa 2026
def _parse_minute(g):
    return f"{g.get('name','?')} {g.get('minute','')}'".strip()


def load_wc2026_fixtures() -> list:
    """Fixtures da Copa 2026 (openfootball), com resultado real quando já jogado."""
    data = json.load(open(RAW / "openfootball" / "worldcup_2026.json", encoding="utf-8"))
    fixtures = []
    for m in data.get("matches", []):
        ft = m.get("score", {}).get("ft")
        fixtures.append({
            "date": m.get("date"),
            "round": m.get("round"),
            "group": m.get("group"),
            "home": norm(m.get("team1")),
            "away": norm(m.get("team2")),
            "home_raw": m.get("team1"),
            "away_raw": m.get("team2"),
            "played": ft is not None,
            "home_score": ft[0] if ft else None,
            "away_score": ft[1] if ft else None,
        })
    return fixtures


def real_teams() -> set:
    """As seleções reais (presentes no histórico). Exclui placeholders (1B, W73, 3A/B...)."""
    hist_teams = set(load_history()["home_team"]) | set(load_history()["away_team"])
    teams = set()
    for f in load_wc2026_fixtures():
        for t in (f["home"], f["away"]):
            if t in hist_teams:
                teams.add(t)
    return teams


def load_market_odds() -> dict:
    """Mapa (home,away)->probs 1X2 sem vig, a partir das odds da The Odds API."""
    path = RAW / "odds_api" / "odds_soccer_fifa_world_cup.json"
    if not path.exists():
        return {}
    games = json.load(open(path, encoding="utf-8"))
    out = {}
    for g in games:
        home, away = norm(g.get("home_team")), norm(g.get("away_team"))
        # média das casas para h2h
        sums = {"home": [], "draw": [], "away": []}
        for bk in g.get("bookmakers", []):
            for mk in bk.get("markets", []):
                if mk["key"] != "h2h":
                    continue
                price = {o["name"]: o["price"] for o in mk["outcomes"]}
                ph = price.get(g.get("home_team")); pa = price.get(g.get("away_team")); pd_ = price.get("Draw")
                if ph and pa and pd_:
                    inv = 1/ph + 1/pa + 1/pd_  # overround
                    sums["home"].append((1/ph)/inv)
                    sums["draw"].append((1/pd_)/inv)
                    sums["away"].append((1/pa)/inv)
        if sums["home"]:
            out[(home, away)] = {
                "home": sum(sums["home"]) / len(sums["home"]),
                "draw": sum(sums["draw"]) / len(sums["draw"]),
                "away": sum(sums["away"]) / len(sums["away"]),
                "n_books": len(sums["home"]),
            }
    return out


if __name__ == "__main__":
    ts = training_set()
    print(f"Treino: {len(ts)} jogos | peso total={ts['weight'].sum():.0f} | "
          f"de {ts['date'].min().date()} a {ts['date'].max().date()}")
    fx = load_wc2026_fixtures()
    played = [f for f in fx if f["played"]]
    print(f"Copa 2026: {len(fx)} fixtures, {len(played)} jogados")
    rt = real_teams()
    print(f"Seleções reais detectadas: {len(rt)}")
    odds = load_market_odds()
    print(f"Jogos com odds de mercado: {len(odds)}")

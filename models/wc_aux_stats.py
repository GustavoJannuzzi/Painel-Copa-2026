"""
Estatísticas auxiliares por jogo — Copa 2026.

Prevê para cada partida:
  · Escanteios (home / away) — Poisson calibrado (Casal et al. 2017)
  · Faltas (home / away)    — regressão força relativa (Bresciani et al. 2021)
  · Cartões amarelos        — taxa falta→cartão calibrada por Copas
  · Probabilidade de pênalti — estimada por intensidade tática
  · BTTS (ambas marcam)     — derivado da matriz Poisson bivariada
  · Over 2.5 gols           — derivado da matriz Poisson bivariada
  · Artilheiros prováveis   — dados reais Copa 2026 + histórico Kaggle (2020+)

Referências:
  Casal, C.A. et al. (2017). Analysis of corner kicks.
  Bresciani, G. et al. (2021). Fouls and yellow cards in international football.
  Dixon, M. & Coles, S. (1997). Modelling association football scores.

Saída: analysis/wc2026_aux_stats.json
"""
import sys
import json
import csv
import math
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wc_data
import wc_dixoncoles as dc

ROOT    = wc_data.PROJECT_ROOT
ANALYSIS = ROOT / "analysis"
RAW     = ROOT / "data" / "raw"

# ── Constantes calibradas para futebol internacional (Copa do Mundo) ──────────
# Casal et al. 2017: 9.2 escanteios/jogo em Copas (menos que ligas de clubes)
CORNERS_BASE = 4.6    # base por time → total ~9.2
CORNERS_ATT  = 0.55   # elasticidade: ataque forte → mais escanteios
CORNERS_DEF  = 0.22   # elasticidade: defesa adversária → menos escanteios

# Bresciani et al. 2021: ~21.5 faltas/jogo em Copas
FOULS_BASE   = 10.8   # base por time → total ~21.6
FOULS_ATT    = 0.38   # time com ataque forte tem mais posse → menos faltas
FOULS_DEF    = 0.28   # contra defesa forte → mais faltas (pressionado)

# Taxa falta→cartão amarelo em Copas: ~0.19 (Bresciani et al.)
YELLOW_RATE  = 0.19

# Probabilidade base de pênalti por jogo em Copas: ~0.27
PEN_BASE     = 0.265


def _btts_over25(lh: float, la: float, rho: float = 0.0):
    """BTTS e Over 2.5 gols a partir da matriz de placar Poisson bivariado."""
    m = dc.score_matrix(lh, la, rho)
    n = m.shape[0]
    btts  = float(sum(m[i][j] for i in range(1, n) for j in range(1, n)))
    over25 = float(sum(m[i][j] for i in range(n) for j in range(n) if i + j > 2))
    return round(btts, 4), round(over25, 4)


def _corners(att_h: float, def_h: float, att_a: float, def_a: float):
    """Escanteios por time usando elasticidades calibradas (log-space DC params)."""
    ch = CORNERS_BASE * math.exp(CORNERS_ATT * att_h - CORNERS_DEF * def_a)
    ca = CORNERS_BASE * math.exp(CORNERS_ATT * att_a - CORNERS_DEF * def_h)
    return round(ch, 1), round(ca, 1)


def _fouls(att_h: float, def_h: float, att_a: float, def_a: float):
    """Faltas por time — time com ataque fraco defende mais → comete mais faltas."""
    fh = FOULS_BASE * math.exp(-FOULS_ATT * att_h + FOULS_DEF * def_h)
    fa = FOULS_BASE * math.exp(-FOULS_ATT * att_a + FOULS_DEF * def_a)
    return round(fh, 1), round(fa, 1)


def _copa2026_events():
    """
    Extrai eventos reais da Copa 2026 (openfootball):
    - gols por jogador/time
    - artilheiros consolidados
    """
    path = RAW / "openfootball" / "worldcup_2026.json"
    if not path.exists():
        return {}, {}

    data    = json.load(open(path, encoding="utf-8"))
    scorers = defaultdict(lambda: defaultdict(lambda: {"goals": 0, "pen": 0}))
    goals_list_by_match = {}  # key = date_home_away → list of goal events

    for m in data.get("matches", []):
        if not m.get("score"):
            continue
        t1 = wc_data.norm(m["team1"])
        t2 = wc_data.norm(m["team2"])

        for g in m.get("goals1", []):
            if not g.get("own_goal"):
                scorers[t1][g["name"]]["goals"] += 1
                if g.get("penalty"):
                    scorers[t1][g["name"]]["pen"] += 1

        for g in m.get("goals2", []):
            if not g.get("own_goal"):
                scorers[t2][g["name"]]["goals"] += 1
                if g.get("penalty"):
                    scorers[t2][g["name"]]["pen"] += 1

        # Lista de eventos de gol para o modal
        key = f"{m['date']}_{t1}_{t2}"
        events = []
        for g in m.get("goals1", []):
            events.append({
                "team": t1, "name": g["name"], "minute": g.get("minute", "?"),
                "penalty": bool(g.get("penalty")), "own_goal": bool(g.get("own_goal"))
            })
        for g in m.get("goals2", []):
            events.append({
                "team": t2, "name": g["name"], "minute": g.get("minute", "?"),
                "penalty": bool(g.get("penalty")), "own_goal": bool(g.get("own_goal"))
            })
        events.sort(key=lambda e: _parse_min(e["minute"]))
        goals_list_by_match[key] = events

    # Converte para lista ordenada por gols
    result_scorers = {}
    for team, s in scorers.items():
        result_scorers[team] = sorted(
            [{"name": n, "goals": v["goals"], "pen": v["pen"]} for n, v in s.items()],
            key=lambda x: x["goals"], reverse=True
        )
    return result_scorers, goals_list_by_match


def _parse_min(minute_str: str) -> int:
    try:
        return int(str(minute_str).split("+")[0])
    except Exception:
        return 0


def _historical_scorers():
    """
    Artilheiros históricos recentes (2020–2026) do Kaggle — fallback para
    times sem gols ainda na Copa 2026.
    """
    path_goals   = RAW / "kaggle" / "goalscorers.csv"
    path_results = RAW / "kaggle" / "results.csv"
    if not path_goals.exists():
        return {}

    # Jogos por time desde 2020
    games_by_team = defaultdict(int)
    if path_results.exists():
        with open(path_results, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("date", "") >= "2020-01-01":
                    games_by_team[wc_data.norm(row["home_team"])] += 1
                    games_by_team[wc_data.norm(row["away_team"])] += 1

    # Gols por jogador desde 2020
    scorer_goals = defaultdict(lambda: defaultdict(int))
    with open(path_goals, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("date", "") < "2020-01-01":
                continue
            if row.get("own_goal", "").upper() == "TRUE":
                continue
            team   = wc_data.norm(row.get("team", ""))
            scorer = row.get("scorer", "").strip()
            if team and scorer:
                scorer_goals[team][scorer] += 1

    result = {}
    for team, scorers in scorer_goals.items():
        games = max(1, games_by_team.get(team, 10))
        result[team] = sorted(
            [{"name": n, "goals": g,
              "goals_per_game": round(g / games, 3), "pen": 0}
             for n, g in scorers.items()],
            key=lambda x: x["goals"], reverse=True
        )[:5]
    return result


def run():
    model_dc     = dc.fit()
    att          = model_dc["attack"]
    deff         = model_dc["defense"]
    rho          = model_dc["rho"]

    copa_sc, goals_events = _copa2026_events()
    hist_sc               = _historical_scorers()

    fixtures = sorted(
        wc_data.load_wc2026_fixtures(),
        key=lambda f: (f["date"] or "", f["round"] or "")
    )
    teams = wc_data.real_teams()

    # Jogos disputados por time na Copa (para calcular gols/jogo)
    copa_games = defaultdict(int)
    for f in fixtures:
        if f.get("played"):
            copa_games[f["home"]] += 1
            copa_games[f["away"]] += 1

    out = {}
    for f in fixtures:
        h, a = f["home"], f["away"]
        if h not in teams or a not in teams:
            continue

        att_h = att.get(h, 0.0)
        att_a = att.get(a, 0.0)
        def_h = deff.get(h, 0.0)
        def_a = deff.get(a, 0.0)

        dl = dc.dc_lambdas(model_dc, h, a, neutral=True)
        if dl is None:
            continue
        lh, la = dl
        btts, over25 = _btts_over25(lh, la, rho)

        ch, ca = _corners(att_h, def_h, att_a, def_a)
        fh, fa = _fouls(att_h, def_h, att_a, def_a)
        yh = round(fh * YELLOW_RATE, 1)
        ya = round(fa * YELLOW_RATE, 1)

        # Pênalti: base ajustada pela intensidade (mais faltas = mais pênaltis)
        pen_prob = round(min(0.92, PEN_BASE * (fh + fa) / 21.6), 3)

        def top_scorers(team):
            games = max(1, copa_games.get(team, 1))
            if team in copa_sc and copa_sc[team]:
                return [
                    {"name": s["name"], "goals": s["goals"],
                     "goals_per_game": round(s["goals"] / games, 2),
                     "pen": s.get("pen", 0)}
                    for s in copa_sc[team][:4]
                ]
            if team in hist_sc:
                return hist_sc[team][:4]
            return []

        key = f"{f['date']}_{h}_{a}"
        out[key] = {
            "home": h, "away": a, "date": f["date"],
            "corners":      {"home": ch, "away": ca, "total": round(ch + ca, 1)},
            "fouls":        {"home": fh, "away": fa, "total": round(fh + fa, 1)},
            "yellow_cards": {"home": yh, "away": ya, "total": round(yh + ya, 1)},
            "penalty_prob": pen_prob,
            "btts":         btts,
            "over_2_5":     over25,
            "xg":           {"home": round(lh, 2), "away": round(la, 2)},
            "scorers":      {"home": top_scorers(h), "away": top_scorers(a)},
            "goal_events":  goals_events.get(key, []),
        }

    path = ANALYSIS / "wc2026_aux_stats.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Aux stats: {len(out)} jogos. Salvo em {path}")
    return out


if __name__ == "__main__":
    run()

"""
FASE 3A — Módulo de impacto de escalação.

Constrói uma base de força individual de jogadores (PlayerStrengthDB)
a partir dos dados StatsBomb (WC 2022 + 2018), combinados com os ratings
Elo de cada seleção.

Lógica:
  1. Para cada partida histórica da Copa (StatsBomb), carrega a escalação.
  2. Jogadores do XI titular recebem uma "contribuição" baseada no Elo do time e
     na posição (goleiro/zagueiro têm peso defensivo, meia/atacante ofensivo).
  3. O impacto de uma escalação futura é medido comparando a força média dos
     titulares confirmados vs a força média histórica do time — gerando um
     fator multiplicativo sobre xG_home / xG_away.

Uso no pipeline:
  from wc_lineup_impact import LineupImpactModel
  model = LineupImpactModel.load_or_build()
  factor_h, factor_a = model.get_impact_factors(home_team, away_team, news_signals)
  # factor_h, factor_a in [0.75, 1.25] — ajusta xG previsto
"""
import sys
import json
import math
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wc_data

PROJECT_ROOT = wc_data.PROJECT_ROOT
SB_DIR       = PROJECT_ROOT / "data" / "raw" / "statsbomb"
CACHE_PATH   = PROJECT_ROOT / "analysis" / "lineup_player_db.json"

# Peso de posição: fração do impacto que vai para força ofensiva vs defensiva
POSITION_WEIGHT = {
    "Goalkeeper":          {"off": 0.0, "def": 1.0},
    "Center Back":         {"off": 0.1, "def": 0.9},
    "Left Back":           {"off": 0.3, "def": 0.7},
    "Right Back":          {"off": 0.3, "def": 0.7},
    "Left Wing Back":      {"off": 0.4, "def": 0.6},
    "Right Wing Back":     {"off": 0.4, "def": 0.6},
    "Defensive Midfield":  {"off": 0.4, "def": 0.6},
    "Center Midfield":     {"off": 0.5, "def": 0.5},
    "Left Midfield":       {"off": 0.6, "def": 0.4},
    "Right Midfield":      {"off": 0.6, "def": 0.4},
    "Left Wing":           {"off": 0.8, "def": 0.2},
    "Right Wing":          {"off": 0.8, "def": 0.2},
    "Attacking Midfield":  {"off": 0.8, "def": 0.2},
    "Center Forward":      {"off": 1.0, "def": 0.0},
    "Secondary Striker":   {"off": 0.9, "def": 0.1},
}
DEFAULT_POSITION_WEIGHT = {"off": 0.5, "def": 0.5}

# Impacto máximo por ausência de jogador-chave
MAX_IMPACT_FACTOR = 0.18  # ±18% no xG


class PlayerStrengthDB:
    """Base de dados de força individual por jogador."""

    def __init__(self):
        # player_id -> {"name": str, "teams": set, "elo_contrib": float, "n_matches": int}
        self.players: dict = {}
        # team_name -> {"avg_xi_elo": float, "n_matches": int}
        self.team_baselines: dict = {}

    def build_from_statsbomb(self, elo_ratings: dict):
        """
        Lê todos os arquivos de lineup do StatsBomb e constrói a base.
        elo_ratings: dict team_name -> rating
        """
        match_files = list((SB_DIR / "matches").glob("*.json"))
        if not match_files:
            return self

        all_lineups: list = []

        for mfile in match_files:
            matches = json.load(open(mfile, encoding="utf-8"))
            for match in matches:
                match_id = match.get("match_id")
                home_name = wc_data.norm(match.get("home_team", {}).get("home_team_name", ""))
                away_name = wc_data.norm(match.get("away_team", {}).get("away_team_name", ""))
                lineup_path = SB_DIR / "lineups" / f"{match_id}.json"
                if not lineup_path.exists():
                    continue

                lineup_data = json.load(open(lineup_path, encoding="utf-8"))
                for team_lineup in lineup_data:
                    team_sb = team_lineup.get("team_name", "")
                    team = wc_data.norm(team_sb)
                    elo = elo_ratings.get(team, 1500.0)
                    lineup = team_lineup.get("lineup", [])

                    xi_players = []
                    for p in lineup:
                        positions = p.get("positions", [])
                        # Verifica se jogou (aparece em posições)
                        started = any(
                            pos.get("start_reason") == "Starting XI"
                            for pos in positions
                        )
                        if started or positions:  # contabiliza todos que jogaram
                            primary_pos = positions[0].get("position", "") if positions else ""
                            xi_players.append({
                                "id": p.get("player_id"),
                                "name": p.get("player_name", ""),
                                "position": primary_pos,
                                "started": started,
                            })

                    all_lineups.append({
                        "match_id": match_id,
                        "team": team,
                        "elo": elo,
                        "players": xi_players,
                    })

        # Agrega por jogador
        player_elo_sum: dict = defaultdict(float)
        player_matches: dict = defaultdict(int)
        player_names: dict = {}
        player_teams: dict = defaultdict(set)

        for entry in all_lineups:
            team = entry["team"]
            elo  = entry["elo"]
            for p in entry["players"]:
                pid = p["id"]
                if pid is None:
                    continue
                player_elo_sum[pid] += elo
                player_matches[pid] += 1
                player_names[pid] = p["name"]
                player_teams[pid].add(team)

        for pid, total_elo in player_elo_sum.items():
            self.players[str(pid)] = {
                "name": player_names.get(pid, ""),
                "teams": list(player_teams[pid]),
                "avg_elo": round(total_elo / player_matches[pid], 1),
                "n_matches": player_matches[pid],
            }

        # Baseline por time: média dos jogadores históricos
        for entry in all_lineups:
            team = entry["team"]
            elos = [
                self.players[str(p["id"])]["avg_elo"]
                for p in entry["players"]
                if str(p["id"]) in self.players
            ]
            if not elos:
                continue
            if team not in self.team_baselines:
                self.team_baselines[team] = {"elo_sum": 0.0, "n": 0}
            self.team_baselines[team]["elo_sum"] += np.mean(elos)
            self.team_baselines[team]["n"] += 1

        # Converte para média
        for team, vals in self.team_baselines.items():
            vals["avg_xi_elo"] = round(vals["elo_sum"] / vals["n"], 1)
            del vals["elo_sum"], vals["n"]

        return self

    def save(self, path: Path = CACHE_PATH):
        json.dump(
            {"players": self.players, "team_baselines": self.team_baselines},
            open(path, "w", encoding="utf-8"),
            indent=2, ensure_ascii=False
        )

    @classmethod
    def load(cls, path: Path = CACHE_PATH):
        obj = cls()
        if not path.exists():
            return None
        data = json.load(open(path, encoding="utf-8"))
        obj.players = data.get("players", {})
        obj.team_baselines = data.get("team_baselines", {})
        return obj

    def find_player(self, name: str, team: str = None):
        """Busca jogador por nome (fuzzy match)."""
        name_lower = name.lower().strip()
        # Exact match primeiro
        for pid, p in self.players.items():
            if p["name"].lower() == name_lower:
                if team is None or team in p["teams"]:
                    return pid, p
        # Partial match (last name)
        parts = name_lower.split()
        last_name = parts[-1] if parts else name_lower
        if len(last_name) > 3:
            for pid, p in self.players.items():
                if last_name in p["name"].lower():
                    if team is None or team in p["teams"]:
                        return pid, p
        return None, None


class LineupImpactModel:
    """
    Calcula fatores de impacto de escalação para ajustar xG dos modelos.

    Uso:
      model = LineupImpactModel.load_or_build()
      factor_h, factor_a = model.get_impact_factors(home, away, news_signals)
    """

    def __init__(self, db: PlayerStrengthDB, current_elo: dict):
        self.db = db
        self.elo = current_elo

    @classmethod
    def load_or_build(cls, elo_ratings: dict = None):
        """Carrega do cache ou reconstrói."""
        db = PlayerStrengthDB.load()
        if db is None or not db.players:
            if elo_ratings is None:
                import wc_elo
                elo_data = wc_elo.build()
                elo_ratings = elo_data["ratings_now"]
            db = PlayerStrengthDB()
            db.build_from_statsbomb(elo_ratings)
            db.save()
            print(f"  PlayerStrengthDB: {len(db.players)} jogadores, "
                  f"{len(db.team_baselines)} times")

        if elo_ratings is None:
            import wc_elo
            elo_data = wc_elo.build()
            elo_ratings = elo_data["ratings_now"]

        return cls(db, elo_ratings)

    def get_impact_factors(
        self,
        home: str,
        away: str,
        news_signals: dict = None,
    ) -> tuple:
        """
        Retorna (factor_home, factor_away) para ajustar xG.

        news_signals: {
          'home': {'absent': [...], 'confirmed': [...]},
          'away': {'absent': [...], 'confirmed': [...]},
        }
        factor > 1.0: time mais forte que baseline (confirmação de estrelas)
        factor < 1.0: time mais fraco (ausência de jogadores-chave)
        """
        if news_signals is None:
            return 1.0, 1.0

        def _team_factor(team_name, signals):
            if not signals:
                return 1.0

            baseline = self.db.team_baselines.get(team_name, {}).get("avg_xi_elo")
            team_elo = self.elo.get(team_name, 1500.0)
            if baseline is None:
                baseline = team_elo

            absent_penalty = 0.0
            for pname in signals.get("absent", []):
                _, player = self.db.find_player(pname, team_name)
                if player:
                    player_elo = player["avg_elo"]
                    # Impacto relativo: quanto acima/abaixo da média do time
                    relative = (player_elo - baseline) / max(baseline, 1)
                    absent_penalty += max(0, relative) * MAX_IMPACT_FACTOR
                else:
                    # Jogador não identificado mas mencionado como desfalque — impacto leve
                    absent_penalty += 0.03

            confirmed_bonus = 0.0
            for pname in signals.get("confirmed", []):
                _, player = self.db.find_player(pname, team_name)
                if player:
                    player_elo = player["avg_elo"]
                    relative = (player_elo - baseline) / max(baseline, 1)
                    confirmed_bonus += max(0, relative) * MAX_IMPACT_FACTOR * 0.5

            net = confirmed_bonus - absent_penalty
            # Limita o impacto total
            factor = 1.0 + max(-MAX_IMPACT_FACTOR, min(MAX_IMPACT_FACTOR, net))
            return round(factor, 4)

        home_signals = (news_signals or {}).get("home", {})
        away_signals = (news_signals or {}).get("away", {})

        return _team_factor(home, home_signals), _team_factor(away, away_signals)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import wc_elo
    print("[LineupImpact] Construindo PlayerStrengthDB a partir do StatsBomb...")
    elo_data = wc_elo.build()
    db = PlayerStrengthDB()
    db.build_from_statsbomb(elo_data["ratings_now"])
    db.save()
    print(f"  {len(db.players)} jogadores | {len(db.team_baselines)} times")
    print("\n  Top times por baseline Elo do XI:")
    top = sorted(db.team_baselines.items(), key=lambda x: x[1].get("avg_xi_elo", 0), reverse=True)
    for t, v in top[:8]:
        print(f"    {t:<20} avg_xi_elo={v['avg_xi_elo']}")

    print("\n  Teste de impacto (Neymar ausente no Brasil):")
    model = LineupImpactModel(db, elo_data["ratings_now"])
    fh, fa = model.get_impact_factors(
        "Brazil", "Scotland",
        news_signals={"home": {"absent": ["Neymar"]}, "away": {}}
    )
    print(f"    factor_home={fh} | factor_away={fa}")
    print(f"    Interpretacao: Brasil xG reduzido por {(1-fh)*100:.1f}%")

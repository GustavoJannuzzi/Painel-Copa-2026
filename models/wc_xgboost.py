"""
FASE 4 — XGBoost Meta-Learner para ensemble da Copa 2026.

Treina um modelo de gradiente boosting que aprende a combinar os sinais do
Elo e do Dixon-Coles, além de features contextuais (diferencial de ratings,
forma recente, rodada) para prever o desfecho 1X2.

Features:
  - elo_home, elo_away, elo_diff, elo_win_prob
  - dc_xg_home, dc_xg_away, dc_xg_diff
  - p_elo_home, p_elo_draw, p_elo_away
  - p_dc_home, p_dc_draw, p_dc_away
  - form_home_w5 (win rate últimos 5 jogos — do histórico Kaggle)
  - form_away_w5
  - h2h_home_win_rate (confrontos diretos)
  - days_since_last_game_home, days_since_last_game_away
  - match_round (1=grupo, 2=oitavas, etc.)

Saída:
  - analysis/xgboost_model.json (parâmetros + importância de features)
  - analysis/xgboost_shap.json (SHAP values por jogo da Copa)
"""
import sys
import json
import math
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wc_data
import wc_elo
import wc_dixoncoles as dc

try:
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    from sklearn.preprocessing import LabelEncoder
    _XGB_OK = True
except ImportError:
    _XGB_OK = False

PROJECT_ROOT = wc_data.PROJECT_ROOT
MODEL_PATH   = PROJECT_ROOT / "analysis" / "xgboost_model.json"
PRED_PATH    = PROJECT_ROOT / "analysis" / "wc2026_predictions.json"


# ──────────────────────────────────────────────────────────────────────────────
# Feature Engineering
# ──────────────────────────────────────────────────────────────────────────────

def _elo_win_prob(elo_home, elo_away):
    """Probabilidade de vitória do mandante pelo Elo (sem mando por ser neutro)."""
    dr = elo_home - elo_away
    return 1.0 / (10 ** (-dr / 400.0) + 1.0)


def _form_last_n(df_history: pd.DataFrame, team: str, ref_date, n: int = 5) -> dict:
    """Win rate, gols marcados/sofridos nos últimos N jogos antes da ref_date."""
    mask = (
        ((df_history["home_team"] == team) | (df_history["away_team"] == team)) &
        (df_history["date"] < ref_date)
    )
    recent = df_history[mask].sort_values("date").tail(n)
    if recent.empty:
        return {"wins": 0.4, "gf": 1.3, "ga": 1.3, "n": 0}
    wins, gf, ga = 0, 0, 0
    for _, row in recent.iterrows():
        if row["home_team"] == team:
            gf += row["home_score"]; ga += row["away_score"]
            wins += 1 if row["home_score"] > row["away_score"] else (0.5 if row["home_score"] == row["away_score"] else 0)
        else:
            gf += row["away_score"]; ga += row["home_score"]
            wins += 1 if row["away_score"] > row["home_score"] else (0.5 if row["away_score"] == row["home_score"] else 0)
    n_games = len(recent)
    return {"wins": wins / n_games, "gf": gf / n_games, "ga": ga / n_games, "n": n_games}


def _h2h(df_history: pd.DataFrame, home: str, away: str, ref_date, n: int = 10) -> float:
    """Taxa de vitória do 'home' nos últimos N confrontos diretos."""
    mask = (
        ((df_history["home_team"] == home) & (df_history["away_team"] == away)) |
        ((df_history["home_team"] == away) & (df_history["away_team"] == home))
    ) & (df_history["date"] < ref_date)
    h2h = df_history[mask].sort_values("date").tail(n)
    if h2h.empty:
        return 0.5  # sem histórico
    wins = 0
    for _, row in h2h.iterrows():
        if row["home_team"] == home:
            wins += 1 if row["home_score"] > row["away_score"] else (0.5 if row["home_score"] == row["away_score"] else 0)
        else:
            wins += 1 if row["away_score"] > row["home_score"] else (0.5 if row["away_score"] == row["home_score"] else 0)
    return wins / len(h2h)


def _days_since_last(df_history: pd.DataFrame, team: str, ref_date) -> float:
    """Dias desde o último jogo do time."""
    mask = (
        ((df_history["home_team"] == team) | (df_history["away_team"] == team)) &
        (df_history["date"] < ref_date)
    )
    last = df_history[mask]["date"].max()
    if pd.isna(last):
        return 30.0
    return float((ref_date - last).days)


def build_features(
    df_history: pd.DataFrame,
    elo_data: dict,
    dc_model: dict,
    fixtures: list,
) -> pd.DataFrame:
    """Constrói a matriz de features para todos os jogos com resultado real."""
    rows = []
    teams = wc_data.real_teams()

    for f in fixtures:
        h, a = f["home"], f["away"]
        if h not in teams or a not in teams:
            continue
        if f["home_score"] is None or f["away_score"] is None:
            continue

        ref_date = pd.Timestamp(f["date"]) if f.get("date") else None
        if ref_date is None:
            continue

        # Elo pré-jogo
        rh, ra = elo_data["prematch"].get((f["date"], h, a), (None, None))
        if rh is None:
            rh = elo_data["ratings_now"].get(h, 1500)
            ra = elo_data["ratings_now"].get(a, 1500)

        elo_win = _elo_win_prob(rh, ra)
        calib   = elo_data["calib"]
        from wc_elo import elo_lambdas
        elo_lh, elo_la = elo_lambdas(rh, ra, True, calib)

        # Dixon-Coles xG
        dl = dc.dc_lambdas(dc_model, h, a, neutral=True)
        if dl is None:
            continue
        dc_lh, dc_la = dl
        m_dc = dc.score_matrix(dc_lh, dc_la, dc_model["rho"])
        n_m  = m_dc.shape[0]
        pw = sum(m_dc[i][j] for i in range(n_m) for j in range(n_m) if i > j)
        pd_ = sum(m_dc[i][i] for i in range(n_m))
        pl  = 1 - pw - pd_

        # Elo 1X2
        from wc_elo import elo_lambdas
        m_elo = dc.score_matrix(elo_lh, elo_la, 0.0)
        n_e   = m_elo.shape[0]
        ew = sum(m_elo[i][j] for i in range(n_e) for j in range(n_e) if i > j)
        ed = sum(m_elo[i][i] for i in range(n_e))
        el = 1 - ew - ed

        # Forma recente (pré-jogo)
        form_h = _form_last_n(df_history, h, ref_date, 5)
        form_a = _form_last_n(df_history, a, ref_date, 5)
        h2h    = _h2h(df_history, h, a, ref_date, 10)
        days_h = _days_since_last(df_history, h, ref_date)
        days_a = _days_since_last(df_history, a, ref_date)

        # Round encoding
        round_str = (f.get("round") or "").lower()
        if "final" in round_str and "semi" not in round_str and "quarter" not in round_str:
            round_num = 6
        elif "semi" in round_str:
            round_num = 5
        elif "quarter" in round_str:
            round_num = 4
        elif "round of 16" in round_str or "oitavas" in round_str:
            round_num = 3
        elif "round of 32" in round_str or "decimo" in round_str:
            round_num = 2
        else:
            round_num = 1  # grupo

        hs, as_ = f["home_score"], f["away_score"]
        outcome = 0 if hs > as_ else (1 if hs == as_ else 2)

        rows.append({
            "date": f["date"],
            "home": h, "away": a,
            # Elo features
            "elo_home": rh, "elo_away": ra,
            "elo_diff": rh - ra,
            "elo_win_prob": elo_win,
            # DC features
            "dc_xg_home": dc_lh, "dc_xg_away": dc_la,
            "dc_xg_diff": dc_lh - dc_la,
            # Probabilidades modelo
            "p_elo_home": ew, "p_elo_draw": ed, "p_elo_away": el,
            "p_dc_home": pw, "p_dc_draw": pd_, "p_dc_away": pl,
            # Forma
            "form_h_wins": form_h["wins"], "form_h_gf": form_h["gf"], "form_h_ga": form_h["ga"],
            "form_a_wins": form_a["wins"], "form_a_gf": form_a["gf"], "form_a_ga": form_a["ga"],
            "h2h_home_rate": h2h,
            # Fadiga
            "days_h": min(days_h, 90.0), "days_a": min(days_a, 90.0),
            # Rodada
            "round_num": round_num,
            # Target
            "outcome": outcome,
        })

    return pd.DataFrame(rows)


FEATURE_COLS = [
    "elo_diff", "elo_win_prob",
    "dc_xg_home", "dc_xg_away", "dc_xg_diff",
    "p_elo_home", "p_elo_draw", "p_elo_away",
    "p_dc_home", "p_dc_draw", "p_dc_away",
    "form_h_wins", "form_h_gf", "form_h_ga",
    "form_a_wins", "form_a_gf", "form_a_ga",
    "h2h_home_rate", "days_h", "days_a",
    "round_num",
]


# ──────────────────────────────────────────────────────────────────────────────
# Treino e predição
# ──────────────────────────────────────────────────────────────────────────────

def train(df: pd.DataFrame) -> dict:
    """Treina XGBoost multiclass no DataFrame de features."""
    if not _XGB_OK:
        raise ImportError("xgboost nao instalado")
    if len(df) < 20:
        raise ValueError(f"Poucos exemplos para treinar: {len(df)}")

    X = df[FEATURE_COLS].fillna(0).values
    y = df["outcome"].values

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        verbosity=0,
    )
    model.fit(X, y)

    # Importância de features
    importance = {
        col: float(model.feature_importances_[i])
        for i, col in enumerate(FEATURE_COLS)
    }

    # Cross-validation (temporal) — só se houver dados suficientes
    cv_rps = None
    if len(df) >= 30:
        from sklearn.model_selection import TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=3)
        rps_scores = []
        for train_idx, val_idx in tscv.split(X):
            m_cv = xgb.XGBClassifier(
                n_estimators=100, max_depth=3, learning_rate=0.1,
                subsample=0.8, colsample_bytree=0.8,
                use_label_encoder=False, eval_metric="mlogloss",
                random_state=42, verbosity=0,
            )
            m_cv.fit(X[train_idx], y[train_idx])
            proba = m_cv.predict_proba(X[val_idx])
            for i, idx in enumerate(val_idx):
                a_vec = [0, 0, 0]; a_vec[y[idx]] = 1
                cp = np.cumsum(proba[i]); ca = np.cumsum(a_vec)
                rps_scores.append(float(np.sum((cp - ca) ** 2) / 2))
        cv_rps = round(float(np.mean(rps_scores)), 4) if rps_scores else None

    return {"model": model, "importance": importance, "cv_rps": cv_rps}


def predict_proba(model, row: dict) -> list:
    """Retorna [P(home), P(draw), P(away)] para uma linha de features."""
    X = np.array([[row.get(col, 0.0) for col in FEATURE_COLS]])
    proba = model.predict_proba(X)[0]
    # Garante ordem: 0=home, 1=draw, 2=away
    classes = list(model.classes_)
    result = [0.0, 0.0, 0.0]
    for i, c in enumerate(classes):
        result[c] = float(proba[i])
    return result


def run(blend_weight: float = 0.15) -> dict:
    """
    Treina o meta-learner e retorna as probabilidades ajustadas para cada jogo.
    blend_weight: peso do XGBoost no ensemble final (0.15 = 15%).
    """
    if not _XGB_OK:
        print("  [XGBoost] xgboost nao instalado, pulando.")
        return {}

    print("  [XGBoost] Construindo features...")
    elo_data = wc_elo.build()
    dc_model = dc.fit()
    df_hist  = wc_data.load_history()
    fixtures = wc_data.load_wc2026_fixtures()

    df = build_features(df_hist, elo_data, dc_model, fixtures)
    print(f"  [XGBoost] {len(df)} exemplos | {len(FEATURE_COLS)} features")

    if len(df) < 20:
        print("  [XGBoost] Poucos exemplos, pulando treino.")
        return {}

    result = train(df)
    model  = result["model"]
    print(f"  [XGBoost] CV RPS: {result['cv_rps']}")

    # Top features
    top_features = sorted(result["importance"].items(), key=lambda x: x[1], reverse=True)[:8]
    print("  [XGBoost] Top features:")
    for feat, imp in top_features:
        print(f"    {feat:<25} {imp:.4f}")

    # Predições por jogo (para integração no ensemble principal)
    teams = wc_data.real_teams()
    preds = {}
    for _, row in df.iterrows():
        h, a, date = row["home"], row["away"], row["date"]
        p_xgb = predict_proba(model, row.to_dict())
        preds[(date, h, a)] = p_xgb

    # Salva metadados
    out = {
        "n_train": int(len(df)),
        "cv_rps": result["cv_rps"],
        "feature_importance": {k: round(v, 4) for k, v in result["importance"].items()},
        "blend_weight": blend_weight,
    }
    json.dump(out, open(MODEL_PATH, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"  [XGBoost] Modelo salvo em: {MODEL_PATH}")

    return {"model": model, "preds": preds, "meta": out}


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run()
    if result:
        print(f"\n[OK] XGBoost meta-learner treinado com sucesso.")

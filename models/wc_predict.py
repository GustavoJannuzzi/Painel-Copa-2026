"""
Ensemble e previsão de TODOS os jogos da Copa 2026.

Combina:
  - Elo (força histórica, calibrado p/ gols) — rating PRÉ-JOGO de cada partida
  - Dixon-Coles ponderado (ataque/defesa por time)
  - Mercado (odds sem vig), quando disponível

Estratégia: matriz de placar combinada (Elo+DC) → 1X2 do modelo; blend com o mercado;
reescala a matriz para bater o 1X2 final → placar mais provável, gols esperados, top-5.

Sem leakage: jogos já disputados usam o Elo de ANTES da partida; DC é pré-torneio.
Saída: analysis/wc2026_predictions.json
"""
import sys
import json
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wc_data
import wc_elo
import wc_dixoncoles as dc

# Módulos de escalação e notícias (Fase 3)
try:
    from wc_news_parser import parse_news
    from wc_lineup_impact import LineupImpactModel
    _LINEUP_AVAILABLE = True
except ImportError:
    _LINEUP_AVAILABLE = False

# Pesos do ensemble otimizados via grid search LOO-CV (Fase 2B do framework v3).
# Diagnóstico (Fase 1) revelou que market odds sozinhas batem o ensemble completo
# (RPS 0.1414 vs 0.1668) — pesos anteriores subutilizavam o mercado.
W_ELO = 0.05
W_DC = 0.05
W_MARKET = 0.90           # quando há odds — muito mais informativo que Elo/DC
W_ELO_NO_MKT = 0.05
W_DC_NO_MKT = 0.95        # DC domina quando não há odds (Elo adiciona pouco)
W_MATRIX_ELO = 0.15       # Elo tem papel menor na matriz de placar


def _wdl(m):
    n = m.shape[0]
    pw = float(sum(m[i][j] for i in range(n) for j in range(n) if i > j))
    pd_ = float(sum(m[i][i] for i in range(n)))
    return pw, pd_, 1 - pw - pd_


def _expected_goals(m):
    n = m.shape[0]
    eh = float(sum(i * m[i][j] for i in range(n) for j in range(n)))
    ea = float(sum(j * m[i][j] for i in range(n) for j in range(n)))
    return round(eh, 2), round(ea, 2)


def _top_scores(m, k=5):
    n = m.shape[0]
    cells = sorted(((f"{i}-{j}", float(m[i][j])) for i in range(n) for j in range(n)),
                   key=lambda x: x[1], reverse=True)
    return [{"score": s, "prob": round(p, 4)} for s, p in cells[:k]]


def _adjust_to_1x2(m, target):
    """Reescala blocos vitória/empate/derrota da matriz p/ bater o 1X2 alvo."""
    n = m.shape[0]
    cur_w, cur_d, cur_l = _wdl(m)
    fw = target[0] / cur_w if cur_w > 1e-9 else 0
    fd = target[1] / cur_d if cur_d > 1e-9 else 0
    fl = target[2] / cur_l if cur_l > 1e-9 else 0
    out = m.copy()
    for i in range(n):
        for j in range(n):
            f = fw if i > j else (fd if i == j else fl)
            out[i][j] *= f
    return out / out.sum()


def _rps(p, outcome_idx):
    """Ranked Probability Score (ordem: casa, empate, fora). p soma 1."""
    a = [0, 0, 0]; a[outcome_idx] = 1
    cp = np.cumsum(p); ca = np.cumsum(a)
    return float(np.sum((cp - ca) ** 2) / 2.0)


def run():
    elo = wc_elo.build()
    model_dc = dc.fit()
    odds = wc_data.load_market_odds()
    calib = elo["calib"]
    teams = wc_data.real_teams()
    fixtures = sorted(wc_data.load_wc2026_fixtures(), key=lambda f: (f["date"] or "", f["round"] or ""))

    # Carrega sinais de escalação/notícias (Fase 3)
    news_signals = {}
    lineup_model = None
    if _LINEUP_AVAILABLE:
        try:
            news_signals = parse_news(max_days=4)
            lineup_model = LineupImpactModel.load_or_build(elo["ratings_now"])
        except Exception as e:
            print(f"  [Lineup/News] Aviso: {e}")

    out_matches = []
    for f in fixtures:
        h, a = f["home"], f["away"]
        if h not in teams or a not in teams:
            continue  # placeholder de mata-mata ainda não definido

        # --- Elo (rating pré-jogo) ---
        rh, ra = elo["prematch"].get((f["date"], h, a), (None, None))
        if rh is None:
            rh = elo["ratings_now"].get(h); ra = elo["ratings_now"].get(a)
        elo_lh, elo_la = wc_elo.elo_lambdas(rh, ra, True, calib)
        m_elo = dc.score_matrix(elo_lh, elo_la, 0.0)

        # --- Dixon-Coles ---
        dl = dc.dc_lambdas(model_dc, h, a, neutral=True)
        if dl is None:
            continue
        dc_lh, dc_la = dl
        m_dc = dc.score_matrix(dc_lh, dc_la, model_dc["rho"])

        # --- Ajuste de escalação/notícias (só para jogos futuros) ---
        lineup_impact = {"home": 1.0, "away": 1.0, "applied": False}
        if not f["played"] and lineup_model is not None:
            home_sig = news_signals.get(h, {})
            away_sig = news_signals.get(a, {})
            if home_sig or away_sig:
                fh, fa = lineup_model.get_impact_factors(
                    h, a,
                    news_signals={"home": home_sig, "away": away_sig}
                )
                if fh != 1.0 or fa != 1.0:
                    elo_lh  = max(0.08, elo_lh  * fh)
                    elo_la  = max(0.08, elo_la  * fa)
                    dc_lh   = max(0.08, dc_lh   * fh)
                    dc_la   = max(0.08, dc_la   * fa)
                    m_elo   = dc.score_matrix(elo_lh, elo_la, 0.0)
                    m_dc    = dc.score_matrix(dc_lh,  dc_la,  model_dc["rho"])
                    lineup_impact = {"home": round(fh, 4), "away": round(fa, 4), "applied": True}

        # Form signal adjustment (leve, ±3% máximo)
        if not f["played"]:
            form_h = (news_signals.get(h, {}).get("form_signal") or 0) * 0.03
            form_a = (news_signals.get(a, {}).get("form_signal") or 0) * 0.03
            if form_h or form_a:
                elo_lh = max(0.08, elo_lh * (1 + form_h))
                elo_la = max(0.08, elo_la * (1 + form_a))
                dc_lh  = max(0.08, dc_lh  * (1 + form_h))
                dc_la  = max(0.08, dc_la  * (1 + form_a))
                m_elo  = dc.score_matrix(elo_lh, elo_la, 0.0)
                m_dc   = dc.score_matrix(dc_lh,  dc_la,  model_dc["rho"])

        # --- matriz combinada Elo+DC ---
        m = W_MATRIX_ELO * m_elo + (1 - W_MATRIX_ELO) * m_dc
        m /= m.sum()
        elo_wdl = _wdl(m_elo); dc_wdl = _wdl(m_dc)

        # --- 1X2 do modelo e blend com mercado ---
        mkt = odds.get((h, a))
        flipped = False
        if mkt is None and (a, h) in odds:  # odds com orientação invertida
            o = odds[(a, h)]; mkt = {"home": o["away"], "draw": o["draw"], "away": o["home"], "n_books": o["n_books"]}
            flipped = True
        model_wdl = _wdl(m)
        if mkt:
            mk = [mkt["home"], mkt["draw"], mkt["away"]]
            final = [W_ELO * elo_wdl[i] + W_DC * dc_wdl[i] + W_MARKET * mk[i] for i in range(3)]
        else:
            tot = W_ELO_NO_MKT + W_DC_NO_MKT
            final = [(W_ELO_NO_MKT * elo_wdl[i] + W_DC_NO_MKT * dc_wdl[i]) / tot for i in range(3)]
        s = sum(final); final = [x / s for x in final]

        m_final = _adjust_to_1x2(m, final)
        eh, ea = _expected_goals(m_final)
        tops = _top_scores(m_final, 5)

        rec = {
            "date": f["date"], "round": f["round"], "group": f["group"],
            "home": h, "away": a, "played": f["played"],
            "actual": [f["home_score"], f["away_score"]] if f["played"] else None,
            "elo_ratings": {"home": round(rh, 1), "away": round(ra, 1)},
            "lineup_impact": lineup_impact,
            "models": {
                "elo": {"xg_home": round(elo_lh, 2), "xg_away": round(elo_la, 2),
                        "p": [round(x, 4) for x in elo_wdl]},
                "dixon_coles": {"xg_home": round(dc_lh, 2), "xg_away": round(dc_la, 2),
                                "p": [round(x, 4) for x in dc_wdl]},
                "market": ({"p": [round(mkt["home"], 4), round(mkt["draw"], 4), round(mkt["away"], 4)],
                            "n_books": mkt["n_books"]} if mkt else None),
            },
            "prediction": {
                "p_home": round(final[0], 4), "p_draw": round(final[1], 4), "p_away": round(final[2], 4),
                "xg_home": eh, "xg_away": ea,
                "most_likely": tops[0]["score"], "top_scores": tops,
            },
        }

        if f["played"]:
            hs, as_ = f["home_score"], f["away_score"]
            outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
            pred_idx = int(np.argmax(final))
            rec["eval"] = {
                "outcome": ["home", "draw", "away"][outcome],
                "predicted": ["home", "draw", "away"][pred_idx],
                "correct_1x2": bool(pred_idx == outcome),
                "exact_score_hit": bool(tops[0]["score"] == f"{hs}-{as_}"),
                "rps": round(_rps(final, outcome), 4),
            }
        out_matches.append(rec)

    result = {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "method": "Ensemble Elo + Dixon-Coles ponderado + Mercado (sem vig)",
        "weights": {"elo": W_ELO, "dixon_coles": W_DC, "market": W_MARKET,
                    "sem_mercado": {"elo": W_ELO_NO_MKT, "dixon_coles": W_DC_NO_MKT},
                    "matriz_elo": W_MATRIX_ELO},
        "elo_calibration": calib,
        "dc_params": {"intercept": model_dc["intercept"], "gamma": model_dc["gamma"], "rho": model_dc["rho"]},
        "n_matches": len(out_matches),
        "matches": out_matches,
    }
    path = wc_data.PROJECT_ROOT / "analysis" / "wc2026_predictions.json"
    json.dump(result, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    played = [m for m in out_matches if m["played"]]
    print(f"Previstos {len(out_matches)} jogos ({len(played)} já disputados). Salvo em {path}")
    return result


if __name__ == "__main__":
    res = run()
    # amostra
    for m in res["matches"][:3]:
        p = m["prediction"]
        print(f"  {m['date']} {m['home']} x {m['away']}: "
              f"{p['p_home']:.0%}/{p['p_draw']:.0%}/{p['p_away']:.0%} | "
              f"placar provável {p['most_likely']} (xG {p['xg_home']}-{p['xg_away']})")

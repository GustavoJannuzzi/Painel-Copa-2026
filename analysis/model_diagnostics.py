"""
FASE 1 — Diagnóstico quantitativo do framework Copa 2026.

Testa:
  1. Temporal cross-validation (fit 2015→2024, validate 2024→2026)
  2. Calibration ECE + reliability diagram detalhado
  3. Erro por faixa de força (favorito/equilibrado/zebra)
  4. Análise do time-decay (halflife: 1, 1.5, 2, 2.5, 3 anos)
  5. Sinergia do ensemble: cada componente isolado vs combinações

Saída: analysis/diagnostics_report.json
"""
import sys
import json
import math
from pathlib import Path
from itertools import product

import numpy as np
from scipy.optimize import minimize, minimize_scalar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "models"))
import wc_data
import wc_elo
import wc_dixoncoles as dc

PROJECT_ROOT = wc_data.PROJECT_ROOT
PRED_PATH = PROJECT_ROOT / "analysis" / "wc2026_predictions.json"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def rps(p, outcome):
    a = [0, 0, 0]; a[outcome] = 1
    return float(np.sum((np.cumsum(p) - np.cumsum(a)) ** 2) / 2)


def logloss(p, outcome):
    return -math.log(max(p[outcome], 1e-12))


def ece(pairs, n_bins=10):
    """Expected Calibration Error (ECE) — média ponderada do erro de calibração."""
    cp = np.array(pairs)
    errors = []
    for lo in np.arange(0, 1.0, 1 / n_bins):
        hi = lo + 1 / n_bins
        sel = cp[(cp[:, 0] >= lo) & (cp[:, 0] < hi)]
        if len(sel):
            errors.append(abs(sel[:, 0].mean() - sel[:, 1].mean()) * len(sel))
    return sum(errors) / max(len(cp), 1)


def load_played():
    data = json.load(open(PRED_PATH, encoding="utf-8"))
    return [m for m in data["matches"] if m["played"]]


# ──────────────────────────────────────────────────────────────────────────────
# 1. Cross-Validation Temporal
# ──────────────────────────────────────────────────────────────────────────────

def temporal_cross_validation():
    """Fit em 2015→2024, valida em 2024-01-01→2026-06-10 (pré-Copa).
    Mede RPS out-of-sample do DC para detectar overfitting."""
    print("  [1/5] Temporal cross-validation...")

    train_df = wc_data.training_set(ref_date="2023-12-31", since="2015-01-01")
    val_df   = wc_data.training_set(ref_date="2026-06-10", since="2024-01-01")
    # Remove Copa 2026 do val também (já feito no training_set)

    teams_train = set(train_df["home_team"]) | set(train_df["away_team"])
    val_df = val_df[val_df["home_team"].isin(teams_train) & val_df["away_team"].isin(teams_train)].copy()

    if len(val_df) < 10:
        return {"error": "val set muito pequeno", "n_val": len(val_df)}

    # Fit em treino
    from scipy.optimize import minimize, minimize_scalar
    orig_ridge = dc.RIDGE
    # Usamos RIDGE atual
    model_tr = _fit_dc_on_df(train_df)

    # Avalia no val set
    rps_vals_dc, rps_vals_naive = [], []
    for _, row in val_df.iterrows():
        h, a = row["home_team"], row["away_team"]
        hs, as_ = int(row["home_score"]), int(row["away_score"])
        outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
        dl = dc.dc_lambdas(model_tr, h, a, neutral=bool(row["neutral"]))
        if dl is None:
            continue
        lh, la = dl
        m = dc.score_matrix(lh, la, model_tr["rho"])
        n_m = m.shape[0]
        pw = sum(m[i][j] for i in range(n_m) for j in range(n_m) if i > j)
        pd_ = sum(m[i][i] for i in range(n_m))
        pl = 1 - pw - pd_
        rps_vals_dc.append(rps([pw, pd_, pl], outcome))
        rps_vals_naive.append(rps([1/3, 1/3, 1/3], outcome))

    # Fit com todo o dataset (in-sample) e avalia no mesmo val
    model_full = _fit_dc_on_df(wc_data.training_set(ref_date="2026-06-10"))
    rps_vals_full = []
    for _, row in val_df.iterrows():
        h, a = row["home_team"], row["away_team"]
        hs, as_ = int(row["home_score"]), int(row["away_score"])
        outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
        dl = dc.dc_lambdas(model_full, h, a, neutral=bool(row["neutral"]))
        if dl is None:
            continue
        lh, la = dl
        m = dc.score_matrix(lh, la, model_full["rho"])
        n_m = m.shape[0]
        pw = sum(m[i][j] for i in range(n_m) for j in range(n_m) if i > j)
        pd_ = sum(m[i][i] for i in range(n_m))
        pl = 1 - pw - pd_
        rps_vals_full.append(rps([pw, pd_, pl], outcome))

    result = {
        "n_train": len(train_df),
        "n_val": len(val_df),
        "rps_oos_dc_2024": round(np.mean(rps_vals_dc), 4) if rps_vals_dc else None,
        "rps_full_on_2024": round(np.mean(rps_vals_full), 4) if rps_vals_full else None,
        "rps_naive_2024": round(np.mean(rps_vals_naive), 4) if rps_vals_naive else None,
        "overfitting_gap": round(
            (np.mean(rps_vals_dc) - np.mean(rps_vals_full)) if rps_vals_dc and rps_vals_full else 0, 4
        ),
        "interpretation": (
            "Sem overfitting significativo" if abs(
                (np.mean(rps_vals_dc) if rps_vals_dc else 0) -
                (np.mean(rps_vals_full) if rps_vals_full else 0)
            ) < 0.005 else "Possível overfitting — considerar mais regularização"
        )
    }
    return result


def _fit_dc_on_df(df):
    """Ajusta Dixon-Coles num DataFrame de treino genérico."""
    teams = sorted(set(df["home_team"]) | set(df["away_team"]))
    idx = {t: i for i, t in enumerate(teams)}
    h = df["home_team"].map(idx).to_numpy()
    a = df["away_team"].map(idx).to_numpy()
    hs = df["home_score"].to_numpy(float)
    as_ = df["away_score"].to_numpy(float)
    home_flag = (~df["neutral"].to_numpy(bool)).astype(float)
    w = df["weight"].to_numpy(float)
    w = w / w.mean()

    n = len(teams)
    x0 = np.concatenate([[np.log(1.35), 0.25], np.zeros(n), np.zeros(n)])
    res = minimize(dc._nll_grad, x0, args=(n, h, a, hs, as_, home_flag, w),
                   jac=True, method="L-BFGS-B",
                   options={"maxiter": 300, "maxfun": 30000})
    intercept, gamma, att, de = dc._unpack(res.x, n)
    rho = dc._fit_rho(intercept, gamma, att, de, h, a, hs, as_, home_flag, w)
    return {
        "teams": teams, "idx": idx,
        "intercept": float(intercept), "gamma": float(gamma), "rho": rho,
        "attack": {t: float(att[i]) for t, i in idx.items()},
        "defense": {t: float(de[i]) for t, i in idx.items()},
    }


# ──────────────────────────────────────────────────────────────────────────────
# 2. Calibração Detalhada + ECE
# ──────────────────────────────────────────────────────────────────────────────

def calibration_analysis():
    """Reliability diagram com bootstrap CI e ECE para o ensemble e cada componente."""
    print("  [2/5] Calibração detalhada...")
    played = load_played()

    pairs_ens, pairs_elo, pairs_dc, pairs_mkt = [], [], [], []
    for m in played:
        hs, as_ = m["actual"]
        outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
        p = [m["prediction"]["p_home"], m["prediction"]["p_draw"], m["prediction"]["p_away"]]
        elo_p = m["models"]["elo"]["p"]
        dc_p  = m["models"]["dixon_coles"]["p"]
        mkt   = m["models"].get("market")

        for idx in range(3):
            pairs_ens.append((p[idx], 1 if idx == outcome else 0))
            pairs_elo.append((elo_p[idx], 1 if idx == outcome else 0))
            pairs_dc.append((dc_p[idx], 1 if idx == outcome else 0))
            if mkt:
                pairs_mkt.append((mkt["p"][idx], 1 if idx == outcome else 0))

    def reliability_bins(pairs, n_bins=10):
        cp = np.array(pairs)
        bins = []
        for lo in np.arange(0, 1.0, 1 / n_bins):
            hi = lo + 1 / n_bins
            sel = cp[(cp[:, 0] >= lo) & (cp[:, 0] < hi)]
            if len(sel):
                bins.append({
                    "bin": f"{lo:.1f}-{hi:.1f}",
                    "n": int(len(sel)),
                    "pred_mean": round(float(sel[:, 0].mean()), 3),
                    "obs_freq": round(float(sel[:, 1].mean()), 3),
                    "error": round(float(abs(sel[:, 0].mean() - sel[:, 1].mean())), 3),
                })
        return bins

    return {
        "n_games": len(played),
        "ece_ensemble": round(ece(pairs_ens), 4),
        "ece_elo": round(ece(pairs_elo), 4),
        "ece_dc": round(ece(pairs_dc), 4),
        "ece_market": round(ece(pairs_mkt), 4) if pairs_mkt else None,
        "bins_ensemble": reliability_bins(pairs_ens),
        "bins_elo": reliability_bins(pairs_elo),
        "bins_dc": reliability_bins(pairs_dc),
        "bias_direction": (
            "overconfident_favorites" if sum(
                (b["pred_mean"] - b["obs_freq"])
                for b in reliability_bins(pairs_ens)
                if b["pred_mean"] > 0.5
            ) > 0 else "underconfident_favorites"
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# 3. Erro por Faixa de Força (favorito/equilibrado/zebra)
# ──────────────────────────────────────────────────────────────────────────────

def strength_analysis():
    """Analisa RPS e acerto 1X2 por faixa do favorito (p_home vs p_away)."""
    print("  [3/5] Análise por faixa de força...")
    played = load_played()

    buckets = {"zebra": [], "equilibrado": [], "ligeiro_favorito": [], "favorito_claro": []}
    bucket_rps = {k: [] for k in buckets}
    bucket_hits = {k: [] for k in buckets}
    bucket_elo_diff = {k: [] for k in buckets}

    for m in played:
        hs, as_ = m["actual"]
        outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
        p = [m["prediction"]["p_home"], m["prediction"]["p_draw"], m["prediction"]["p_away"]]
        fav_p = max(p[0], p[2])  # probabilidade do favorito (home ou away)
        elo_diff = abs(m["elo_ratings"]["home"] - m["elo_ratings"]["away"])

        if fav_p < 0.45:
            b = "equilibrado"
        elif fav_p < 0.60:
            b = "ligeiro_favorito"
        elif fav_p < 0.75:
            b = "favorito_claro"
        else:
            b = "zebra"  # muito favorito → upset seria zebra

        bucket_rps[b].append(rps(p, outcome))
        bucket_hits[b].append(1 if int(np.argmax(p)) == outcome else 0)
        bucket_elo_diff[b].append(elo_diff)

    result = {}
    for b in buckets:
        n = len(bucket_rps[b])
        result[b] = {
            "n": n,
            "rps_mean": round(float(np.mean(bucket_rps[b])), 4) if n else None,
            "hit_rate": round(float(np.mean(bucket_hits[b])), 4) if n else None,
            "avg_elo_diff": round(float(np.mean(bucket_elo_diff[b])), 1) if n else None,
        }
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 4. Análise do Time-Decay (halflife)
# ──────────────────────────────────────────────────────────────────────────────

def halflife_analysis():
    """Testa halflife [365, 547, 730, 912, 1460] dias no DC e mede RPS nos jogos da Copa."""
    print("  [4/5] Análise de time-decay (halflife)...")
    played = load_played()
    if len(played) < 10:
        return {"error": "poucos jogos para análise"}

    teams_in_played = set()
    for m in played:
        teams_in_played.add(m["home"]); teams_in_played.add(m["away"])

    results = []
    halflives = [365, 547, 730, 912, 1460]

    orig_hl = wc_data.HALFLIFE_DAYS
    for hl in halflives:
        # Monkey-patch temporário
        wc_data.HALFLIFE_DAYS = hl
        try:
            df = wc_data.training_set()
            model = _fit_dc_on_df(df)
        except Exception as e:
            results.append({"halflife_days": hl, "error": str(e)})
            continue
        finally:
            wc_data.HALFLIFE_DAYS = orig_hl

        rps_list = []
        for m in played:
            h, a = m["home"], m["away"]
            dl = dc.dc_lambdas(model, h, a, neutral=True)
            if dl is None:
                continue
            lh, la = dl
            mat = dc.score_matrix(lh, la, model["rho"])
            n_m = mat.shape[0]
            pw = sum(mat[i][j] for i in range(n_m) for j in range(n_m) if i > j)
            pd_ = sum(mat[i][i] for i in range(n_m))
            pl = 1 - pw - pd_
            hs, as_ = m["actual"]
            outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
            rps_list.append(rps([pw, pd_, pl], outcome))

        results.append({
            "halflife_days": hl,
            "halflife_years": round(hl / 365, 1),
            "rps_copa": round(float(np.mean(rps_list)), 4) if rps_list else None,
            "n_evaluated": len(rps_list),
        })

    # Identifica melhor halflife
    valid = [r for r in results if r.get("rps_copa") is not None]
    best = min(valid, key=lambda x: x["rps_copa"]) if valid else None
    return {"results": results, "best_halflife": best}


# ──────────────────────────────────────────────────────────────────────────────
# 5. Análise de Sinergia do Ensemble
# ──────────────────────────────────────────────────────────────────────────────

def ensemble_synergy():
    """Testa cada componente isolado e combinações para quantificar sinergia."""
    print("  [5/5] Sinergia do ensemble...")
    played = load_played()
    if len(played) < 10:
        return {"error": "poucos jogos"}

    models_rps = {
        "naive": [], "elo_only": [], "dc_only": [], "market_only": [],
        "elo_dc": [], "elo_mkt": [], "dc_mkt": [], "ensemble": [],
    }

    for m in played:
        hs, as_ = m["actual"]
        outcome = 0 if hs > as_ else (1 if hs == as_ else 2)
        p_ens = [m["prediction"]["p_home"], m["prediction"]["p_draw"], m["prediction"]["p_away"]]
        p_elo = m["models"]["elo"]["p"]
        p_dc  = m["models"]["dixon_coles"]["p"]
        mkt   = m["models"].get("market")
        p_mkt = mkt["p"] if mkt else None

        def norm3(v):
            s = sum(v); return [x / s for x in v]

        models_rps["naive"].append(rps([1/3, 1/3, 1/3], outcome))
        models_rps["elo_only"].append(rps(p_elo, outcome))
        models_rps["dc_only"].append(rps(p_dc, outcome))
        models_rps["ensemble"].append(rps(p_ens, outcome))

        # Elo + DC (sem mercado)
        elo_dc = norm3([0.35 * p_elo[i] + 0.65 * p_dc[i] for i in range(3)])
        models_rps["elo_dc"].append(rps(elo_dc, outcome))

        if p_mkt:
            models_rps["market_only"].append(rps(p_mkt, outcome))
            # Elo + Market
            elo_mkt = norm3([0.5 * p_elo[i] + 0.5 * p_mkt[i] for i in range(3)])
            models_rps["elo_mkt"].append(rps(elo_mkt, outcome))
            # DC + Market
            dc_mkt = norm3([0.5 * p_dc[i] + 0.5 * p_mkt[i] for i in range(3)])
            models_rps["dc_mkt"].append(rps(dc_mkt, outcome))
        else:
            for k in ("market_only", "elo_mkt", "dc_mkt"):
                models_rps[k].append(None)

    def mean_or_none(lst):
        vals = [v for v in lst if v is not None]
        return round(float(np.mean(vals)), 4) if vals else None

    summary = {k: mean_or_none(v) for k, v in models_rps.items()}
    # Ranking
    ranked = sorted(
        [(k, v) for k, v in summary.items() if v is not None],
        key=lambda x: x[1]
    )
    summary["ranking"] = [{"model": k, "rps": v} for k, v in ranked]
    summary["n_with_market"] = sum(1 for m in played if m["models"].get("market"))
    summary["n_without_market"] = sum(1 for m in played if not m["models"].get("market"))

    return summary


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def run():
    print("[Diagnóstico] Iniciando análise completa...")

    report = {}

    # 1. Cross-validation temporal
    report["temporal_cv"] = temporal_cross_validation()

    # 2. Calibração
    report["calibration"] = calibration_analysis()

    # 3. Força
    report["strength_analysis"] = strength_analysis()

    # 4. Time-decay
    report["halflife_analysis"] = halflife_analysis()

    # 5. Sinergia
    report["ensemble_synergy"] = ensemble_synergy()

    # Salva
    out_path = PROJECT_ROOT / "analysis" / "diagnostics_report.json"
    json.dump(report, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    # Imprime resumo
    print("\n" + "=" * 60)
    print("RESUMO DO DIAGNÓSTICO")
    print("=" * 60)

    cv = report["temporal_cv"]
    print(f"\n[1] Cross-validation temporal:")
    print(f"    RPS OOS (2024+): {cv.get('rps_oos_dc_2024')} | Full: {cv.get('rps_full_on_2024')}")
    print(f"    Gap overfitting: {cv.get('overfitting_gap')} | {cv.get('interpretation','')}")

    cal = report["calibration"]
    print(f"\n[2] Calibração (ECE):")
    print(f"    Ensemble: {cal['ece_ensemble']:.4f} | Elo: {cal['ece_elo']:.4f} | DC: {cal['ece_dc']:.4f}" +
          (f" | Market: {cal['ece_market']:.4f}" if cal.get('ece_market') else ""))
    print(f"    Direção: {cal['bias_direction']}")

    sa = report["strength_analysis"]
    print(f"\n[3] Análise por força:")
    for bucket, vals in sa.items():
        if vals.get("n", 0) > 0:
            print(f"    {bucket:<20} n={vals['n']:>3} | RPS={vals['rps_mean']} | Acerto={vals['hit_rate']:.1%}")

    hl = report["halflife_analysis"]
    if "results" in hl:
        print(f"\n[4] Time-decay (halflife):")
        for r in hl["results"]:
            marker = " << MELHOR" if hl.get("best_halflife", {}).get("halflife_days") == r["halflife_days"] else ""
            print(f"    {r['halflife_years']} anos ({r['halflife_days']}d): RPS={r.get('rps_copa')}{marker}")

    es = report["ensemble_synergy"]
    print(f"\n[5] Sinergia do ensemble (RPS por modelo):")
    for entry in es.get("ranking", []):
        print(f"    {entry['model']:<20} RPS={entry['rps']}")

    print(f"\n[OK] Relatorio salvo em: {out_path}")
    return report


if __name__ == "__main__":
    run()

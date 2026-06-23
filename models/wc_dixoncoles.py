"""
Dixon-Coles ponderado (Ley et al. 2019) — forças de ataque/defesa de seleções
via máxima verossimilhança PONDERADA (recência × importância da competição).

Implementação em 2 estágios (rápida e robusta):
  Estágio 1: Poisson (intercepto + ataque/defesa por time + mando) com GRADIENTE
             ANALÍTICO via L-BFGS-B e regularização ridge (estabiliza times com
             poucos jogos e resolve a indeterminação de translação).
  Estágio 2: ajuste do ρ (correção Dixon-Coles p/ placares baixos) por busca 1-D,
             fixadas as taxas do estágio 1.

λ_casa = exp(intercepto + ataque[casa] - defesa[fora] + mando·[não-neutro])
λ_fora = exp(intercepto + ataque[fora] - defesa[casa])
"""
import sys
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize, minimize_scalar

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wc_data

RIDGE = 2.0  # regularização L2 sobre ataque/defesa


def _prepare(df):
    teams = sorted(set(df["home_team"]) | set(df["away_team"]))
    idx = {t: i for i, t in enumerate(teams)}
    h = df["home_team"].map(idx).to_numpy()
    a = df["away_team"].map(idx).to_numpy()
    hs = df["home_score"].to_numpy(float)
    as_ = df["away_score"].to_numpy(float)
    home_flag = (~df["neutral"].to_numpy(bool)).astype(float)
    w = df["weight"].to_numpy(float)
    w = w / w.mean()  # normaliza p/ escala ~ por jogo
    return teams, idx, h, a, hs, as_, home_flag, w


def _unpack(params, n):
    intercept = params[0]
    gamma = params[1]
    att = params[2:2 + n]
    de = params[2 + n:2 + 2 * n]
    return intercept, gamma, att, de


def _nll_grad(params, n, h, a, hs, as_, home_flag, w):
    """NLL Poisson ponderada + ridge, com gradiente analítico."""
    intercept, gamma, att, de = _unpack(params, n)
    log_lh = intercept + att[h] - de[a] + gamma * home_flag
    log_la = intercept + att[a] - de[h]
    lh = np.exp(log_lh); la = np.exp(log_la)

    ll = w * (hs * log_lh - lh + as_ * log_la - la)
    nll = -ll.sum() + RIDGE * (np.dot(att, att) + np.dot(de, de))

    # resíduos
    rh = w * (hs - lh)   # eq. casa
    ra = w * (as_ - la)  # eq. fora
    g_int = -(rh.sum() + ra.sum())
    g_gam = -(rh * home_flag).sum()
    # ataque[t]: + onde t é casa (eq casa), + onde t é fora (eq fora)
    g_att = -(np.bincount(h, rh, n) + np.bincount(a, ra, n)) + 2 * RIDGE * att
    # defesa[t]: -def_away na eq casa (t=fora) e -def_home na eq fora (t=casa)
    g_de = (np.bincount(a, rh, n) + np.bincount(h, ra, n)) + 2 * RIDGE * de
    grad = np.concatenate([[g_int, g_gam], g_att, g_de])
    return nll, grad


def _fit_rho(intercept, gamma, att, de, h, a, hs, as_, home_flag, w):
    """Ajusta ρ maximizando a verossimilhança DC (correção dos placares baixos)."""
    log_lh = intercept + att[h] - de[a] + gamma * home_flag
    log_la = intercept + att[a] - de[h]
    lh = np.exp(log_lh); la = np.exp(log_la)
    m00 = (hs == 0) & (as_ == 0); m10 = (hs == 1) & (as_ == 0)
    m01 = (hs == 0) & (as_ == 1); m11 = (hs == 1) & (as_ == 1)

    def neg_ll(rho):
        tau = np.ones_like(lh)
        tau[m00] = 1 - lh[m00] * la[m00] * rho
        tau[m01] = 1 + lh[m01] * rho
        tau[m10] = 1 + la[m10] * rho
        tau[m11] = 1 - rho
        if np.any(tau <= 0):
            return 1e9
        return -(w * np.log(tau)).sum()

    res = minimize_scalar(neg_ll, bounds=(-0.2, 0.2), method="bounded")
    return float(res.x)


def fit(ref_date: str = "2026-06-10"):
    df = wc_data.training_set(ref_date=ref_date)
    teams, idx, h, a, hs, as_, home_flag, w = _prepare(df)
    n = len(teams)

    x0 = np.concatenate([[np.log(1.35), 0.25], np.zeros(n), np.zeros(n)])
    res = minimize(_nll_grad, x0, args=(n, h, a, hs, as_, home_flag, w),
                   jac=True, method="L-BFGS-B",
                   options={"maxiter": 500, "maxfun": 50000})
    intercept, gamma, att, de = _unpack(res.x, n)
    rho = _fit_rho(intercept, gamma, att, de, h, a, hs, as_, home_flag, w)

    return {
        "teams": teams, "idx": idx,
        "intercept": float(intercept), "gamma": float(gamma), "rho": rho,
        "attack": {t: float(att[i]) for t, i in idx.items()},
        "defense": {t: float(de[i]) for t, i in idx.items()},
        "converged": bool(res.success), "n_train": int(len(df)),
    }


def dc_lambdas(model, home, away, neutral=True):
    att = model["attack"]; de = model["defense"]
    if home not in att or away not in att:
        return None
    g = 0.0 if neutral else model["gamma"]
    lam_h = np.exp(model["intercept"] + att[home] - de[away] + g)
    lam_a = np.exp(model["intercept"] + att[away] - de[home])
    return float(lam_h), float(lam_a)


def score_matrix(lam_h, lam_a, rho=0.0, max_goals=10):
    """Matriz de placar com correção Dixon-Coles nas células baixas."""
    from scipy.stats import poisson
    ph = poisson.pmf(np.arange(max_goals + 1), lam_h)
    pa = poisson.pmf(np.arange(max_goals + 1), lam_a)
    m = np.outer(ph, pa)
    m[0, 0] *= 1 - lam_h * lam_a * rho
    m[0, 1] *= 1 + lam_h * rho
    m[1, 0] *= 1 + lam_a * rho
    m[1, 1] *= 1 - rho
    m = np.clip(m, 0, None)
    return m / m.sum()


if __name__ == "__main__":
    import time
    t0 = time.time()
    model = fit()
    dt = time.time() - t0
    print(f"Fit em {dt:.1f}s | convergiu={model['converged']} | n_train={model['n_train']} | "
          f"times={len(model['teams'])}")
    print(f"intercepto={model['intercept']:.3f} mando(gamma)={model['gamma']:.3f} rho={model['rho']:.3f}")
    # ranking por força líquida = ataque + defesa (ambos: maior = melhor)
    teams = wc_data.real_teams()
    strength = sorted(((t, model["attack"][t] + model["defense"][t]) for t in teams if t in model["attack"]),
                      key=lambda x: x[1], reverse=True)
    print("\nTop 12 por força líquida (ataque + defesa):")
    for i, (t, s) in enumerate(strength[:12], 1):
        print(f"  {i:>2}. {t:<16} {s:+.2f}  (att {model['attack'][t]:+.2f} / def {model['defense'][t]:+.2f})")
    lh, la = dc_lambdas(model, "Brazil", "Scotland", neutral=True)
    print(f"\nBrasil vs Escócia (neutro): xG Brasil={lh:.2f}  Escócia={la:.2f}")
    m = score_matrix(lh, la, model["rho"])
    n = m.shape[0]
    pw = sum(m[i][j] for i in range(n) for j in range(n) if i > j)
    pd_ = sum(m[i][i] for i in range(n))
    print(f"  P(Brasil vence)={pw:.1%}  P(empate)={pd_:.1%}  P(Escócia)={1-pw-pd_:.1%}")
    json.dump({k: model[k] for k in ("intercept", "gamma", "rho", "attack", "defense")},
              open(wc_data.PROJECT_ROOT / "analysis" / "dixoncoles_model.json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

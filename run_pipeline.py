"""
Pipeline completo da Copa 2026 — execute para ATUALIZAR tudo conforme saem os resultados.

Passos:
  0. Coleta resultados atualizados da Copa (openfootball — grátis, sem chave)
  1. Ratings Elo de todas as seleções            -> analysis/elo_ratings.json
  2. Dixon-Coles ponderado (ataque/defesa)        -> analysis/dixoncoles_model.json
  3. Ensemble + previsão de todos os jogos        -> analysis/wc2026_predictions.json
  4. Backtest e métricas de acurácia              -> analysis/wc2026_backtest.json
  5. Dashboard visual                             -> output/index.html

Uso:  python run_pipeline.py
      python run_pipeline.py --no-collect   (pula a coleta, só re-modela)
"""
import os
import sys
import subprocess
from pathlib import Path

# Console do Windows usa cp1252 — força UTF-8 para não quebrar em acentos/símbolos.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
PY = sys.executable
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

STEPS = [
    ("Coleta resultados Copa 2026", ROOT / "data" / "collectors" / "openfootball.py"),
    ("Ratings Elo", ROOT / "models" / "wc_elo.py"),
    ("Dixon-Coles", ROOT / "models" / "wc_dixoncoles.py"),
    ("Ensemble + previsões", ROOT / "models" / "wc_predict.py"),
    ("Backtest / acurácia", ROOT / "models" / "wc_backtest.py"),
    ("Dashboard index.html", ROOT / "output" / "build_dashboard.py"),
]


def main():
    steps = STEPS[1:] if "--no-collect" in sys.argv else STEPS
    for i, (label, script) in enumerate(steps, 1):
        print(f"\n{'='*60}\n[{i}/{len(steps)}] {label}\n{'='*60}")
        r = subprocess.run([PY, str(script)], env=ENV, cwd=str(ROOT))
        if r.returncode != 0:
            print(f"!! Falhou em '{label}' (exit {r.returncode}). Abortando.")
            sys.exit(r.returncode)
    print(f"\n✓ Pipeline concluído. Abra output/index.html no navegador.")


if __name__ == "__main__":
    main()

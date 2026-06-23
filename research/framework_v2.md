# Framework v2 — Motor Preditivo com Dados Reais (todas as seleções)

> Substitui os parâmetros estimados manualmente do framework v1 (`models/ensemble.py`)
> por modelos **treinados em dados reais**, cobrindo **todas as 48 seleções** da Copa 2026,
> com **backtest** e **painel visual**. Baseado em pesquisa da literatura (jun/2026).

## 1. Métodos escolhidos (e por quê)

A literatura para previsão de **seleções** converge para um ensemble de força estatística
com decaimento temporal + sabedoria de mercado. Referências que guiaram o design:

| Método | Papel no framework | Referência |
|---|---|---|
| **Poisson/Dixon-Coles ponderado** | Núcleo: ataque/defesa por seleção, peso por recência × importância | Ley, Van de Wiele & Van Eetvelde (2019); Dixon & Coles (1997) |
| **Elo de seleções** | Força histórica de longo prazo, calibrada p/ gols | World Football Elo; Hvattum & Arntzen (2010) |
| **Mercado (odds sem vig)** | "Wisdom of crowds" + info não modelável (jogos futuros) | Forrest et al. (2005) |
| **Ensemble** | Combinação supera componentes isolados | Groll et al. (2019); meta-análises |

**Avaliação:** **RPS (Ranked Probability Score)** como métrica primária — padrão científico,
sensível à ordem casa→empate→fora (Constantinou & Fenton 2012). Log-loss como secundária,
reliability diagram para calibração. Backtest **temporal sem leakage**.

## 2. O que conseguimos replicar com os dados que temos

| Modelo | Replicável? | Como / dados |
|---|---|---|
| Elo de seleções | ✅ | `results.csv` (49k jogos 1872-2026); fórmula World Football Elo (K por torneio, multiplicador de gols, campo neutro) |
| Dixon-Coles ponderado | ✅ | MLE em jogos recentes (2015-2026) com peso recência×importância; ρ p/ placares baixos |
| Mercado sem vig | ✅ | 31 jogos com odds (The Odds API); normalização multiplicativa |
| Priors de xG | ⚠️ parcial | StatsBomb cobre só Copas 2018/2022 (não usado no v2 inicial; disponível p/ evoluir) |
| ML / Random Forest híbrido | ⚠️ | exigiria features extras (valor de mercado, etc.); fora do escopo v2 |

## 3. Pipeline (arquivos)

```
data/collectors/openfootball.py   → resultados atualizados da Copa 2026
models/wc_data.py                 → carga + normalização de nomes + pesos de treino
models/wc_elo.py                  → Elo de todas as seleções + calibração Elo→gols
models/wc_dixoncoles.py           → Dixon-Coles ponderado (MLE, 2 estágios)
models/wc_predict.py              → ensemble + previsão dos 72 jogos de grupo
models/wc_backtest.py             → RPS, acerto 1X2, placar, calibração
output/build_dashboard.py         → index.html self-contained
run_pipeline.py                   → roda tudo de uma vez (atualização)
```

**Sem leakage:** jogos já disputados são previstos com o Elo de *antes* da partida;
o Dixon-Coles é treinado só com dados **anteriores** ao torneio (≤ 2026-06-10, sem a Copa 2026).

## 4. Resultados do backtest (41 jogos de grupo já disputados)

| Métrica | Valor | Referência |
|---|---|---|
| **RPS médio (ensemble)** | **0.171** | bom ≈ 0.18-0.21; ingênuo ≈ 0.22; bate mercado < 0.19 |
| Acerto 1X2 | 56% | — |
| Acerto de placar exato | ~5-7% | naturalmente baixo |
| Log-loss | 0.94 | secundária |
| Baselines | Elo 0.184 · DC 0.167 · ingênuo 0.225 | DC é o componente mais forte |

O ensemble (0.171) está em território de "bate o mercado" e é mais robusto que qualquer
componente isolado para jogos futuros (onde o mercado entra) e mata-mata.

## 5. Ranking de força gerado (top 6 por Elo)

Argentina · Espanha · França · Inglaterra · Colômbia · Brasil — coerente com o consenso real.

## 6. Como atualizar conforme os resultados

```bash
python run_pipeline.py              # coleta + re-modela + regenera o painel
python run_pipeline.py --no-collect # só re-modela (sem nova coleta)
```
Depois, abra `output/index.html`. À medida que os grupos terminam, os times do mata-mata
deixam de ser placeholders e passam a ser previstos automaticamente.

## 7. Limitações / próximos passos

- **xG (StatsBomb)** ainda não integrado como prior — evolução natural p/ regularizar
  seleções com poucos jogos recentes.
- **Pesos do ensemble** foram ajustados de forma conservadora; poderiam ser otimizados por
  validação temporal (cuidado com overfitting nos ~41 jogos).
- **Mata-mata**: previsto só quando os confrontos estiverem definidos.
- **Sem fatores contextuais ao vivo** (lesões/escalações) no v2 — o mercado os captura indiretamente.

# Copa do Mundo 2026 — Agente Preditivo

## Objetivo
Framework multi-metodológico para predição de **todos os jogos da Copa do Mundo 2026** (48 seleções),
combinando modelos estatísticos treinados em dados reais, mercado de apostas e backtest contínuo,
com **painel visual** (`output/index.html`) que mostra previsões, resultados e acurácia.
> Origem: começou como predição de um único jogo do Brasil (v1); evoluiu para o motor v2 (todas as seleções).

## Estrutura do Projeto

```
Copa agente/
├── CLAUDE.md               # Este arquivo
├── research/               # Literatura científica e frameworks de referência
│   ├── models_review.md    # Revisão dos modelos preditivos
│   ├── data_sources.md     # Fontes de dados identificadas
│   └── framework_design.md # Design do ensemble framework
├── data/                   # Dados coletados
│   ├── brazil_stats.json   # Estatísticas do Brasil
│   ├── opponent_stats.json # Estatísticas do adversário
│   ├── lineups.json        # Escalações
│   └── historical.json     # Dados históricos relevantes
├── models/                 # Implementação dos modelos
│   ├── poisson_model.py
│   ├── elo_model.py
│   ├── bayesian_model.py
│   ├── xg_model.py
│   └── ensemble.py
├── analysis/               # Análise e resultados
│   ├── match_analysis.md   # Análise textual completa
│   └── predictions.json    # Resultados numéricos de cada modelo
└── output/                 # Apresentação final
    └── final_report.md
```

## Fase 1 — Pesquisa (CONCLUÍDA)
- [x] Revisão de modelos preditivos científicos → `research/models_review.md`
- [x] Identificação de fontes de dados abertas → `research/framework_design.md`
- [x] Coleta de dados do jogo de hoje → `data/match_data.json`

## Fase 2 — Framework Design (CONCLUÍDA)
- [x] Definir arquitetura do ensemble → `research/framework_design.md`
- [x] Implementar modelos base → `models/*.py`
- [x] Calibração e ponderação → `models/ensemble.py`

## Fase 3 — Análise (CONCLUÍDA)
- [x] Executar todos os modelos → `analysis/predictions.json`
- [x] Gerar predição com intervalos de confiança → `analysis/match_analysis.md`
- [x] Análise qualitativa complementar → `analysis/match_analysis.md`

## Fase 4 — Apresentação (CONCLUÍDA)
- [x] Relatório final com metodologia e resultados → `output/final_report.md`

## v1 — RESULTADO (jogo único, arquivado)
**Predição v1: Brasil 2 × 0 Haiti** (14.84%) | **Resultado real: Brasil 3 × 0 Haiti**
(o 3-0 estava no top-5 previsto e no conjunto de 80% de confiança; direção correta).

## Framework v2 — Motor de dados reais (todas as seleções) [ATUAL]
Pipeline que prevê **todos os jogos** da Copa, com backtest e painel. Ver `research/framework_v2.md`.

**Como atualizar tudo (conforme saem resultados):**
```
python run_pipeline.py              # coleta + Elo + Dixon-Coles + ensemble + backtest + dashboard
python run_pipeline.py --no-collect # só re-modela
```
Depois abra `output/index.html`.

**Arquivos do v2:**
- `models/wc_data.py` — carga, normalização de nomes, pesos de treino
- `models/wc_elo.py` — Elo de seleções + calibração Elo→gols
- `models/wc_dixoncoles.py` — Dixon-Coles ponderado (MLE)
- `models/wc_predict.py` — ensemble + previsões → `analysis/wc2026_predictions.json`
- `models/wc_backtest.py` — RPS/acerto/calibração → `analysis/wc2026_backtest.json`
- `output/build_dashboard.py` → `output/index.html`
- `data/collectors/` — coletores (openfootball, kaggle, api_football, odds, newsdata, statsbomb)

**Resultado atual (41 jogos de grupo disputados):** RPS **0.171** · acerto 1X2 **56%** · (bom modelo ≈ 0.18-0.21).
**Métrica de avaliação:** RPS (padrão científico; Constantinou & Fenton 2012).

## Contexto Técnico
- **Escopo**: Copa do Mundo 2026 — todas as 48 seleções (fase de grupos prevista; mata-mata conforme definido)
- **Data atual**: 22/06/2026
- **Língua**: Português (BR)

## Metodologias Alvo
1. **Dixon-Coles** — Poisson bivariado com correção para placares baixos
2. **Elo adaptado** — Rating de força relativa entre seleções
3. **xG-based** — Predição baseada em Expected Goals histórico
4. **Bayesian hierarchical** — Inferência bayesiana com priors de performance
5. **ML Ensemble** — XGBoost/Random Forest em features agregadas
6. **Mercado de apostas** — Odds como wisdom of crowds calibrado

## Notas de Execução
- Priorizar dados da Copa 2026 + últimos 12 meses de qualificatórias
- Rankear FIFA como baseline de força
- Considerar fadiga (dias desde último jogo), altitude, temperatura
- Escalação tem impacto estimado de 15-25% no resultado esperado

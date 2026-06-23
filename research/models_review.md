# Revisão de Modelos Preditivos — Estado da Arte

## Sumário Executivo

Com base em pesquisa bibliográfica sistemática, os modelos mais eficazes para predição de resultados de futebol em 2024-2026 são:

1. **CatBoost + Pi-Ratings** — melhor performance ML documentada (55.82% acurácia)
2. **Dixon-Coles com xG como input** — melhor modelo estatístico gerativo
3. **Ensemble (combinação de modelos)** — sempre supera modelos individuais na meta-análise
4. **Mercado de apostas calibrado** — melhor benchmark para probabilidades 1X2

---

## 1. Modelos Estatísticos Clássicos

### 1.1 Poisson Bivariado Independente (Maher, 1982)
- **Mecanismo**: Modela gols de cada time como variáveis Poisson independentes
- **Features**: Força de ataque e defesa de cada time (estimadas por máxima verossimilhança)
- **Limitação principal**: Subestima probabilidade de placares baixos (0-0, 1-1) devido à correlação negativa entre gols das equipes
- **Acurácia**: Baseline — superado por quase todos os modelos subsequentes

### 1.2 Dixon-Coles (1997) — Gold Standard Estatístico
- **Mecanismo**: Poisson bivariado + correção ρ para dependência em placares baixos + time-weighting
- **Formula de correção**: τ(x,y,λ,μ,ρ) modificador para (0,0), (1,0), (0,1), (1,1)
- **Features**: Ataque/defesa por time + vantagem de jogar em casa + tempo (jogos recentes têm mais peso)
- **Acurácia**: ~15% superior ao Poisson simples (Premier League 2018-19)
- **Melhor uso**: Distribuição de placares, over/under, handicap asiático

### 1.3 Negative Binomial com Zero-Inflated (recente)
- **Uso**: Captura overdispersion — alguns times marcam 0 mais do que Poisson prevê
- **Aplicação Copa 2026**: Útil para times como Haiti, que têm probabilidade alta de 0 gols
- **Performance**: Ligeiramente superior ao Poisson puro em torneios com jogos desequilibrados

---

## 2. Machine Learning

### 2.1 CatBoost + Pi-Ratings — Melhor Performance (2024-2026)
- **Acurácia**: 55.82% em predição 1X2 (referência: R-bloggers World Cup 2026)
- **Features principais**: Pi-ratings de ataque/defesa + forma recente + contexto de jogo
- **Vantagem**: Trata naturalmente variáveis categóricas; robusto a overfitting
- **Pi-Ratings (Constantinou & Fenton)**: Variante do Elo que decompõe força em ataque e defesa separados

### 2.2 XGBoost
- **Acurácia**: 52.43% (mesmas condições do CatBoost)
- **Features**: Similar ao CatBoost; melhor quando há muitas features numéricas
- **Uso**: Amplamente adotado em competições de predição esportiva (Kaggle, etc.)

### 2.3 Random Forest
- **Acurácia**: 52-58% (varia por conjunto de dados)
- **Vantagem**: Interpretabilidade via Gini importance, robusto a outliers
- **Uso ideal**: Validação cruzada e importância de variáveis

### 2.4 MLP Neural Network (Frontiers in Sports, 2025)
- **Acurácia**: 86.7% com arquitetura 24-4-3 em Copa do Mundo
- **Features**: Exclusivamente indicadores técnicos de Copas anteriores
- **Nota de cautela**: Acurácia alta pode refletir conjunto de teste específico ou features com vazamento

### 2.5 FootballNet CNN (2024)
- **Mecanismo**: CNN especializada para análise de sequências de eventos de jogo
- **Aplicação**: Predição em tempo real (live betting), mais do que pré-jogo

---

## 3. Modelos de Rating

### 3.1 Elo Clássico
- **Mecanismo**: Rating atualizado após cada jogo: R_new = R_old + K × (Score - E_Score)
- **Limitações**: Atualização lenta; não distingue ataque de defesa; insensível a margem de gols
- **Performance em Copa**: Bom para 1X2, fraco para número de gols

### 3.2 Pi-Ratings (Constantinou & Fenton, 2012)
- **Mecanismo**: Elo separado para ataque (π+) e defesa (π-)
- **Atualização**: Baseada em gols marcados e sofridos, com decay temporal
- **Performance**: Melhor que Elo simples em 12% dos casos
- **Melhor combinação**: CatBoost + Pi-Ratings → 55.82% (estado da arte)

### 3.3 SPI — Soccer Power Index (FiveThirtyEight)
- **Mecanismo**: Inclui dados de jogadores individuais além de resultados
- **Performance**: Supera Elo simples consistentemente em ligas com dados de jogadores
- **Limitação**: Dados de jogadores individuais difíceis de obter para Copa do Mundo

### 3.4 Ranking FIFA Oficial
- **Uso no framework**: Baseline de força, mas atualização lenta (mensal)
- **Performance preditiva**: Inferior ao Elo e Pi-Ratings (metodologia controversa)

---

## 4. Expected Goals (xG) — Variável Mais Importante

### 4.1 xG Clássico Logístico
- **Features por ordem de importância** (SHAP values, múltiplos estudos):
  1. Distância ao gol (dominante)
  2. Ângulo ao gol
  3. Parte do corpo (cabeça: 10-12% conversão vs. pé: 8-10%)
  4. Situação de jogo (open play vs. corner vs. free kick)
  5. Pressão do marcador
- **Modelos usados**: Regressão logística, XGBoost, redes neurais
- **Poder preditivo**: Mais estável que gols reais em pequenas amostras (Copa = 3-7 jogos)

### 4.2 xG Sequencial (PMC, 2024)
- **Inovação**: Incorpora sequência de ações antes do chute (passes, progressões, pressões)
- **Melhoria**: ~8% superior ao xG clássico em termos de log-loss
- **Features temporais**: Localização do passe anterior, velocidade da jogada

### 4.3 xG como Input para Poisson
- **Ref**: PLOS ONE 2023 — "xG predictions improve upon goals as inputs"
- **Insight**: Substituir gols observados por xG nos modelos Poisson reduz variância e melhora predições
- **Calibração**: 70% xG + 30% gols reais é a combinação ótima (Mead et al.)

---

## 5. Meta-Análises

### 5.1 Estudo com 11 Modelos — World Cup 2026 (Towards Data Science)
- **Modelos testados**: 3 ratings (Elo, Colley, PageRank) + 2 geradores (Poisson, NegBin) + 5 ML (logistic, KNN, RF, XGBoost, MLP)
- **Resultado chave**: 4 campeões diferentes entre os 11 modelos → ensemble é necessário
- **Lição**: Nenhum modelo individual é dominante em todos os cenários

### 5.2 Machine Learning Survey (arXiv 2403.07669)
- **Conclusão**: Ensemble methods superam modelos individuais de forma consistente
- **Melhor feature**: Rating histórico do time (Elo/Pi)
- **Segunda melhor feature**: xG recente

### 5.3 Hybrid ML Forecasts para UEFA EURO 2020 (arXiv)
- **Metodologia**: Combina modelos de rating com ML + calibração por mercado
- **Conclusão**: "Combined forecasts beat their components on average"
- **Aplicação ao nosso caso**: Justifica o ensemble ponderado adotado

### 5.4 Simple Models vs. Betting Odds (Sagepub, 2026)
- **Pergunta**: Modelos simples superam o mercado de apostas?
- **Resultado**: Não consistentemente — mercado é eficiente para probabilidades 1X2
- **Implicação**: Mercado tem peso alto (28%) no nosso ensemble

---

## 6. Fatores Contextuais — Impacto Quantificado

| Fator | Magnitude | Evidência |
|-------|-----------|-----------|
| Vantagem de jogar em casa | +0.3 gols esperados, +10% P(win) | Dixon-Coles (1997), extensamente replicado |
| Campo neutro (Copa do Mundo) | 0 (sem vantagem de casa) | FIFA World Cup historical data |
| Jogador chave ausente (top scorer) | -8 a -15% gols esperados | Schumacher et al. (2020) |
| Forma recente (últimas 5 jogos) | ±5-10% xG esperado | Pi-Ratings calibration |
| Fadiga (jogo em 4 dias) | -5% volume de jogo | Carling et al. (2012) |
| Altitude (>2000m) | +20% para adaptados, -20% visitante | FIFA altitude studies |
| Temperatura extrema (>30°C) | -5% gols totais | CRY sport science |
| Motivação (jogo decisivo) | +5-8% intensidade | Literature inconsistente |
| H2H histórico | Fraco preditor isolado | Forrest et al. (2005) |

---

## 7. Calibração para Jogos Muito Desequilibrados

Uma particularidade de Brasil × Haiti é o grau extremo de desequilíbrio. A literatura sugere:

1. **Jogos com rating difference >400 pontos Elo**: Modelos Poisson subestimam gols do favorito
2. **Correção sugerida**: Usar distribuição Negative Binomial ou Zero-Inflated Poisson para o time fraco
3. **Problema de degradação de performance dos modelos ML**: Treinados principalmente em jogos equilibrados, podem subestimar assimetrias extremas

**Nossa solução**: Ancorar no mercado (que processa jogos desequilibrados melhor) e dar peso adicional ao modelo xG (mais robusto a extrapolação).

---

## 8. Conclusões para o Framework

| Prioridade | Ação |
|-----------|------|
| Alta | Usar mercado de apostas como âncora de probabilidade 1X2 |
| Alta | xG como input principal para gols esperados |
| Alta | Dixon-Coles para distribuição de placar |
| Média | Elo/Pi-Ratings para validação cruzada |
| Média | Bayesiano para quantificar incerteza |
| Baixa | ML puro (dados insuficientes da Copa 2026) |

**Pesos finais do ensemble:**
- Mercado calibrado: 28%
- Bayesiano hierárquico: 25%
- xG-based Poisson: 22%
- Dixon-Coles: 15%
- Elo adaptado: 10%

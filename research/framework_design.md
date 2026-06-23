# Framework de Predição — Design Arquitetural

## Princípio Fundamental: Ensemble Ponderado por Evidência

O framework combina múltiplas famílias de modelos, cada uma capturando um aspecto diferente do fenômeno. A predição final é uma média ponderada onde os pesos refletem a acurácia empírica de cada classe de modelo (baseada na literatura).

---

## Camada 1 — Modelos Base (Independentes)

### 1.1 Modelo de Força Relativa (Elo / Pi-Rating)
**Base teórica**: Elo original (Elo, 1978) adaptado por Hvattum & Arntzen (2010)
**O que calcula**: Probabilidade de vitória/empate/derrota baseada em ratings históricos
**Inputs**:
- Rating Elo atual do Brasil
- Rating Elo atual do adversário
- Fator de local (Copa Mundo = neutro ou semi-neutro)
- K-factor calibrado para torneios internacionais

**Fórmula**:
```
E_A = 1 / (1 + 10^((R_B - R_A)/400))
P(Brasil vence) = f(E_A, home_advantage, momentum)
```

**Output**: P(W), P(D), P(L)

---

### 1.2 Modelo de Poisson Bivariado (Dixon-Coles Adaptado)
**Base teórica**: Dixon & Coles (1997), Karlis & Ntzoufras (2003)
**O que calcula**: Distribuição de probabilidade sobre todos os placares possíveis
**Inputs**:
- Taxa de ataque histórica (gols/jogo nos últimos 10 jogos, ponderada por recência)
- Taxa de defesa histórica do adversário
- Parâmetro de correlação ρ (corrige sub-probabilidade de 0-0 e 1-1)
- Fator de força contextual (Copa do Mundo vs amistoso)

**Fórmula**:
```
λ = α_att(Brasil) × β_def(Adv) × γ (home advantage)
μ = α_att(Adv) × β_def(Brasil) × γ⁻¹

P(X=x, Y=y) = τ(x,y,λ,μ,ρ) × Poisson(x|λ) × Poisson(y|μ)
```

**Output**: Distribuição completa de placares, P(W/D/L), gols esperados

---

### 1.3 Modelo Bayesiano Hierárquico
**Base teórica**: Baio & Blangiardo (2010), Rue & Salvesen (2000)
**O que calcula**: Força latente de ataque/defesa com incerteza explícita
**Inputs**:
- Série histórica de gols marcados/sofridos
- Prior baseado em desempenho em fases anteriores da Copa
- Covariáveis: ausências por lesão, jogadores em forma

**Estrutura**:
```
y_j ~ Poisson(θ_j)
log(θ_j) = home + att[team_j] - def[opp_j]
att[k] ~ Normal(μ_att, σ_att)
def[k] ~ Normal(μ_def, σ_def)
```

**Output**: Distribuição posterior sobre gols, intervalos de credibilidade 80/95%

---

### 1.4 Modelo de Expected Goals (xG)
**Base teórica**: Rathke (2017), Spearman et al. (2018)
**O que calcula**: Probabilidade de gol corrigida pela qualidade das chances
**Inputs**:
- xG médio por jogo na Copa 2026
- xGA (xG Against) médio do adversário
- Diferença entre xG e gols reais (luck adjustment)
- Mapa de zonas de finalização preferidas

**Lógica**:
```
xG_Brasil_esperado = média(xG_últimos_3_jogos) × fator_adversário_defesa
xG_Adv_esperado = média(xG_adv_últimos_3) × fator_Brasil_defesa

P(gol | xG) via conversão histórica por faixa de xG
```

**Output**: xG esperado para cada time → distribuição de gols

---

### 1.5 Modelo de Mercado (Wisdom of Crowds Calibrado)
**Base teórica**: Forrest et al. (2005), Spann & Skiera (2009)
**O que calcula**: Probabilidade implícita do mercado, ajustada para margem da casa
**Inputs**:
- Odds de múltiplas casas (Bet365, Pinnacle, etc.)
- Remoção da vig (margem da casa)
- Calibração: mercado tende a subestimar azarões em Copas

**Fórmula**:
```
P_implícita = (1/odd) / Σ(1/odd_i)  # Remove margem
P_calibrada = f(P_implícita, tournament_stage, public_bias)
```

**Output**: P(W/D/L) e linha de gols esperada

---

## Camada 2 — Fatores Contextuais (Modificadores)

Fatores que ajustam os outputs dos modelos base, com magnitude estimada pela literatura:

| Fator | Impacto estimado | Direção |
|-------|------------------|---------|
| Jogador chave lesionado/suspenso | ±8-15% gols esperados | Depende do player |
| Forma recente (últimos 5 jogos) | ±5-10% | Momentum |
| Dias de descanso (>4 dias = vantagem) | ±3-5% | Fadiga física |
| Altitude (>2000m) | ±10-20% gols | Desfavorece visitante não adaptado |
| Temperatura extrema (>30°C) | ±5% | Reduz volume de jogo |
| Fase do torneio | ±5% | Mata-mata = mais cauteloso |
| Motivação/pressão | Qualitativo | Avaliação subjetiva |

---

## Camada 3 — Ensemble e Agregação

### Pesos Iniciais (baseados em literatura de comparação de modelos)

| Modelo | Peso Base | Justificativa |
|--------|-----------|---------------|
| Mercado (Odds calibradas) | 30% | Melhor acurácia empírica agregada |
| Bayesiano Hierárquico | 25% | Captura incerteza estrutural |
| Dixon-Coles Poisson | 20% | Robusto para distribuição de gols |
| xG Model | 15% | Capta qualidade, não apenas volume |
| Elo/Pi-Rating | 10% | Bom para 1X2, fraco para gols |

### Método de Combinação

```
P_final(placar) = Σ w_i × P_i(placar) × adj_contextual

Gols_esperados_Brasil = Σ w_i × λ_i × Π(fator_contextual_j)
Gols_esperados_Adv    = Σ w_i × μ_i × Π(fator_contextual_j)
```

### Saída Final

1. **Placar mais provável** (máximo da distribuição conjunta)
2. **Placar esperado** (média ponderada)
3. **Top-5 placares** com probabilidades individuais
4. **P(Brasil vence)**, **P(Empate)**, **P(Adversário vence)**
5. **Intervalo de confiança 80%** para gols de cada time
6. **Análise de sensibilidade**: o que muda se jogador X não joga

---

## Métricas de Validação (Ex-post)

Para calibrar confiança do modelo:
- Brier Score dos sub-modelos em Copas anteriores
- Log-loss calibration
- RPS (Ranked Probability Score) — padrão em predição esportiva

---

## Limitações Explícitas

1. **Amostra pequena**: Copa do Mundo tem apenas 3-7 jogos por time → alta variância
2. **Eventos aleatórios**: pênaltis, expulsões, gols de cabeça em escanteio
3. **Dados de Copa 2026 limitados**: se ainda nas fases iniciais, poucos jogos observados
4. **Mudanças táticas**: técnico pode surpreender com formação diferente
5. **Fator psicológico**: pressão, torcida, narrativa — difícil quantificar

---

## Roadmap de Implementação

```
[✓] Design do framework
[ ] Coleta de dados (agentes em execução)
[ ] Implementação modelos base (Python)
[ ] Calibração com dados disponíveis
[ ] Execução do ensemble
[ ] Análise de sensibilidade
[ ] Relatório final
```

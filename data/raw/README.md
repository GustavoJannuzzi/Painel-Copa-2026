# Dados Coletados — Índice

Coleta executada em **26/06/2026** pelos scripts em [`data/collectors/`](../collectors).
Para recoletar tudo: `python data/collectors/collect_all.py`
Chaves de API ficam em `.env` (raiz do projeto, não versionado).

---

## ✅ O que cada fonte entregou

### `openfootball/worldcup_2026.json` 🟢 (sem chave) — **a mais valiosa para 2026**
- **104 jogos** da Copa 2026 (11/06 → final 19/07), com placares dos já disputados + **goleadores com minuto**.
- Resultados reais do Brasil: **1×1 Marrocos** (13/06), **3×0 Haiti** (19/06), **0×3 Escócia** (24/06) — Brasil 1º do Grupo C, joga Round of 32 em 29/06 vs 2º do Grupo F (Japão).
- **60 jogos disputados** (grupos A–F completos + grupos G/H/I com 2 rodadas; grupos J/K/L com 2 rodadas). Faltam 12 jogos da fase de grupos (26–27/06).
- Refrescar: `python data/collectors/openfootball.py`

### `kaggle/` 🟡 (conta Kaggle — token KGAT funcionou) — histórico
- `results.csv` — **49.477 jogos de seleções (1872→2026)**, inclui o calendário da Copa 2026. 1.062 jogos do Brasil.
- `goalscorers.csv` — 47.690 gols com minuto/autor. `shootouts.csv` — disputas de pênaltis. `former_names.csv`.
- Base ideal para Elo, Poisson e ratings de força. Refrescar: `python data/collectors/kaggle_data.py`

### `odds_api/odds_soccer_fifa_world_cup.json` 🟡 (chave) — **mercado, Copa 2026 AO VIVO**
- **31 jogos** da Copa 2026 com odds reais (h2h 1X2 + totais), várias casas (US/EU).
- Ex.: próximo jogo do Brasil → **Escócia 8.0 | Empate 5.1 | Brasil 1.33**.
- Também `odds_soccer_brazil_serie_b.json` e `sports.json` (14 competições de futebol ativas).
- Custo: ~4 créditos/competição de 500/mês. Refrescar: `python data/collectors/odds_api.py`

### `api_football/` 🟡 (chave) — eventos granulares **da Copa 2022** (free não libera 2026)
- ⚠️ **Free tier só dá temporadas 2022–2024.** Para 2026 retorna erro de plano.
- Coletado da Copa **2022**: 5 jogos do Brasil + detalhe de Croácia×Brasil:
  - `fixtures_events.json` — timeline (Goal/Card/subst; **faltas individuais NÃO vêm no free**).
  - `fixtures_statistics.json` — **faltas, escanteios, posse, finalizações por time** (ex.: Brasil 24 faltas, 7 escanteios, 49% posse, 21 finalizações).
  - `fixtures_lineups.json` — escalações e formações.
- Útil para **calibrar modelos** com eventos reais. Refrescar: `python data/collectors/api_football.py`

### `statsbomb/` 🟢 (sem chave) — **eventos ultra-granulares: xG + falta por jogador**
- Única fonte gratuita com **xG real**, **falta atribuída a cada jogador**, cartões c/ minuto e coordenadas.
- Coletado: **10 jogos do Brasil** nas Copas **2022 e 2018** (5 + 5), ~3.300–5.145 eventos por jogo (25 MB).
- `competitions.json`, `matches/`, `events/{match_id}.json`, `lineups/{match_id}.json` (cache local — não rebaixa).
- Ex. (Croácia×Brasil 2022): xG Brasil 4.95 / Croácia 3.77; faltas por jogador (Brozović 4, Casemiro 3, Modrić 3...).
- Edições disponíveis no repo: 2022 (c/ dados 360), 2018, 1990, 1986, 1974, 1970, 1962, 1958.
- Editar `SEASON_NAMES`/`TEAM` em `statsbomb.py` p/ ampliar. Refrescar: `python data/collectors/statsbomb.py`

### `newsdata/` 🟡 (chave) — notícias atuais
- `news_pt.json` (596 disponíveis) e `news_en.json` (1.563) — artigos de 22/06, incl. preview de Escócia×Brasil.
- 200 créditos/dia. Refrescar: `python data/collectors/newsdata.py`

---

## 📦 Arquivo consolidado

### [`../wc2026_brazil_context.json`](../wc2026_brazil_context.json)
Gerado por `build_summary.py` a partir das fontes acima. Contém:
- Grupo C real e classificação atual (Brasil 4pts, Marrocos 4, Escócia 3, Haiti 0)
- Os 3 jogos do Brasil com resultados e goleadores
- Próximo jogo + odds de mercado
- Tamanho do dataset histórico

### [`../statsbomb_brazil_summary.json`](../statsbomb_brazil_summary.json)
Gerado por `statsbomb.py`: resumo dos 10 jogos do Brasil (2022+2018) com xG por time,
finalizações, faltas por time, **faltas por jogador** e cartões. Pronto para calibrar os modelos.

Refrescar: `python data/collectors/build_summary.py`

---

## 🔑 Resumo de acesso (o que funcionou)

| Fonte | Acesso | Cobre 2026 ao vivo? | Granularidade |
|---|---|---|---|
| openfootball | 🟢 livre | ✅ resultados + goleadores | jogo + gols c/ minuto |
| Kaggle (martj42) | 🟡 token OK | ✅ calendário (placar defasado) | jogo |
| The Odds API | 🟡 chave | ✅ **odds ao vivo** | mercado 1X2 + totais |
| API-Football | 🟡 chave | ❌ **só 2022–2024 no free** | eventos + stats (faltas/escanteios por time) |
| NewsData.io | 🟡 chave | ✅ notícias | texto |
| StatsBomb | 🟢 livre | ❌ só Copas passadas | **xG + falta por jogador + coordenadas** |

**Limitação confirmada:** falta-por-jogador e xG **ao vivo na Copa 2026** não vêm em nenhuma fonte gratuita (só pago/trial). Para esse nível de detalhe usamos a **StatsBomb Open Data** (Copas 2022/2018) — ideal para *calibrar* os modelos com dados reais, ainda que de torneios passados.

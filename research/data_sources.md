# Fontes de Dados de Futebol — Levantamento Completo

> Pesquisa realizada em 22/06/2026 para o projeto de predição da Copa do Mundo 2026.
> Foco: fontes **gratuitas** (free tier, cadastro grátis, RSS, scraping ou datasets abertos).
> Cobre **todas as seleções** da Copa, não só o Brasil.
>
> Legenda: 🟢 grátis sem login · 🟡 grátis com cadastro/free tier · 🟠 trial / scraping (zona cinzenta de ToS) · 🔴 pago
> "não confirmado" = não foi possível verificar o número/detalhe exato na pesquisa.

---

## ⭐ TL;DR — Stack recomendada (100% grátis)

| Necessidade | Fonte primária | Backup / complemento |
|---|---|---|
| **Eventos ao vivo da Copa 2026** (gols, cartões, escanteios, posse, faltas por time) | API-Football (`/fixtures/events` + `/statistics`) | Live-Score-API (600 req/h) |
| **Calendário / grupos / resultados Copa 2026** | openfootball/worldcup.json 🟢 | Wikidata (SPARQL) + Wikipedia |
| **Eventos ultra-granulares para TREINAR modelos** (xG, faltas por jogador, localização) | StatsBomb Open Data 🟢 (Copas passadas) | Pappalardo/Wyscout (CC BY) |
| **Histórico longo de seleções** (Elo, Poisson, Dixon-Coles) | Kaggle `martj42` (49k jogos, 1872–2026) | piterfm "FIFA WC 1930-2026" |
| **Stats de jogador no clube** (gols, xG, forma) | FBref via `soccerdata` | Understat (xG) + Sofascore (rating) |
| **Odds (mercado)** | The Odds API 🟡 (500 créd/mês) | Football-Data.co.uk 🟢 (histórico) |
| **Lesões** | API-Football `/injuries` + `/sidelined` | worldfootballR (Transfermarkt) |
| **Notícias** | Google News RSS 🟢 | NewsData.io (200 créd/dia) |
| **Escalações** | API-Football `/fixtures/lineups` | RotoWire / Goal.com / Sofascore |

**Aviso sobre granularidade:** "falta atribuída a um jogador específico no minuto X" e "xG ao vivo" **não vêm em nenhum tier gratuito de API ao vivo**. A maioria entrega faltas como **total por time**. Para falta-por-jogador + xG só há: (a) StatsBomb Open Data, mas só de **Copas passadas**; ou (b) Sportradar/SportMonks/Opta — **pagos** (ou trial de 30 dias).

---

## 1. APIs de dados de partida (eventos, estatísticas, ao vivo)

### Tabela comparativa — melhores opções gratuitas

| API | Custo / Limite | Timeline min-a-min | Faltas (quem) | Escant. | Cartões | Gol+assist | Posse/Chutes | xG | Copa 2026 |
|---|---|---|---|---|---|---|---|---|---|
| **API-Football** 🟡 | 100 req/dia, 10/min | ✅ (Goal/Card/Subst/VAR/Foul) | ⚠️ só total/time | ✅ | ✅ | ✅ | ✅ | ❌ (free) | ✅ |
| **Live-Score-API** 🟡 | **600 req/hora** | ✅ match events | ⚠️ provável total | ✅ | ✅ (c/ recebedor) | ✅ | ✅ | ? | ✅ (World Cup API) |
| **Highlightly** 🟡 | 100 req/dia | ✅ live events | ? | provável | ✅ | provável | ✅ | ❌ free | provável (n/conf.) |
| **Football-Data.org** 🟡 | 10 req/min | ❌ (free) | ❌ | 🔴 add-on | limitado | ❌ | 🔴 add-on | ❌ | ✅ (fixtures/result.) |
| **TheSportsDB** 🟡 | chave `3` / $9/mês | limitada (5 req) | ❌ | fraco | parcial | parcial | fraco | ❌ | ✅ (raso) |
| **StatsBomb Open** 🟢 | 100% grátis, sem chave | ✅ ultra-granular | **✅ por jogador** | ✅ | ✅ | ✅ | ✅ | **✅** | só Copas **passadas** |
| **openfootball worldcup.json** 🟢 | 100% grátis | só gols c/ minuto | ❌ | ❌ | ❌ | parcial | ❌ | ❌ | ✅ (calend./result.) |
| **Sportradar** 🟠 | trial 30 dias | **✅ delta 10s** | **✅** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Entity Sports** 🟠 | free token = só histórico teste | ✅ play-by-play | ✅ (L1) | ✅ | ✅ | ✅ | ✅ | — | ✅ (pago p/ live) |

### Detalhamento

**API-Football (API-Sports)** 🟡 — *melhor custo-benefício para a Copa 2026 ao vivo*
- URL: https://www.api-football.com (direto via api-sports.io ou RapidAPI)
- Free: cadastro grátis, **100 req/dia, 10 req/min** (reseta 00:00 UTC). Já tem guia oficial da Copa 2026.
- Dados: `fixtures/events` (timeline com minuto, time, jogador, assistência, tipo: Goal/Card/Subst/VAR/**Foul**); `fixtures/statistics` (chutes, **faltas**, **escanteios**, posse %, cartões, passes, offsides); lineups e ratings por jogador. **Sem xG no free.**
- Limitação real: 100 req/dia é apertado para polling ao vivo (a cada 15s estoura rápido).
- Python: `footballAPI`, `SoccerAPI` (Comonitski), wrappers no tópico `api-football`.

**Live-Score-API** 🟡 — *limite mais generoso para jogo ao vivo*
- URL: https://live-score-api.com — **600 req/hora** no free + trial 14 dias.
- Dados: live scores, match events, **estatísticas (posse, chutes no/fora, escanteios, faltas)**, h2h, lineups, gols/cartões com identificação de quem recebeu. **Tem World Cup API dedicada.**
- Faltas provavelmente agregadas por time (confirmar granularidade por jogador).

**Highlightly** 🟡 — https://highlightly.net/football-api/ — free 100 req/dia, live events + timeline + lineups + highlights de vídeo. 950+ ligas; cobertura de Copa provável (não confirmada).

**Football-Data.org** 🟡 — https://www.football-data.org — free 10 req/min, **inclui FIFA World Cup**. Ótimo para fixtures/resultados/tabelas; **sem eventos granulares nem stats detalhadas no free** (escanteios/posse exigem add-on pago). Python: `pyfootball`.

**TheSportsDB** 🟡 — https://www.thesportsdb.com — chave de teste `3` (limitada) ou $9/mês. Bom para metadados (times, logos, schedule); **fraco para eventos granulares**.

**The Odds API** 🟡 — https://the-odds-api.com — free **500 créditos/mês** (~16 req/dia; 1 req pode custar vários créditos). **Só odds** (h2h, spreads, totals), cobre Brasileirão + mundiais. Use na peça "mercado de apostas" do ensemble.

**Sportradar** 🟠 — https://developer.sportradar.com — **trial 30 dias** (não é free permanente). Padrão da indústria: **Live Timelines Delta (10s)** com faltas por jogador + xG. Ideal para um *burst* de coleta dentro do trial.

**SportMonks** 🟠🔴 — https://www.sportmonks.com — free plan **só cobre Dinamarca + Escócia** (Copa **não** está no free). Dados riquíssimos (timeline, faltas, escanteios, xG no plano All-In) via trial 14 dias ou plano pago. Tem produto dedicado à Copa 2026 (pago).

**Outras:** Entity Sports 🟠 (token grátis só histórico de teste), Goalserve 🔴 (trial 30d, depois $150-550/mês), SportsData.io 🟠 (trial com dados *embaralhados*), AllSportsApi 🟡 (assistências + push WebSocket, limites pouco transparentes), **Opta/Stats Perform** 🔴 (enterprise, sem free tier — padrão-ouro mas inviável sem contrato).

**Scraping (FlashScore / SofaScore):** sem API oficial. Apify actors e libs (`FlashscoreScraping`, scrapers de SofaScore) trazem eventos/stats/lineups com latência 5-15s e a maior granularidade "grátis" ao vivo — porém frágil (anti-bot, ToS).

---

## 2. Datasets abertos para download (Kaggle, GitHub, acadêmicos)

### 2.1 Eventos granulares (para treinar xG / ML / Dixon-Coles)

**StatsBomb Open Data** 🟢 ⭐⭐⭐ — *o mais importante*
- https://github.com/statsbomb/open-data · Python: `pip install statsbombpy`
- ~3.400 eventos/jogo: passes, chutes **com xG**, **faltas atribuídas a jogador**, cartões, escanteios, dribles, **coordenadas X/Y**, e StatsBomb **360** (freeze-frames) em jogos selecionados.
- Cobertura: **Copas do Mundo masc. 2022, 2018, 1990, 1986, 1974, 1970, 1962, 1958**; Women's WC 2023/2019; Euro 2024/2020; Copa América 2024; Champions/La Liga históricas (eras Messi); etc. **Não tem 2026 ao vivo** — ideal para *treino/calibração*.
- JSON, sem login. User agreement (uso não-comercial, creditar StatsBomb). Viz: `mplsoccer`.

**Pappalardo et al. — Wyscout "Soccer match event dataset"** 🟢 (CC BY 4.0)
- figshare: https://figshare.com/collections/Soccer_match_event_dataset/4415000 · Nature: https://www.nature.com/articles/s41597-019-0247-7
- Eventos spatio-temporais (passes, chutes, faltas, duelos) com coordenadas. Cobertura: **Copa do Mundo 2018 + Euro 2016 + 5 grandes ligas 2017/18**. Estático. Versão JSON moderna: https://github.com/koenvo/wyscout-soccer-match-event-dataset

**Kaggle "Football Events" (secareanualin)** 🟡 — https://www.kaggle.com/datasets/secareanualin/football-events — **~900k eventos** em 9.074 jogos (gols, faltas, escanteios, cartões, chutes c/ texto). Só 5 grandes ligas EUR 2011/12–2016/17. **Sem Copas.** Estático.

**Kaggle "European Soccer Database" (hugomathien)** 🟡 — https://www.kaggle.com/datasets/hugomathien/soccer — SQLite ~300MB, +25k partidas, eventos em XML (gols, posse, escanteio, **faltas, cartões**), atributos FIFA, **odds de 10 casas**. 11 países EUR 2008–2016. Excelente para ML (relacional + odds).

### 2.2 Histórico de seleções e Copas (para Elo / baseline)

**Kaggle "International football results 1872-2026" (martj42)** 🟡 ⭐⭐⭐ — https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017 (mirror GitHub aberto: martj42/international_results)
- **~49.393 partidas de seleções A (1872–2026)**: resultado, torneio, sede, neutro. + `goalscorers.csv` (artilheiros c/ minuto) + `shootouts.csv`. Nível de partida (sem faltas/escanteios). **Atualizado quase diariamente.** Melhor base histórica de seleções.

**openfootball / worldcup** 🟢 ⭐⭐ — https://github.com/openfootball/worldcup.json (raw: `.../master/2026/worldcup.json`)
- **Todas as Copas 1930–2026** (já tem estrutura da 2026: grupos, calendário, sedes), resultados, gols c/ minuto. **Domínio público (CC0), sem chave.** Sem faltas/escanteios/lineups. Melhor fonte limpa para o torneio-alvo.

**piterfm "FIFA World Cup 1930-2026"** 🟡 — https://www.kaggle.com/datasets/piterfm/fifa-football-world-cup — matches, **goals, bookings, penalties, subs, squads, árbitros, técnicos, standings, awards** de todas as Copas. CSV.

**Football-Data.co.uk** 🟢 ⭐⭐ — https://www.football-data.co.uk/data.php — CSV por liga/temporada (2000/01→atual) com gols, **chutes, faltas, escanteios, cartões, árbitro + odds históricas de várias casas** (Bet365, Pinnacle...). **Só clubes** (sem seleções) — crucial para calibrar o motor de odds. Sem login.

**FiveThirtyEight SPI** 🟢 — https://github.com/fivethirtyeight/data/tree/master/soccer-spi — ratings SPI off/def, probabilidades, xG projetado/real. ~40 ligas 2016–2023. ⚠️ **DESCONTINUADO** (sem updates pós-2022/23) — usar só como feature histórica.

**Outros úteis:** `davidcariboo/player-scores` (Transfermarkt: 80k+ jogos, eventos, valuations — **atualizado**); `stefanoleone992` EA FC24/FIFA23 (atributos de jogadores — útil p/ impacto de escalação); `die9origephit` FIFA WC 2022 completo; datahub.io football-datasets.

---

## 3. Stats de jogadores nos clubes + métricas avançadas

> Nenhuma destas tem API oficial pública (exceto ClubElo CSV e datasets Kaggle). Acesso = **scraping** de páginas públicas → respeite robots.txt, use cache e delays. As libs maduras (`soccerdata`, `worldfootballR`) já fazem isso.

| Fonte | Dados-chave | Acesso | Cobertura | Ferramenta |
|---|---|---|---|---|
| **FBref** 🟡 | gols, assist, min, **xG, xA, npxG**, prog. passes/carries, SCA/GCA | scraping (sem key) | Big 5 + 40+ países (MLS, **Brasileirão**, Argentina), CL, Libertadores | `soccerdata`, `worldfootballR`, `ScraperFC` |
| **Understat** 🟡 | **xG, xA, xGChain, xGBuildup**, shot-level | scraping (JSON no HTML) | só 6 ligas EUR (desde 14/15) | `understatapi`, `soccerdata` |
| **Transfermarkt** 🟠 | valor de mercado, elencos, transferências, **lesões** | scraping (WAF) | mundo inteiro + seleções | `worldfootballR`, `transfermarkt-scraper` |
| **Sofascore** 🟠 | **ratings** por jogo, stats, heatmaps, lineups | scraping API interna | muito ampla (cobre Copa) | `soccerdata`, `ScraperFC`, `EasySoccerData` |
| **WhoScored** 🟠 | ratings/stats Opta detalhados | scraping c/ Selenium (Incapsula) | ampla | `soccerdata` (precisa Chrome) |
| **ClubElo** 🟢 | Elo de **clube** (força/contexto) | **API CSV grátis legítima** | clubes EUR | `soccerdata`, `pandas.read_csv` |
| **FotMob** 🟠 | xG/xA por jogo, stats temporada | API interna não-oficial (cinzenta) | ampla | `fotmob-api`, `pyfotmob` |
| **SoFIFA / EA FC** 🟡 | ratings e atributos do jogo | scraping / Kaggle CSV | quase todos os clubes | `soccerdata` (SoFIFA), Kaggle |

**Agregadores recomendados:**
- **`soccerdata`** (Python) — https://soccerdata.readthedocs.io — um pacote unifica FBref + Understat + Sofascore + WhoScored + ClubElo + SoFIFA + ESPN + Football-Data.co.uk em DataFrames padronizados, com cache e rate limiting automáticos. Cobre ~90% da necessidade.
- **`worldfootballR`** (R) — https://jaseziv.github.io/worldfootballR — FBref + Understat + Transfermarkt (FotMob foi **removido** por mudança de ToS na v0.6.4).
- **`ScraperFC`** (Python) — agrega FBref, Understat, ClubElo, Sofascore, Capology (salários), Transfermarkt.

**ClubElo** 🟢 — http://api.clubelo.com — única API CSV verdadeiramente livre: ranking de um dia (`/2026-06-22`), histórico de clube (`/ManCity`), fixtures. Foco europeu; cobertura fora da Europa não confirmada.

**Combinação sugerida:** FBref (base de stats global) + Understat (xG detalhado p/ quem joga nas 6 grandes EUR) + Sofascore (rating de forma p/ jogadores fora da Europa) + ClubElo (força do clube como feature) + EA FC24/25/26 (atributos).

---

## 4. Lesões

| Fonte | O que dá | Acesso | Cobertura |
|---|---|---|---|
| **API-Football** `/injuries` + `/sidelined` 🟡 | lesões atuais por **fixture** + histórico por jogador | REST, free 100/dia | ⚠️ checar flag `coverage.injuries` no `/leagues` p/ a Copa |
| **worldfootballR** `tm_player_injury_history()` 🟠 | histórico de lesões (Transfermarkt) | R, scraping (usar `Sys.sleep()`) | qualquer jogador por ID |
| **Datasets Kaggle/GitHub** 🟡 | histórico em CSV (treino/ML) | download | `davidcariboo/player-scores`, `salimt/football-datasets` (inclui seleção), figshare Transfermarkt |
| **PhysioRoom / PremierInjuries** 🟡 | tabela de lesões diária | scraping | **só Premier League** |
| **SportMonks** `sidelined` 🔴 | lesões/suspensões | REST | só nos planos pagos (free não serve) |

⚠️ A cobertura de lesões da Copa 2026 no free da API-Football **não está garantida** — verifique `coverage.injuries` após cadastrar.

---

## 5. Notícias

| Fonte | Free tier | Cadastro | Atraso | Comercial | Nota |
|---|---|---|---|---|---|
| **Google News RSS** 🟢 | **ilimitado** | não | quase real-time | ⚠️ só pessoal/não-comercial | **melhor opção** |
| **NewsData.io** 🟡 | 200 créd/dia (~2000 art.) | sim | ~12h | ✅ permitido | filtro `category=sports`, PT incluído |
| **Currents API** 🟡 | **1000 req/dia** | sim | real-time | ? | free generoso |
| **GNews** 🟡 | 100 req/dia | sim | 12h | ❌ só dev | sem conteúdo full |
| **NewsAPI.org** 🟡 | 100 req/dia | sim | **24h** | ❌ só dev | histórico ~1 mês |
| **Mediastack** 🟡 | 500 req/**mês** | sim | 30 min | limitado | free muito restrito |
| **Reddit API (r/soccer)** 🟡 | 60 req/min (OAuth) | sim | real-time | ToS | sentimento/buzz |
| **Bing News Search** 🔴 | — | — | — | — | **descontinuada pela Microsoft — não usar** |

**Google News RSS** (recomendado): `https://news.google.com/rss/search?q=Brazil+World+Cup+lineup&hl=pt-BR&gl=BR&ceid=BR:pt-419` — sem chave, sem conta.

---

## 6. Escalações (lineups)

- **API-Football** `/fixtures/lineups` 🟡 — escalações oficiais (titulares, reservas, formação, técnico) por fixture; free 100/dia. Checar `coverage.lineups`.
- **Sofascore** 🟠 (via `ScraperFC`/`soccerdata`) — escalações confirmadas + stats ricos; cobre Copa.
- **Sites de XI provável (scraping leve)** 🟡: RotoWire (`rotowire.com/soccer/lineups.php?league=WOC` — previstas E confirmadas por jogo da Copa), **Goal.com** ("probable line-ups WC 2026" das 48 seleções), **TheFantasyTool** (`thefantasytool.com/predicted-lineups-wc`), WhoScored (previews).
- **SportMonks** lineups 🔴 — free só DK/Escócia.

---

## 7. Estrutura da Copa 2026 (grupos, sedes, calendário)

- **Wikidata** 🟢 — `query.wikidata.org` (SPARQL) — melhor fonte **estruturada**, sem cadastro.
- **Wikipedia** 🟢 — https://en.wikipedia.org/wiki/2026_FIFA_World_Cup — 48 seleções, 104 jogos, 12 grupos (A–L), 16 sedes (11 EUA, 3 MEX, 2 CAN). Tabelas raspáveis.
- **openfootball/worldcup.json** 🟢 — já com a estrutura da 2026 (ver §2.2).
- **FIFA oficial** 🟢 — calendário/resultados (scraping, sem API).

---

## 8. Bibliotecas Python/R úteis (resumo)

| Lib | Linguagem | Cobre |
|---|---|---|
| `statsbombpy` | Python | StatsBomb Open Data |
| `soccerdata` | Python | FBref, Understat, Sofascore, WhoScored, ClubElo, SoFIFA, ESPN, Football-Data.co.uk |
| `worldfootballR` | R | FBref, Understat, Transfermarkt (lesões!) |
| `ScraperFC` | Python | FBref, Understat, ClubElo, Sofascore, Capology, Transfermarkt |
| `mplsoccer` | Python | viz + carregar StatsBomb open |
| `understatapi` | Python | Understat (xG/shot-level) |
| `fotmob-api` / `pyfotmob` | Python | FotMob (não-oficial) |
| `pyfootball` | Python | Football-Data.org |
| `transfermarkt-scraper` | Python | Transfermarkt |

---

## 9. Como isso encaixa no projeto atual

O projeto hoje usa **parâmetros estimados manualmente** (ver `models/ensemble.py`). Com estas fontes dá para substituir por dados reais:

1. **Treinar/calibrar de verdade** os modelos xG e Dixon-Coles → **StatsBomb Open Data** (Copas 2018/2022 com xG e eventos reais).
2. **Ratings de força reais** (Elo) → **Kaggle martj42** (49k jogos de seleções) em vez de Elo chutado.
3. **Forma recente dos jogadores no clube** (impacto de escalação de 15-25% citado no CLAUDE.md) → **FBref + Understat via `soccerdata`**.
4. **Lesões/escalações ao vivo da Copa 2026** → **API-Football** (`/injuries`, `/fixtures/lineups`).
5. **Odds reais (mercado)** → **The Odds API** (ao vivo) + **Football-Data.co.uk** (histórico p/ calibração).
6. **Notícias pré-jogo** → **Google News RSS**.

**Limitações que permanecem mesmo com tudo isso:** falta-por-jogador e xG **ao vivo** na Copa 2026 só via pago/trial (Sportradar 30 dias); cobertura da Copa 2026 nos free tiers (API-Football injuries/lineups) precisa ser confirmada no cadastro.

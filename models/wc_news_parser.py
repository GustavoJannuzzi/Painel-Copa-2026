"""
FASE 3B — Parser de notícias para extração de sinais de escalação/lesão.

Analisa os campos title + description dos artigos coletados pelo NewsData.io
e extrai:
  - Jogadores ausentes / lesionados / suspensos
  - Jogadores confirmados para o jogo
  - Sinal de forma da seleção (+1 / 0 / -1)

Combina:
  1. Padrões de regex específicos para PT e EN
  2. spaCy NER para reconhecer nomes de pessoas (PERSON entities)
  3. Fuzzy matching contra a base de jogadores (PlayerStrengthDB)

Saída: {
  team_name: {
    "absent": [player_name, ...],
    "confirmed": [player_name, ...],
    "form_signal": +1 / 0 / -1,
    "sources": [article_title, ...],
  }
}
"""
import sys
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wc_data

PROJECT_ROOT = wc_data.PROJECT_ROOT
NEWS_PT = PROJECT_ROOT / "data" / "raw" / "newsdata" / "news_pt.json"
NEWS_EN = PROJECT_ROOT / "data" / "raw" / "newsdata" / "news_en.json"
CACHE_PATH = PROJECT_ROOT / "analysis" / "news_signals.json"

# ──────────────────────────────────────────────────────────────────────────────
# Padrões de regex
# ──────────────────────────────────────────────────────────────────────────────

# PT — lesão/ausência
INJURY_PT = re.compile(
    r'\b(lesionado|contundido|se machucou|fora dos treinos|desfalque|'
    r'n[aã]o joga|n[aã]o atua|vetado|poupado|entorse|fratura|cirurgia|'
    r'suspenso|expulso|cart[aã]o vermelho|dois amarelos)\b',
    re.I
)
# EN — injury/absence
INJURY_EN = re.compile(
    r'\b(injured|injury|ruled out|doubtful|unavailable|suspended|'
    r'red card|two yellows|fitness doubt|limped off|withdrawn|doubt|'
    r'won\'t play|not available|out of the squad|miss(es|ing)?)\b',
    re.I
)
# PT — confirmação de escalação
CONFIRM_PT = re.compile(
    r'\b(vai jogar|escalado|confirmado|titulares?|XI inicial|vai atuar|começa jogando|'
    r'inicia a partida|convocado|est[áa] em campo)\b',
    re.I
)
# EN — lineup confirmation
CONFIRM_EN = re.compile(
    r'\b(confirmed lineup|starting XI|will start|named in the squad|'
    r'set to play|fit to play|returns? to the squad|is available)\b',
    re.I
)
# Padrões de forma positiva (PT + EN)
FORM_POSITIVE = re.compile(
    r'\b(imbat[íi]vel|grande fase|goleada|dominou|vit[oó]ria convincente|'
    r'melhor campanha|artilheiro|top form|on fire|unstoppable|dominant|'
    r'impressive|flying|excellent form)\b',
    re.I
)
FORM_NEGATIVE = re.compile(
    r'\b(crise|mau momento|derrota|fraco|decepcionante|pior momento|'
    r'preocupa|bajo rendimiento|struggle|poor form|crisis|disappointed)\b',
    re.I
)

# Mapa de nomes de times para detectar de qual time é a notícia
TEAM_ALIASES = {
    "Brazil": ["brasil", "brazil", "seleção", "canarinho", "verde e amarela"],
    "Argentina": ["argentina", "albiceleste", "messi"],
    "France": ["france", "frança", "les bleus", "equipe de france"],
    "Germany": ["germany", "alemanha", "mannschaft"],
    "England": ["england", "inglaterra", "three lions"],
    "Spain": ["spain", "espanha", "la roja", "la furia"],
    "Portugal": ["portugal", "seleção das quinas", "navegadores"],
    "Netherlands": ["netherlands", "holanda", "netherlands", "oranje"],
    "Colombia": ["colombia", "colômbia"],
    "Morocco": ["morocco", "marrocos", "lions of the atlas"],
    "Mexico": ["mexico", "méxico", "el tri"],
    "United States": ["united states", "usa", "estados unidos", "us men"],
    "Japan": ["japan", "japão"],
    "Uruguay": ["uruguay", "uruguai", "la celeste"],
    "Switzerland": ["switzerland", "suíça", "suiza"],
    "Norway": ["norway", "noruega"],
    "Senegal": ["senegal", "lions de la teranga"],
    "South Korea": ["south korea", "coreia do sul", "coreia"],
    "Croatia": ["croatia", "croácia"],
    "Ecuador": ["ecuador", "equador"],
    "Australia": ["australia", "austrália"],
    "Turkey": ["turkey", "turquia"],
    "Paraguay": ["paraguay", "paraguai"],
    "Saudi Arabia": ["saudi arabia", "arábia saudita"],
    "Scotland": ["scotland", "escócia"],
    "Ghana": ["ghana", "gana"],
    "Canada": ["canada", "canadá"],
    "Bosnia and Herzegovina": ["bósnia", "bosnia"],
    "DR Congo": ["congo", "rd congo"],
    "South Africa": ["south africa", "africa do sul", "áfrica do sul"],
    "Algeria": ["algeria", "argélia"],
    "Jordan": ["jordan", "jordânia"],
    "Ivory Coast": ["ivory coast", "costa do marfim"],
    "Curacao": ["curacao", "curaçao"],
    "Iraq": ["iraq", "iraque"],
    "Tunisia": ["tunisia", "tunísia"],
    "Cape Verde": ["cape verde", "cabo verde"],
    "New Zealand": ["new zealand", "nova zelândia"],
    "Iran": ["iran", "irã"],
    "Belgium": ["belgium", "bélgica"],
    "Sweden": ["sweden", "suécia"],
    "Egypt": ["egypt", "egito"],
    "Uzbekistan": ["uzbekistan", "uzbequistão"],
    "Haiti": ["haiti"],
    "Qatar": ["qatar", "catar"],
}


# ──────────────────────────────────────────────────────────────────────────────
# Carrega spaCy (com fallback se modelo PT não estiver disponível)
# ──────────────────────────────────────────────────────────────────────────────

def _load_spacy():
    try:
        import spacy
        try:
            return spacy.load("pt_core_news_sm"), spacy.load("en_core_web_sm")
        except OSError:
            try:
                return None, spacy.load("en_core_web_sm")
            except OSError:
                return None, None
    except ImportError:
        return None, None


# ──────────────────────────────────────────────────────────────────────────────
# Extração
# ──────────────────────────────────────────────────────────────────────────────

def _detect_team(text: str) -> str | None:
    text_lower = text.lower()
    for team, aliases in TEAM_ALIASES.items():
        if any(alias in text_lower for alias in aliases):
            return team
    return None


def _extract_persons_spacy(text: str, nlp) -> list:
    if nlp is None or not text:
        return []
    doc = nlp(text[:500])  # limita para speed
    return [ent.text for ent in doc.ents if ent.label_ == "PER"]


def _is_recent(pub_date: str, max_days: int = 3) -> bool:
    """Filtra apenas notícias dos últimos N dias."""
    try:
        dt = datetime.strptime(pub_date[:19], "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - dt).days <= max_days
    except Exception:
        return True  # se não conseguir parsear, inclui


def parse_news(max_days: int = 4) -> dict:
    """
    Processa todos os artigos de notícias e retorna sinais por time.
    max_days: janela de notícias recentes a considerar.
    """
    nlp_pt, nlp_en = _load_spacy()
    signals: dict = defaultdict(lambda: {
        "absent": [], "confirmed": [], "form_signal": 0, "sources": []
    })

    def _process_article(article: dict, lang: str):
        pub = article.get("pubDate", "")
        if not _is_recent(pub, max_days):
            return

        title = article.get("title", "") or ""
        desc  = article.get("description", "") or ""
        text  = f"{title}. {desc}"
        text_clean = re.sub(r'[^\w\s.,;:\'-]', ' ', text)

        # Detecta time referenciado
        team = _detect_team(text_clean)
        if team is None:
            return

        # Detecta padrão de lesão/ausência
        is_injury = bool(
            (lang == "pt" and INJURY_PT.search(text_clean)) or
            (lang == "en" and INJURY_EN.search(text_clean))
        )
        is_confirm = bool(
            (lang == "pt" and CONFIRM_PT.search(text_clean)) or
            (lang == "en" and CONFIRM_EN.search(text_clean))
        )

        # Extrai nomes de pessoas
        nlp = nlp_pt if lang == "pt" else nlp_en
        persons = _extract_persons_spacy(text_clean, nlp)

        if is_injury and persons:
            for p in persons:
                if p not in signals[team]["absent"]:
                    signals[team]["absent"].append(p)
            if title not in signals[team]["sources"]:
                signals[team]["sources"].append(title[:80])

        if is_confirm and persons:
            for p in persons:
                if p not in signals[team]["confirmed"] and p not in signals[team]["absent"]:
                    signals[team]["confirmed"].append(p)

        # Forma
        if FORM_POSITIVE.search(text_clean):
            signals[team]["form_signal"] += 1
        if FORM_NEGATIVE.search(text_clean):
            signals[team]["form_signal"] -= 1

    # Processa PT
    if NEWS_PT.exists():
        data = json.load(open(NEWS_PT, encoding="utf-8"))
        articles = data if isinstance(data, list) else data.get("results", [])
        for a in articles:
            _process_article(a, "pt")

    # Processa EN
    if NEWS_EN.exists():
        data = json.load(open(NEWS_EN, encoding="utf-8"))
        articles = data if isinstance(data, list) else data.get("results", [])
        for a in articles:
            _process_article(a, "en")

    # Normaliza form_signal para -1 / 0 / +1
    result = {}
    for team, s in signals.items():
        result[team] = {
            "absent": list(set(s["absent"])),
            "confirmed": list(set(s["confirmed"])),
            "form_signal": max(-1, min(1, s["form_signal"])),
            "sources": s["sources"][:3],
        }

    return result


def save_signals(signals: dict, path: Path = CACHE_PATH):
    json.dump(signals, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def load_signals(path: Path = CACHE_PATH) -> dict:
    if not path.exists():
        return {}
    return json.load(open(path, encoding="utf-8"))


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("[NewsParser] Analisando noticias recentes...")
    signals = parse_news(max_days=4)
    save_signals(signals)

    teams_with_signals = {t: s for t, s in signals.items()
                         if s["absent"] or s["confirmed"] or s["form_signal"] != 0}
    print(f"\n  Times com sinais detectados: {len(teams_with_signals)}")
    for team, s in teams_with_signals.items():
        print(f"\n  {team}:")
        if s["absent"]:
            print(f"    Desfalques: {s['absent']}")
        if s["confirmed"]:
            print(f"    Confirmados: {s['confirmed']}")
        if s["form_signal"] != 0:
            print(f"    Forma: {'+' if s['form_signal'] > 0 else ''}{s['form_signal']}")
        if s["sources"]:
            print(f"    Fonte: {s['sources'][0][:60]}")

    print(f"\n[OK] Sinais salvos em: {CACHE_PATH}")

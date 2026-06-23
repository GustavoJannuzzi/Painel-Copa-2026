"""
Gera output/index.html — painel visual self-contained da Copa 2026.
v3: modal de detalhes por jogo, ícones SVG, fonte Inter, stats auxiliares.
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "models"))
import wc_data

ANALYSIS = ROOT / "analysis"


def build_ratings():
    elo = json.load(open(ANALYSIS / "elo_ratings.json", encoding="utf-8"))["ratings"]
    dcm = json.load(open(ANALYSIS / "dixoncoles_model.json", encoding="utf-8"))
    att, de = dcm["attack"], dcm["defense"]
    teams = wc_data.real_teams()
    rows = []
    for t in teams:
        if t in elo and t in att:
            rows.append({"team": t, "elo": round(elo[t], 1),
                         "att": round(att[t], 2), "def": round(de[t], 2),
                         "net": round(att[t] + de[t], 2)})
    rows.sort(key=lambda r: r["elo"], reverse=True)
    return rows


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Copa 2026 — Painel Preditivo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  background:#020810;
  color:#c8d8ec;
  font-family:'Inter',-apple-system,'Segoe UI',Roboto,sans-serif;
  line-height:1.5;
  min-height:100vh;
  overflow-x:hidden;
  -webkit-font-smoothing:antialiased;
}
body::before{
  content:'';position:fixed;inset:0;
  background-image:
    linear-gradient(rgba(0,180,255,.035) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,180,255,.035) 1px,transparent 1px);
  background-size:40px 40px;
  pointer-events:none;z-index:0;
}
body::after{
  content:'';position:fixed;inset:0;
  background:
    radial-gradient(ellipse 80% 60% at 50% -10%,rgba(0,100,255,.10),transparent),
    radial-gradient(ellipse 50% 40% at 100% 80%,rgba(120,0,255,.07),transparent),
    radial-gradient(ellipse 50% 40% at 0% 60%,rgba(0,200,100,.05),transparent);
  pointer-events:none;z-index:0;
}
.glass{
  background:rgba(8,18,40,.65);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border:1px solid rgba(255,255,255,.08);border-radius:14px;
}
.glass-bright{
  background:rgba(10,24,55,.75);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,.12);border-radius:14px;
}

/* ── HEADER ── */
.site-header{
  position:sticky;top:0;z-index:200;
  background:rgba(2,8,16,.88);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
  border-bottom:1px solid rgba(255,255,255,.06);
}
.header-inner{max-width:1320px;margin:0 auto;padding:14px 24px 0;}
.header-top{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.logo-icon{
  width:36px;height:36px;flex-shrink:0;
  display:flex;align-items:center;justify-content:center;
  filter:drop-shadow(0 0 14px rgba(250,200,20,.5));
}
.header-text h1{
  font-size:18px;font-weight:800;letter-spacing:-.03em;
  background:linear-gradient(100deg,#e8b820 0%,#ff9200 55%,#f03850 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.header-text .tagline{font-size:11px;color:#4a6080;margin-top:1px;font-weight:500;}
.header-pills{margin-left:auto;display:flex;gap:7px;flex-wrap:wrap;}
.hpill{
  display:inline-flex;align-items:center;gap:5px;
  padding:4px 11px;border-radius:6px;
  font-size:11px;font-weight:700;letter-spacing:.01em;
  border:1px solid;backdrop-filter:blur(8px);
  transition:all .2s;
}
.hpill:hover{transform:translateY(-1px)}
.hpill-g{background:rgba(0,229,122,.07);border-color:rgba(0,229,122,.22);color:#00d470}
.hpill-y{background:rgba(232,184,32,.07);border-color:rgba(232,184,32,.22);color:#e8b820}
.hpill-b{background:rgba(0,170,255,.07);border-color:rgba(0,170,255,.22);color:#00aaff}

/* ── TABS ── */
.tab-bar{
  display:flex;gap:2px;padding:12px 0 0;
  overflow-x:auto;scrollbar-width:none;
}
.tab-bar::-webkit-scrollbar{display:none}
.tab-btn{
  position:relative;
  background:transparent;border:none;
  color:#3a5570;cursor:pointer;
  font-size:11.5px;font-weight:700;
  padding:7px 15px;border-radius:8px 8px 0 0;
  white-space:nowrap;letter-spacing:.02em;
  transition:color .2s;font-family:'Inter',sans-serif;
  display:flex;align-items:center;gap:6px;
}
.tab-btn::after{
  content:'';position:absolute;bottom:0;left:50%;right:50%;
  height:2px;background:linear-gradient(90deg,#e8b820,#ff9200);
  border-radius:2px;transition:all .25s;
}
.tab-btn:hover{color:#7a9ab8}
.tab-btn.active{color:#e8b820}
.tab-btn.active::after{left:10px;right:10px}
.tab-icon{width:14px;height:14px;flex-shrink:0;opacity:.75}
.tab-btn.active .tab-icon{opacity:1}

/* ── LAYOUT ── */
.wrap{max-width:1320px;margin:0 auto;padding:26px 20px 100px;position:relative;z-index:1;}
.tab-pane{display:none}.tab-pane.active{display:block}
.section{margin-bottom:26px}
.section-title{
  font-size:14px;font-weight:800;color:#c0d0e4;letter-spacing:-.01em;
  margin-bottom:16px;display:flex;align-items:center;gap:8px;
}
.section-title-dot{
  width:3px;height:16px;border-radius:2px;flex-shrink:0;
  background:linear-gradient(180deg,#e8b820,#ff9200);
}
.section-title::after{
  content:'';flex:1;height:1px;
  background:linear-gradient(90deg,rgba(255,255,255,.08),transparent);
  margin-left:6px;
}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media(max-width:1024px){.grid4{grid-template-columns:repeat(2,1fr)}}
@media(max-width:860px){.grid2,.grid3,.grid4{grid-template-columns:1fr}}

/* ── KPI CARDS ── */
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:26px;}
.kpi{
  position:relative;overflow:hidden;
  background:rgba(8,18,40,.72);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:18px;
  transition:transform .2s,border-color .2s,box-shadow .2s;
}
.kpi:hover{
  transform:translateY(-2px);border-color:rgba(255,255,255,.14);
  box-shadow:0 8px 36px rgba(0,0,0,.4),0 0 0 1px rgba(255,255,255,.05);
}
.kpi-glow{position:absolute;top:-30px;right:-30px;width:90px;height:90px;border-radius:50%;opacity:.1;filter:blur(28px);transition:opacity .2s;}
.kpi:hover .kpi-glow{opacity:.2}
.kpi-icon{width:20px;height:20px;margin-bottom:10px;display:block;opacity:.7}
.kpi .num{font-size:32px;font-weight:900;letter-spacing:-.04em;line-height:1;font-variant-numeric:tabular-nums;}
.kpi .num.c-gold{color:#e8b820;text-shadow:0 0 28px rgba(232,184,32,.3)}
.kpi .num.c-green{color:#00d470;text-shadow:0 0 28px rgba(0,212,112,.25)}
.kpi .num.c-cyan{color:#00ccf5;text-shadow:0 0 28px rgba(0,204,245,.25)}
.kpi .num.c-purple{color:#a060f0;text-shadow:0 0 28px rgba(160,96,240,.25)}
.kpi .num.c-orange{color:#ff8820;text-shadow:0 0 28px rgba(255,136,32,.25)}
.kpi .label{font-size:11px;font-weight:700;color:#7a9ab8;margin-top:7px;text-transform:uppercase;letter-spacing:.06em;}
.kpi .explain{font-size:11px;color:#2e4060;margin-top:3px;line-height:1.4}
.kpi .quality-bar{height:2px;margin-top:10px;border-radius:1px;background:rgba(255,255,255,.06);overflow:hidden;}
.kpi .quality-fill{height:100%;border-radius:1px;transition:width 1s ease}

/* ── TOOLTIP ── */
.tip{
  position:relative;display:inline-block;width:14px;height:14px;border-radius:50%;
  background:rgba(255,255,255,.07);color:#4a6080;font-size:9px;font-weight:700;
  text-align:center;line-height:14px;cursor:help;border:1px solid rgba(255,255,255,.1);
  vertical-align:middle;margin-left:4px;
}
.tip::before{
  content:attr(data-tip);position:absolute;bottom:calc(100% + 8px);left:50%;
  transform:translateX(-50%);background:rgba(5,15,35,.97);
  border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:8px 12px;
  width:220px;font-size:11px;color:#7a9ab8;line-height:1.5;white-space:normal;
  pointer-events:none;opacity:0;transition:opacity .15s;z-index:999;
}
.tip:hover::before{opacity:1}

/* ── CHARTS ── */
.chart-box{position:relative;padding:18px;}
.chart-box .ch-title{font-size:12.5px;font-weight:700;color:#7a9ab8;margin-bottom:12px;display:flex;align-items:center;gap:6px;}
.chart-box .ch-sub{font-size:11px;color:#2e4060;margin-top:-8px;margin-bottom:10px}
.ch{position:relative;height:220px}
.ch-sm{position:relative;height:180px}

/* ── TABLES ── */
.tbl-wrap{overflow-x:auto;border-radius:12px;border:1px solid rgba(255,255,255,.06);}
table{width:100%;border-collapse:collapse;font-size:12.5px}
thead th{
  background:rgba(5,14,32,.82);color:#3a5570;font-size:10px;font-weight:700;
  text-transform:uppercase;letter-spacing:.07em;
  padding:10px 14px;white-space:nowrap;border-bottom:1px solid rgba(255,255,255,.06);
  cursor:pointer;user-select:none;transition:color .15s;
}
thead th:hover{color:#7a9ab8}
thead th .sort-arrow{opacity:.4;margin-left:3px}
tbody td{
  padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.04);
  vertical-align:middle;white-space:nowrap;
}
tbody tr:last-child td{border-bottom:none}
tbody tr{transition:background .12s;cursor:pointer;}
tbody tr:hover td{background:rgba(255,255,255,.03)}

/* ── PROB BAR ── */
.pbar{display:flex;height:5px;border-radius:3px;overflow:hidden;gap:1px}
.pbar .ph{background:#3b82f6}.pbar .pd{background:#8050d0}.pbar .pa{background:#e04060}
.pnums{font-size:10px;color:#3a5570;margin-top:3px;font-variant-numeric:tabular-nums}

/* ── PILLS ── */
.pill{
  display:inline-flex;align-items:center;gap:3px;
  padding:2px 8px;border-radius:5px;font-size:10px;font-weight:700;border:1px solid;
}
.pill-win{background:rgba(0,212,112,.1);color:#00d470;border-color:rgba(0,212,112,.28)}
.pill-lose{background:rgba(224,64,96,.1);color:#e04060;border-color:rgba(224,64,96,.22)}
.pill-score{background:rgba(232,184,32,.1);color:#e8b820;border-color:rgba(232,184,32,.28)}
.pill-pend{background:rgba(74,96,128,.1);color:#4a6080;border-color:rgba(74,96,128,.22)}

/* ── FILTERS ── */
.filters{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:16px}
.fbtn{
  background:rgba(8,18,40,.8);color:#3a5570;
  border:1px solid rgba(255,255,255,.06);border-radius:7px;padding:5px 13px;
  cursor:pointer;font-size:11px;font-weight:700;transition:all .15s;
  letter-spacing:.02em;font-family:'Inter',sans-serif;
}
.fbtn:hover{color:#7a9ab8;border-color:rgba(255,255,255,.12)}
.fbtn.active{background:rgba(232,184,32,.1);color:#e8b820;border-color:rgba(232,184,32,.3);}

/* ── GAME CARDS ── */
.gcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;}
.gcard{
  position:relative;overflow:hidden;
  background:rgba(8,18,40,.72);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:16px;
  cursor:pointer;
  transition:transform .2s,border-color .2s,box-shadow .2s;
}
.gcard:hover{
  transform:translateY(-2px);border-color:rgba(232,184,32,.28);
  box-shadow:0 10px 36px rgba(0,0,0,.5),0 0 24px rgba(232,184,32,.04);
}
.gcard::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(255,255,255,.025),transparent 60%);pointer-events:none;}
.gc-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}
.gc-group{font-size:10px;font-weight:700;color:#3a5570;text-transform:uppercase;letter-spacing:.07em}
.gc-date{font-size:10px;color:#243448;font-weight:500;}
.gc-matchup{display:flex;align-items:center;gap:8px;margin-bottom:12px}
.gc-team{flex:1;text-align:center}
.gc-team .tc-name{font-size:13.5px;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;letter-spacing:-.01em;}
.gc-team .tc-xg{font-size:10px;color:#3a5570;margin-top:2px;font-weight:500;}
.gc-vs{color:#243448;font-size:12px;font-weight:700;flex-shrink:0}
.gc-score{
  text-align:center;font-size:26px;font-weight:900;letter-spacing:-.03em;
  color:#e8b820;text-shadow:0 0 20px rgba(232,184,32,.35);
  margin:2px 0 8px;font-variant-numeric:tabular-nums;
}
.gc-pbar{display:flex;height:4px;border-radius:2px;overflow:hidden;margin-bottom:5px;gap:1px}
.gc-pnums{
  display:flex;justify-content:space-between;
  font-size:10px;font-variant-numeric:tabular-nums;color:#3a5570;font-weight:500;
}
.gc-pnums .pn-h{color:#3b82f6;font-weight:700}
.gc-pnums .pn-a{color:#e04060;font-weight:700}
.gc-mkt{font-size:10px;color:#2e4060;margin-top:7px;display:flex;align-items:center;gap:4px;}
.gc-hint{font-size:10px;color:#2a3c54;margin-top:7px;text-align:right;font-weight:500;letter-spacing:.02em;}

/* ── STANDINGS ── */
.sgrids{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;}
.sgroup{background:rgba(8,18,40,.72);border:1px solid rgba(255,255,255,.06);border-radius:12px;overflow:hidden;}
.sgroup:hover{border-color:rgba(255,255,255,.11)}
.sg-head{background:rgba(5,12,30,.8);padding:9px 13px;font-size:10px;font-weight:700;color:#3a5570;text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid rgba(255,255,255,.05);}
.sg-tbl{width:100%;border-collapse:collapse;font-size:11.5px}
.sg-tbl td{padding:7px 10px;border-bottom:1px solid rgba(255,255,255,.04)}
.sg-tbl tr:last-child td{border:none}
.sg-tbl .rank{color:#2a3c54;width:16px;font-weight:700}
.sg-tbl .qual{border-left:3px solid #00d470}
.sg-tbl .bubble{border-left:3px solid #e8b820}
.sg-tbl .pts{font-weight:800;color:#c8d8ec;text-align:center;width:24px}
.sg-tbl .gd{color:#3a5570;text-align:center;width:28px;font-size:10.5px}
.form-pills{display:flex;gap:2px}
.fp{width:13px;height:13px;border-radius:2px;font-size:8px;font-weight:800;display:flex;align-items:center;justify-content:center;}
.fp-w{background:rgba(0,212,112,.2);color:#00d470;border:1px solid rgba(0,212,112,.28)}
.fp-d{background:rgba(128,80,208,.15);color:#8050d0;border:1px solid rgba(128,80,208,.28)}
.fp-l{background:rgba(224,64,96,.15);color:#e04060;border:1px solid rgba(224,64,96,.22)}

/* ── BRACKET ── */
.bracket-scroll{overflow-x:auto;padding-bottom:12px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.1) transparent}
.bracket{display:flex;gap:10px;min-width:1200px;align-items:stretch}
.b-col{flex:1;display:flex;flex-direction:column;gap:0}
.b-col-narrow{flex:.55}
.b-rnd-title{font-size:9px;font-weight:800;color:#2e4060;text-transform:uppercase;letter-spacing:.1em;text-align:center;padding:7px 0 9px;border-bottom:1px solid rgba(255,255,255,.05);margin-bottom:5px;}
.b-match{background:rgba(5,14,32,.72);border:1px solid rgba(255,255,255,.06);border-radius:9px;padding:7px 9px;margin:3px 0;transition:border-color .15s;position:relative;overflow:hidden;}
.b-match:hover{border-color:rgba(232,184,32,.28)}
.b-match::before{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;background:linear-gradient(180deg,transparent,rgba(232,184,32,.28),transparent);}
.b-team{display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:11px;}
.b-team:first-child{border-bottom:1px solid rgba(255,255,255,.05)}
.b-name{font-weight:700;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.b-tag{font-size:9px;color:#2e4060;margin-right:4px;flex-shrink:0}
.b-prob{font-size:10px;color:#3a5570;font-variant-numeric:tabular-nums;flex-shrink:0}
.b-fav .b-name{color:#e8b820}
.b-fav .b-prob{color:#e8b820;font-weight:700}

/* ── FRAMEWORK CARDS ── */
.fw-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:26px;}
.fw-card{background:rgba(8,18,40,.65);border:1px solid rgba(255,255,255,.07);border-radius:12px;padding:18px;transition:border-color .2s,transform .2s;position:relative;overflow:hidden;}
.fw-card:hover{border-color:rgba(232,184,32,.22);transform:translateY(-2px)}
.fw-card::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(255,255,255,.02),transparent);pointer-events:none;}
.fw-num{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#e8b820,#ff9200);color:#000;font-weight:900;font-size:13px;display:flex;align-items:center;justify-content:center;margin-bottom:11px;box-shadow:0 4px 12px rgba(232,184,32,.28);}
.fw-card h4{font-size:13.5px;font-weight:800;color:#c8d8ec;margin-bottom:7px;letter-spacing:-.01em;}
.fw-card p{font-size:11.5px;color:#3a5570;line-height:1.65}
.fw-card code{background:rgba(232,184,32,.1);padding:1px 5px;border-radius:3px;font-size:11px;color:#e8b820;border:1px solid rgba(232,184,32,.18);}

/* ── METRIC BARS ── */
.mbar-row{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:12px;}
.mbar-row:last-child{border:none}
.mbar-name{width:130px;flex-shrink:0;color:#4a6080}
.mbar-bg{flex:1;height:5px;border-radius:3px;background:rgba(255,255,255,.05);overflow:hidden;}
.mbar-fill{height:100%;border-radius:3px;transition:width .8s ease}
.mbar-val{width:52px;text-align:right;font-weight:700;font-variant-numeric:tabular-nums;color:#7a9ab8}

/* ── DATA SOURCES ── */
.ds-list{list-style:none}
.ds-item{display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05);}
.ds-item:last-child{border:none}
.ds-icon{width:20px;height:20px;flex-shrink:0;margin-top:1px;color:#4a6080}
.ds-info strong{font-size:12.5px;color:#7a9ab8;font-weight:700}
.ds-info p{font-size:11px;color:#2e4060;margin-top:2px;line-height:1.5}

/* ── CALIBRATION BINS ── */
.calbins{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}
.calbin{flex:1;min-width:56px;background:rgba(5,14,32,.7);border:1px solid rgba(255,255,255,.06);border-radius:9px;padding:9px 5px;text-align:center;font-size:10.5px;transition:border-color .15s;}
.calbin:hover{border-color:rgba(255,255,255,.14)}
.calbin .cbl{color:#2e4060;margin-bottom:5px;font-size:9px;text-transform:uppercase;letter-spacing:.05em}
.calbin .cbars{height:52px;display:flex;align-items:flex-end;justify-content:center;gap:4px;margin-bottom:4px}
.calbin .cbar{width:11px;border-radius:2px 2px 0 0}
.calbin .cval{font-weight:800;font-size:12px}
.calbin .cn{font-size:9px;color:#243448}

/* ── RANKING ── */
.rank-bar-bg{width:96px;height:4px;background:rgba(255,255,255,.05);border-radius:2px;overflow:hidden;display:inline-block;vertical-align:middle}
.rank-bar-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,#3b82f6,#e8b820)}

/* ── MISC ── */
.mono{font-variant-numeric:tabular-nums}
.muted{color:#3a5570}
.small{font-size:11px}
.score-big{font-size:21px;font-weight:900;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.scroll-y{overflow-y:auto;max-height:500px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.1) transparent}
.divider{border:none;border-top:1px solid rgba(255,255,255,.05);margin:16px 0}
.empty{color:#2e4060;text-align:center;padding:48px;font-size:14px}
.footer{color:#243448;font-size:11px;margin-top:36px;padding:14px 0;border-top:1px solid rgba(255,255,255,.05);line-height:1.7;}
.fade-in{animation:fadeIn .35s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
@keyframes shimmer{0%{background-position:200% center}100%{background-position:-200% center}}
.shimmer-text{
  background:linear-gradient(90deg,#4a6080 0%,#c8d8ec 50%,#4a6080 100%);
  background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;animation:shimmer 3s linear infinite;
}
.pulse-dot{width:6px;height:6px;border-radius:50%;background:#00d470;display:inline-block;box-shadow:0 0 0 0 rgba(0,212,112,.4);animation:pulseDot 2s infinite;}
@keyframes pulseDot{0%{box-shadow:0 0 0 0 rgba(0,212,112,.4)}70%{box-shadow:0 0 0 6px rgba(0,212,112,0)}100%{box-shadow:0 0 0 0 rgba(0,212,112,0)}}
.rr-row{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:12px;cursor:pointer;transition:background .12s;}
.rr-row:last-child{border:none}
.rr-row:hover{background:rgba(255,255,255,.02);border-radius:7px;padding-left:6px}
.countup{display:inline-block}

/* ── MODAL ── */
.modal-overlay{
  position:fixed;inset:0;z-index:1000;
  background:rgba(1,5,14,.85);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  display:flex;align-items:center;justify-content:center;
  padding:20px;opacity:0;pointer-events:none;transition:opacity .25s;
}
.modal-overlay.open{opacity:1;pointer-events:all}
.modal-box{
  background:rgba(6,15,38,.96);border:1px solid rgba(255,255,255,.12);border-radius:18px;
  width:100%;max-width:680px;max-height:90vh;overflow-y:auto;
  scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.1) transparent;
  transform:scale(.97) translateY(8px);transition:transform .25s;
  position:relative;
}
.modal-overlay.open .modal-box{transform:scale(1) translateY(0)}
.modal-close{
  position:sticky;top:0;z-index:10;
  display:flex;justify-content:flex-end;
  background:linear-gradient(180deg,rgba(6,15,38,.98) 80%,transparent);
  padding:14px 16px 6px;
}
.modal-close-btn{
  background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);
  border-radius:7px;color:#7a9ab8;font-size:12px;font-weight:700;
  padding:5px 12px;cursor:pointer;font-family:'Inter',sans-serif;
  transition:all .15s;
}
.modal-close-btn:hover{background:rgba(255,255,255,.12);color:#c8d8ec}
.modal-body{padding:0 20px 24px}
.modal-header{
  text-align:center;padding:0 0 20px;border-bottom:1px solid rgba(255,255,255,.07);margin-bottom:20px;
}
.modal-badge{font-size:10px;font-weight:700;color:#3a5570;text-transform:uppercase;letter-spacing:.09em;margin-bottom:10px;}
.modal-teams{
  display:flex;align-items:center;gap:12px;justify-content:center;
  font-size:17px;font-weight:800;letter-spacing:-.01em;margin-bottom:8px;
}
.modal-score{
  font-size:44px;font-weight:900;letter-spacing:-.04em;font-variant-numeric:tabular-nums;
  color:#e8b820;text-shadow:0 0 32px rgba(232,184,32,.35);margin:4px 0;
}
.modal-score.predicted{color:#4a6080;text-shadow:none;font-size:28px}
.modal-pbar-row{display:flex;height:5px;border-radius:3px;overflow:hidden;margin-bottom:5px;max-width:360px;margin-left:auto;margin-right:auto;}
.modal-pnums{display:flex;justify-content:space-between;font-size:11px;font-variant-numeric:tabular-nums;max-width:360px;margin:0 auto;}
.modal-section{margin-bottom:20px}
.modal-section-title{font-size:10px;font-weight:800;color:#3a5570;text-transform:uppercase;letter-spacing:.09em;margin-bottom:10px;display:flex;align-items:center;gap:7px;}
.modal-section-title::before{content:'';width:2px;height:12px;background:linear-gradient(180deg,#e8b820,#ff9200);border-radius:1px;flex-shrink:0;}

/* goal events */
.goal-list{display:flex;flex-direction:column;gap:5px}
.goal-item{
  display:flex;align-items:center;gap:9px;font-size:12.5px;
  padding:6px 10px;border-radius:7px;background:rgba(255,255,255,.025);
}
.goal-min{font-size:11px;font-weight:700;color:#3a5570;width:36px;flex-shrink:0;font-variant-numeric:tabular-nums;}
.goal-name{flex:1;font-weight:600}
.goal-tag{font-size:9.5px;font-weight:700;padding:1px 6px;border-radius:3px;flex-shrink:0}
.goal-tag-pen{background:rgba(232,184,32,.15);color:#e8b820;border:1px solid rgba(232,184,32,.25)}
.goal-tag-og{background:rgba(224,64,96,.15);color:#e04060;border:1px solid rgba(224,64,96,.22)}
.goal-team-h{border-left:2px solid #3b82f6}
.goal-team-a{border-left:2px solid #e04060}

/* aux stat bars */
.aux-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.aux-card{
  background:rgba(5,12,30,.7);border:1px solid rgba(255,255,255,.07);
  border-radius:10px;padding:12px 14px;
}
.aux-card-title{font-size:10px;font-weight:700;color:#3a5570;text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px;}
.aux-stat-row{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.aux-stat-row:last-child{margin-bottom:0}
.aux-team-label{font-size:11px;font-weight:700;width:80px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.aux-bar-bg{flex:1;height:5px;border-radius:3px;background:rgba(255,255,255,.06);overflow:hidden}
.aux-bar-fill{height:100%;border-radius:3px;transition:width .6s ease}
.aux-val{font-size:11px;font-weight:700;font-variant-numeric:tabular-nums;color:#7a9ab8;width:32px;text-align:right;flex-shrink:0}
.prob-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:4px}
.prob-card{background:rgba(5,12,30,.7);border:1px solid rgba(255,255,255,.07);border-radius:9px;padding:11px 10px;text-align:center;}
.prob-val{font-size:22px;font-weight:900;font-variant-numeric:tabular-nums;letter-spacing:-.03em}
.prob-lbl{font-size:9.5px;font-weight:700;color:#3a5570;text-transform:uppercase;letter-spacing:.06em;margin-top:3px}

/* scorer grid */
.scorer-cols{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.scorer-col-title{font-size:11px;font-weight:700;color:#7a9ab8;margin-bottom:7px}
.scorer-item{display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:11.5px;}
.scorer-item:last-child{border:none}
.scorer-name{flex:1;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.scorer-goals{font-size:11px;font-weight:700;color:#e8b820;font-variant-numeric:tabular-nums;flex-shrink:0}
</style>
</head>
<body>

<!-- MODAL OVERLAY -->
<div class="modal-overlay" id="match-modal" role="dialog" aria-modal="true">
  <div class="modal-box">
    <div class="modal-close">
      <button class="modal-close-btn" id="modal-close-btn">ESC Fechar</button>
    </div>
    <div class="modal-body" id="modal-body"><!-- preenchido por JS --></div>
  </div>
</div>

<!-- HEADER -->
<div class="site-header">
  <div class="header-inner">
    <div class="header-top">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="36" height="36">
          <circle cx="12" cy="12" r="10" stroke="#e8b820" stroke-width="1.5"/>
          <polygon points="12,4 14.5,9.5 20.5,9.5 15.8,13.2 17.8,19 12,15.5 6.2,19 8.2,13.2 3.5,9.5 9.5,9.5" fill="none" stroke="#e8b820" stroke-width="1.2" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="header-text">
        <h1>Copa do Mundo 2026 — Painel Preditivo</h1>
        <div class="tagline" id="tagline">Carregando dados…</div>
      </div>
      <div class="header-pills">
        <div class="hpill hpill-y" id="pill-rps"></div>
        <div class="hpill hpill-g" id="pill-acc"></div>
        <div class="hpill hpill-b" id="pill-games"></div>
      </div>
    </div>
    <nav class="tab-bar" id="tab-bar">
      <button class="tab-btn active" data-tab="overview">
        <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        Visão Geral
      </button>
      <button class="tab-btn" data-tab="played">
        <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
        Disputados
      </button>
      <button class="tab-btn" data-tab="upcoming">
        <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/></svg>
        Próximos
      </button>
      <button class="tab-btn" data-tab="bracket">
        <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>
        Classificação
      </button>
      <button class="tab-btn" data-tab="framework">
        <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/></svg>
        Como Funciona
      </button>
      <button class="tab-btn" data-tab="ranking">
        <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        Ranking
      </button>
    </nav>
  </div>
</div>

<!-- MAIN -->
<div class="wrap">

  <!-- VISÃO GERAL -->
  <div class="tab-pane active fade-in" id="tab-overview">
    <div class="kpi-row" id="kpi-cards"></div>
    <div class="grid2 section">
      <div class="glass chart-box">
        <div class="ch-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          Evolução da Precisão ao longo da Copa
          <span class="tip" data-tip="Linha dourada = RPS acumulado do modelo. Meta = abaixo da linha verde. Menor é melhor.">?</span>
        </div>
        <div class="ch-sub">RPS acumulado — quanto mais baixo, mais preciso.</div>
        <div class="ch"><canvas id="chart-rps"></canvas></div>
      </div>
      <div class="glass chart-box">
        <div class="ch-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="12" width="4" height="8"/><rect x="10" y="6" width="4" height="14"/><rect x="17" y="3" width="4" height="17"/></svg>
          Comparação com outras abordagens
          <span class="tip" data-tip="Barra menor = modelo mais preciso. Ensemble combina Elo + Dixon-Coles + Mercado.">?</span>
        </div>
        <div class="ch-sub">Nosso ensemble vs métodos isolados.</div>
        <div class="ch"><canvas id="chart-models"></canvas></div>
      </div>
    </div>
    <div class="grid2 section">
      <div class="glass chart-box">
        <div class="ch-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
          Confiabilidade das previsões
          <span class="tip" data-tip="Pontos na diagonal = modelo bem calibrado. Quando prevemos 70%, acontece ~70% das vezes.">?</span>
        </div>
        <div class="ch-sub">Probabilidade prevista vs frequência real observada.</div>
        <div class="ch"><canvas id="chart-calib"></canvas></div>
      </div>
      <div class="glass chart-box">
        <div class="ch-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>
          Seleções mais fortes da Copa
          <span class="tip" data-tip="Rating Elo calculado sobre ~49 mil jogos históricos desde 1872.">?</span>
        </div>
        <div class="ch-sub">Top 12 por rating Elo (49 mil jogos históricos).</div>
        <div class="ch"><canvas id="chart-elo"></canvas></div>
      </div>
    </div>
    <div class="glass section" style="padding:18px">
      <div class="section-title">
        <span class="section-title-dot"></span>
        Últimos Resultados
      </div>
      <div id="recent-results"></div>
    </div>
  </div>

  <!-- DISPUTADOS -->
  <div class="tab-pane fade-in" id="tab-played">
    <div class="filters" id="played-filters">
      <button class="fbtn active" data-gf="all">Todos os grupos</button>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th data-sk="date">Data</th>
          <th data-sk="group">Grupo</th>
          <th>Jogo</th>
          <th>Resultado</th>
          <th>Placar Previsto</th>
          <th>Probabilidades</th>
          <th data-sk="rps">Precisão<span class="sort-arrow">↕</span></th>
          <th>Acertou?</th>
          <th>Exato?</th>
        </tr></thead>
        <tbody id="played-body"></tbody>
      </table>
    </div>
    <div class="muted small" style="margin-top:9px;padding-left:4px" id="played-count"></div>
  </div>

  <!-- PRÓXIMOS -->
  <div class="tab-pane fade-in" id="tab-upcoming">
    <div class="filters" id="upcoming-filters">
      <button class="fbtn active" data-uf="all">Todos</button>
    </div>
    <div class="gcards" id="upcoming-grid"></div>
    <div class="empty" id="upcoming-empty" style="display:none">Nenhum jogo futuro encontrado.</div>
  </div>

  <!-- CLASSIFICAÇÃO + CHAVEAMENTO -->
  <div class="tab-pane fade-in" id="tab-bracket">
    <div class="section">
      <div class="section-title">
        <span class="section-title-dot"></span>
        Classificação por Grupo
      </div>
      <p class="small muted" style="margin-bottom:16px">
        <span style="color:#00d470">■</span> Verde = classificado &nbsp;
        <span style="color:#e8b820">■</span> Amarelo = na briga por 3° lugar
      </p>
      <div class="sgrids" id="standings-grid"></div>
    </div>
    <div class="section">
      <div class="section-title">
        <span class="section-title-dot"></span>
        Projeção do Chaveamento — Oitavas de Final
      </div>
      <p class="small muted" style="margin-bottom:16px">
        Baseado nos prováveis classificados. WC 2026: 32 equipes nas oitavas.
      </p>
      <div class="bracket-scroll">
        <div class="bracket" id="bracket-view"></div>
      </div>
    </div>
  </div>

  <!-- COMO FUNCIONA -->
  <div class="tab-pane fade-in" id="tab-framework">
    <div class="section">
      <div class="section-title">
        <span class="section-title-dot"></span>
        Como o Modelo Prevê os Jogos
      </div>
      <div class="fw-cards" id="fw-cards-container"></div>
    </div>
    <div class="grid2 section">
      <div class="glass" style="padding:18px">
        <div class="section-title" style="font-size:13px"><span class="section-title-dot"></span>De onde vêm os dados</div>
        <ul class="ds-list" id="ds-list"></ul>
      </div>
      <div class="glass" style="padding:18px">
        <div class="section-title" style="font-size:13px"><span class="section-title-dot"></span>Configuração Atual</div>
        <div id="model-params"></div>
      </div>
    </div>
    <div class="glass section" style="padding:18px">
      <div class="section-title" style="font-size:13px"><span class="section-title-dot"></span>Métricas de Acurácia</div>
      <div id="accuracy-detail"></div>
      <div class="divider"></div>
      <p class="small muted" style="margin-bottom:10px">
        <b style="color:#7a9ab8">Calibração por faixa:</b> azul = previsto · verde/amarelo = real observado. Ideal = iguais.
      </p>
      <div class="calbins" id="calib-bins"></div>
    </div>
  </div>

  <!-- RANKING -->
  <div class="tab-pane fade-in" id="tab-ranking">
    <div class="section">
      <div class="section-title">
        <span class="section-title-dot"></span>
        Ranking de Força — Copa 2026
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>#</th>
            <th>Seleção</th>
            <th data-rk="elo">Elo<span class="sort-arrow">↓</span></th>
            <th data-rk="att">Ataque</th>
            <th data-rk="def">Defesa</th>
            <th data-rk="net">Força Total</th>
            <th>Barra</th>
          </tr></thead>
          <tbody id="ranking-body"></tbody>
        </table>
      </div>
    </div>
  </div>

</div><!-- /wrap -->

<div style="max-width:1320px;margin:0 auto;padding:0 20px;position:relative;z-index:1">
  <div class="footer">
    Copa do Mundo 2026 — Framework Preditivo &nbsp;·&nbsp;
    Elo + Dixon-Coles + Mercado de Apostas &nbsp;·&nbsp;
    Avaliado por RPS (Constantinou &amp; Fenton, 2012) &nbsp;·&nbsp;
    Escanteios/Faltas: Casal et al. 2017 · Bresciani et al. 2021 &nbsp;·&nbsp;
    Fontes: Kaggle · OpenFootball · Odds API
  </div>
</div>

<!-- DATA -->
<script id="pred-data"   type="application/json">__DATA_PRED__</script>
<script id="back-data"   type="application/json">__DATA_BACK__</script>
<script id="rating-data" type="application/json">__DATA_RATINGS__</script>
<script id="aux-data"    type="application/json">__DATA_AUX__</script>

<script>
/* ═══ DATA ═══ */
const PRED = JSON.parse(document.getElementById('pred-data').textContent);
const BACK = JSON.parse(document.getElementById('back-data').textContent);
const RAT  = JSON.parse(document.getElementById('rating-data').textContent);
const AUX  = JSON.parse(document.getElementById('aux-data').textContent);

const pct  = x => (x*100).toFixed(0)+'%';
const pct1 = x => (x*100).toFixed(1)+'%';

const FLAGS = {
  'Argentina':'🇦🇷','Brazil':'🇧🇷','France':'🇫🇷','England':'🏴󠁧󠁢󠁥󠁮󠁧󠁿','Spain':'🇪🇸',
  'Germany':'🇩🇪','Portugal':'🇵🇹','Netherlands':'🇳🇱','Belgium':'🇧🇪','Uruguay':'🇺🇾',
  'Colombia':'🇨🇴','Mexico':'🇲🇽','United States':'🇺🇸','Japan':'🇯🇵','South Korea':'🇰🇷',
  'Morocco':'🇲🇦','Senegal':'🇸🇳','Canada':'🇨🇦','Australia':'🇦🇺','Switzerland':'🇨🇭',
  'Croatia':'🇭🇷','Norway':'🇳🇴','Sweden':'🇸🇪','Ecuador':'🇪🇨','Saudi Arabia':'🇸🇦',
  'Iran':'🇮🇷','Turkey':'🇹🇷','Czech Republic':'🇨🇿','Austria':'🇦🇹','Scotland':'🏴󠁧󠁢󠁳󠁣󠁴󠁿',
  'Ghana':'🇬🇭','Egypt':'🇪🇬','Tunisia':'🇹🇳','Ivory Coast':'🇨🇮','South Africa':'🇿🇦',
  'DR Congo':'🇨🇩','Algeria':'🇩🇿','Bosnia and Herzegovina':'🇧🇦','Haiti':'🇭🇹',
  'Paraguay':'🇵🇾','Qatar':'🇶🇦','Iraq':'🇮🇶','Jordan':'🇯🇴','New Zealand':'🇳🇿',
  'Panama':'🇵🇦','Cape Verde':'🇨🇻','Curaçao':'🇨🇼','Uzbekistan':'🇺🇿',
};
const F    = t => FLAGS[t] || '🏳️';
const short = t => t.replace(' and Herzegovina','').replace('Ivory ','').replace('DR ','');

/* ═══ MODAL ═══ */
const modal       = document.getElementById('match-modal');
const modalBody   = document.getElementById('modal-body');
const modalClose  = document.getElementById('modal-close-btn');

function auxKey(m){ return `${m.date}_${m.home}_${m.away}`; }

function openModal(m) {
  const p   = m.prediction;
  const aux = AUX[auxKey(m)] || null;

  let html = `<div class="modal-header">
    <div class="modal-badge">${m.group||''} · ${m.round||''} · ${m.date}</div>
    <div class="modal-teams">
      <span>${F(m.home)} ${m.home}</span>
      <span style="color:#243448;font-size:13px;font-weight:500">×</span>
      <span>${m.away} ${F(m.away)}</span>
    </div>`;

  if (m.played && m.actual) {
    html += `<div class="modal-score">${m.actual[0]} — ${m.actual[1]}</div>`;
    const e = m.eval||{};
    const ok = e.correct_1x2;
    html += `<div style="font-size:11px;color:${ok?'#00d470':'#e04060'};font-weight:700;margin-bottom:8px">${ok?'Resultado previsto corretamente':'Resultado diferente do previsto'}</div>`;
    html += `<div style="font-size:11px;color:#3a5570;margin-bottom:8px">Previsto: <b style="color:#e8b820">${p.most_likely}</b> &nbsp;·&nbsp; RPS: <b>${e.rps!=null?e.rps.toFixed(3):'—'}</b></div>`;
  } else {
    html += `<div class="modal-score predicted">${p.most_likely}</div>`;
    html += `<div style="font-size:11px;color:#3a5570;margin-bottom:8px">Placar mais provável · xG: ${p.xg_home} – ${p.xg_away}</div>`;
  }

  html += `<div class="modal-pbar-row">
    <div style="flex:${p.p_home};background:#3b82f6;border-radius:3px 0 0 3px"></div>
    <div style="flex:${p.p_draw};background:#8050d0"></div>
    <div style="flex:${p.p_away};background:#e04060;border-radius:0 3px 3px 0"></div>
  </div>
  <div class="modal-pnums">
    <span style="color:#3b82f6;font-weight:700">${pct(p.p_home)} ${short(m.home)}</span>
    <span style="color:#8050d0">${pct(p.p_draw)} Empate</span>
    <span style="color:#e04060;font-weight:700">${short(m.away)} ${pct(p.p_away)}</span>
  </div>
  </div>`; // end modal-header

  /* GOLS (partidas disputadas) */
  if (m.played && aux && aux.goal_events && aux.goal_events.length) {
    html += `<div class="modal-section">
      <div class="modal-section-title">Gols marcados</div>
      <div class="goal-list">`;
    aux.goal_events.forEach(g => {
      const side = g.team===m.home?'h':'a';
      html += `<div class="goal-item goal-team-${side}">
        <span class="goal-min">${g.minute}'</span>
        <span class="goal-name">${F(g.team)} ${g.name}</span>
        ${g.penalty?'<span class="goal-tag goal-tag-pen">PEN</span>':''}
        ${g.own_goal?'<span class="goal-tag goal-tag-og">OG</span>':''}
      </div>`;
    });
    html += '</div></div>';
  } else if (m.played && m.actual && (m.actual[0]+m.actual[1])>0) {
    html += `<div class="modal-section">
      <div class="modal-section-title">Gols marcados</div>
      <div class="goal-list">
        <div class="goal-item" style="color:#3a5570;font-style:italic">Detalhes de gols não disponíveis</div>
      </div></div>`;
  }

  /* PROBABILIDADES EXTRAS */
  if (aux) {
    const btts   = aux.btts;
    const over25 = aux.over_2_5;
    const penp   = aux.penalty_prob;
    html += `<div class="modal-section">
      <div class="modal-section-title">Probabilidades de mercado previstas</div>
      <div class="prob-grid">
        <div class="prob-card">
          <div class="prob-val" style="color:#00d470">${pct(btts)}</div>
          <div class="prob-lbl">Ambas marcam</div>
        </div>
        <div class="prob-card">
          <div class="prob-val" style="color:#3b82f6">${pct(over25)}</div>
          <div class="prob-lbl">Mais de 2.5</div>
        </div>
        <div class="prob-card">
          <div class="prob-val" style="color:#e8b820">${pct(penp)}</div>
          <div class="prob-lbl">Pênalti</div>
        </div>
      </div>
    </div>`;

    /* ESCANTEIOS E FALTAS */
    const c = aux.corners; const f = aux.fouls; const y = aux.yellow_cards;
    const cMax = Math.max(c.home, c.away, 1);
    const fMax = Math.max(f.home, f.away, 1);
    const yMax = Math.max(y.home, y.away, 1);
    html += `<div class="modal-section">
      <div class="modal-section-title">Estatísticas táticas previstas</div>
      <div class="aux-grid">
        <div class="aux-card">
          <div class="aux-card-title">Escanteios (total prev. ${c.total})</div>
          <div class="aux-stat-row">
            <span class="aux-team-label">${short(m.home)}</span>
            <div class="aux-bar-bg"><div class="aux-bar-fill" style="width:${(c.home/cMax*100).toFixed(0)}%;background:#3b82f6"></div></div>
            <span class="aux-val">${c.home}</span>
          </div>
          <div class="aux-stat-row">
            <span class="aux-team-label">${short(m.away)}</span>
            <div class="aux-bar-bg"><div class="aux-bar-fill" style="width:${(c.away/cMax*100).toFixed(0)}%;background:#e04060"></div></div>
            <span class="aux-val">${c.away}</span>
          </div>
        </div>
        <div class="aux-card">
          <div class="aux-card-title">Faltas (total prev. ${f.total})</div>
          <div class="aux-stat-row">
            <span class="aux-team-label">${short(m.home)}</span>
            <div class="aux-bar-bg"><div class="aux-bar-fill" style="width:${(f.home/fMax*100).toFixed(0)}%;background:#3b82f6"></div></div>
            <span class="aux-val">${f.home}</span>
          </div>
          <div class="aux-stat-row">
            <span class="aux-team-label">${short(m.away)}</span>
            <div class="aux-bar-bg"><div class="aux-bar-fill" style="width:${(f.away/fMax*100).toFixed(0)}%;background:#e04060"></div></div>
            <span class="aux-val">${f.away}</span>
          </div>
        </div>
        <div class="aux-card">
          <div class="aux-card-title">Cartões Amarelos (total ${y.total})</div>
          <div class="aux-stat-row">
            <span class="aux-team-label">${short(m.home)}</span>
            <div class="aux-bar-bg"><div class="aux-bar-fill" style="width:${(y.home/yMax*100).toFixed(0)}%;background:#e8b820"></div></div>
            <span class="aux-val">${y.home}</span>
          </div>
          <div class="aux-stat-row">
            <span class="aux-team-label">${short(m.away)}</span>
            <div class="aux-bar-bg"><div class="aux-bar-fill" style="width:${(y.away/yMax*100).toFixed(0)}%;background:#e8b820"></div></div>
            <span class="aux-val">${y.away}</span>
          </div>
        </div>
        <div class="aux-card">
          <div class="aux-card-title">xG esperado</div>
          <div class="aux-stat-row">
            <span class="aux-team-label">${short(m.home)}</span>
            <div class="aux-bar-bg"><div class="aux-bar-fill" style="width:${Math.min(100,(aux.xg.home/4*100)).toFixed(0)}%;background:#3b82f6"></div></div>
            <span class="aux-val">${aux.xg.home}</span>
          </div>
          <div class="aux-stat-row">
            <span class="aux-team-label">${short(m.away)}</span>
            <div class="aux-bar-bg"><div class="aux-bar-fill" style="width:${Math.min(100,(aux.xg.away/4*100)).toFixed(0)}%;background:#e04060"></div></div>
            <span class="aux-val">${aux.xg.away}</span>
          </div>
        </div>
      </div>
    </div>`;

    /* ARTILHEIROS */
    const sh = aux.scorers.home||[];
    const sa = aux.scorers.away||[];
    if (sh.length || sa.length) {
      html += `<div class="modal-section">
        <div class="modal-section-title">Artilheiros ${m.played?'da Copa 2026':'prováveis'}</div>
        <div class="scorer-cols">
          <div>
            <div class="scorer-col-title">${F(m.home)} ${short(m.home)}</div>
            ${sh.map(s=>`<div class="scorer-item">
              <span class="scorer-name">${s.name}</span>
              <span class="scorer-goals">${s.goals} gol${s.goals!==1?'s':''} ${s.pen?'<span style="font-size:9px;color:#3a5570">('+s.pen+' pen)</span>':''}</span>
            </div>`).join('')||'<div class="muted small">— sem dados —</div>'}
          </div>
          <div>
            <div class="scorer-col-title">${F(m.away)} ${short(m.away)}</div>
            ${sa.map(s=>`<div class="scorer-item">
              <span class="scorer-name">${s.name}</span>
              <span class="scorer-goals">${s.goals} gol${s.goals!==1?'s':''} ${s.pen?'<span style="font-size:9px;color:#3a5570">('+s.pen+' pen)</span>':''}</span>
            </div>`).join('')||'<div class="muted small">— sem dados —</div>'}
          </div>
        </div>
      </div>`;
    }
  }

  /* TOP-5 PLACARES */
  if (p.top_scores && p.top_scores.length) {
    html += `<div class="modal-section">
      <div class="modal-section-title">Top placares previstos</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        ${p.top_scores.map((s,i)=>`<div style="background:rgba(5,12,30,.8);border:1px solid rgba(255,255,255,${i===0?.18:.07});border-radius:8px;padding:8px 14px;text-align:center">
          <div style="font-size:17px;font-weight:900;font-variant-numeric:tabular-nums;color:${i===0?'#e8b820':'#4a6080'}">${s.score}</div>
          <div style="font-size:10px;color:#2e4060;margin-top:2px">${(s.prob*100).toFixed(1)}%</div>
        </div>`).join('')}
      </div>
    </div>`;
  }

  modalBody.innerHTML = html;
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modal.classList.remove('open');
  document.body.style.overflow = '';
}

modalClose.addEventListener('click', closeModal);
modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

/* ═══ HEADER ═══ */
document.getElementById('tagline').textContent =
  `${PRED.n_matches} jogos modelados · ${BACK.n_played} já disputados · atualizado em ${PRED.generated_at.split('T')[0]}`;
document.getElementById('pill-rps').innerHTML   = `RPS ${BACK.mean_rps}`;
document.getElementById('pill-acc').innerHTML   = `${pct(BACK.hit_rate_1x2)} acerto`;
document.getElementById('pill-games').innerHTML = `${BACK.n_played}/${PRED.n_matches} jogos`;

/* ═══ TABS ═══ */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => { p.classList.remove('active'); });
    btn.classList.add('active');
    const pane = document.getElementById('tab-' + btn.dataset.tab);
    pane.classList.add('active');
    pane.classList.remove('fade-in');
    void pane.offsetWidth;
    pane.classList.add('fade-in');
  });
});

/* ═══ COUNT-UP ═══ */
function countUp(el, target, duration=900, decimals=0, suffix='') {
  const start = performance.now();
  if (typeof target === 'string') { el.textContent = target; return; }
  (function step(now) {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1-p, 3);
    el.textContent = (target * ease).toFixed(decimals) + suffix;
    if (p < 1) requestAnimationFrame(step);
  })(start);
}

/* ═══ KPI CARDS ═══ */
const rpsScore = BACK.mean_rps < 0.17 ? 95 : BACK.mean_rps < 0.19 ? 80 : BACK.mean_rps < 0.21 ? 60 : 40;
const rpsLabel = BACK.mean_rps < 0.19 ? 'Excelente' : BACK.mean_rps < 0.21 ? 'Bom' : 'Regular';

const KPI_ICONS = {
  chart:`<svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
  target:`<svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`,
  hex:`<svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5"/></svg>`,
  ball:`<svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 00-6.88 2.77M12 2a10 10 0 016.88 2.77M5.12 4.77A9.96 9.96 0 002 12m3.12-7.23L9 10m6-5.23L15 10m-3-8v8m0 0l-6 2m6-2l6 2"/></svg>`,
  bar:`<svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="12" width="4" height="8"/><rect x="10" y="6" width="4" height="14"/><rect x="17" y="3" width="4" height="17"/></svg>`,
};

const kpis = [
  {icon:'chart',id:'kpi-rps',val:BACK.mean_rps,dec:4,suffix:'',cls:'c-gold',glow:'rgba(232,184,32,.14)',
   label:'Precisão RPS',explain:`${rpsLabel} — bom modelo fica entre 0.18 e 0.21.`,
   quality:rpsScore,qColor:'#e8b820',tip:'RPS: padrão científico. Menor = mais preciso.'},
  {icon:'target',id:'kpi-acc',val:BACK.hit_rate_1x2*100,dec:1,suffix:'%',cls:'c-green',glow:'rgba(0,212,112,.1)',
   label:'Resultado Correto',explain:'Jogos onde o resultado (V/E/D) foi previsto certo.',
   quality:BACK.hit_rate_1x2*100,qColor:'#00d470',tip:'Acerto 1X2: resultado mais provável coincidiu com o real.'},
  {icon:'hex',id:'kpi-exact',val:BACK.exact_score_hit_rate*100,dec:1,suffix:'%',cls:'c-cyan',glow:'rgba(0,204,245,.08)',
   label:'Placar Exato',explain:`Acertamos o placar exato em ${Math.round(BACK.exact_score_hit_rate*BACK.n_played)} de ${BACK.n_played} jogos.`,
   quality:BACK.exact_score_hit_rate*200,qColor:'#00ccf5',tip:'Acerto do placar exato (ex: 2-0). Difícil de acertar.'},
  {icon:'ball',id:'kpi-played',val:BACK.n_played,dec:0,suffix:'',cls:'c-purple',glow:'rgba(160,96,240,.1)',
   label:'Jogos Avaliados',explain:`${PRED.n_matches - BACK.n_played} jogos ainda por disputar.`,
   quality:(BACK.n_played/PRED.n_matches)*100,qColor:'#a060f0',tip:'Jogos da fase de grupos já disputados.'},
  {icon:'bar',id:'kpi-vsnaive',val:((BACK.baselines.rps_naive_uniform - BACK.mean_rps)/BACK.baselines.rps_naive_uniform*100),
   dec:1,suffix:'%',cls:'c-orange',glow:'rgba(255,136,32,.1)',
   label:'Melhor que Aleatório',explain:'Comparado a 33%/33%/33% para todos os jogos.',
   quality:70,qColor:'#ff8820',tip:'Quanto mais que um modelo aleatório (33/33/33).'},
];

document.getElementById('kpi-cards').innerHTML = kpis.map(k =>
  `<div class="kpi" style="--glow:${k.glow}">
    <div class="kpi-glow" style="background:${k.glow};filter:blur(28px)"></div>
    ${KPI_ICONS[k.icon]}
    <div class="num ${k.cls}" id="${k.id}">0</div>
    <div class="label">${k.label}<span class="tip" data-tip="${k.tip}">?</span></div>
    <div class="explain">${k.explain}</div>
    <div class="quality-bar"><div class="quality-fill" style="width:${Math.min(k.quality,100)}%;background:${k.qColor}"></div></div>
  </div>`
).join('');
setTimeout(() => { kpis.forEach(k => countUp(document.getElementById(k.id), k.val, 800, k.dec, k.suffix)); }, 100);

/* ═══ CHART DEFAULTS ═══ */
Chart.defaults.color = '#3a5570';
Chart.defaults.borderColor = 'rgba(255,255,255,.05)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;
const gridColor = 'rgba(255,255,255,.04)';

/* CHART: RPS TIMELINE */
(function() {
  const tl = BACK.rps_timeline;
  new Chart(document.getElementById('chart-rps'), {
    type:'line',
    data:{
      labels:tl.map((_,i)=>`J${i+1}`),
      datasets:[
        {label:'RPS/jogo',data:tl.map(d=>d.rps),borderColor:'rgba(74,96,128,.45)',
         backgroundColor:'transparent',pointRadius:2,pointHoverRadius:4,borderWidth:1.5,tension:.3},
        {label:'RPS acumulado',data:tl.map(d=>d.cum_rps),borderColor:'#e8b820',
         backgroundColor:(ctx)=>{const g=ctx.chart.ctx.createLinearGradient(0,0,0,200);
         g.addColorStop(0,'rgba(232,184,32,.14)');g.addColorStop(1,'rgba(232,184,32,.01)');return g;},
         fill:true,pointRadius:0,borderWidth:2.5,tension:.4},
        {label:'Meta < 0.19',data:tl.map(()=>0.19),borderColor:'#00d470',borderDash:[5,4],
         pointRadius:0,borderWidth:1.5,backgroundColor:'transparent'},
        {label:'Ingênuo 0.22',data:tl.map(()=>0.225),borderColor:'#e04060',borderDash:[5,4],
         pointRadius:0,borderWidth:1.5,backgroundColor:'transparent'},
      ]
    },
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{legend:{position:'bottom',labels:{boxWidth:9,padding:12,font:{size:10}}},
        tooltip:{backgroundColor:'rgba(2,8,24,.96)',borderColor:'rgba(255,255,255,.1)',borderWidth:1,padding:9}},
      scales:{y:{min:0,max:.42,grid:{color:gridColor},ticks:{callback:v=>v.toFixed(2)}},
              x:{grid:{display:false},ticks:{maxTicksLimit:12}}}
    }
  });
})();

/* CHART: MODEL COMPARISON */
(function() {
  const b = BACK.baselines;
  const data=[
    {l:'Ensemble',v:BACK.mean_rps,c:'#e8b820'},
    {l:'Dixon-Coles',v:b.rps_dixon_coles_only,c:'#3b82f6'},
    {l:'Elo',v:b.rps_elo_only,c:'#8050d0'},
    {l:'Aleatório',v:b.rps_naive_uniform,c:'#e04060'},
  ];
  new Chart(document.getElementById('chart-models'),{type:'bar',
    data:{labels:data.map(d=>d.l),datasets:[{data:data.map(d=>d.v),
      backgroundColor:data.map(d=>d.c+'22'),borderColor:data.map(d=>d.c),
      borderWidth:1.5,borderRadius:7,borderSkipped:false}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},
        tooltip:{backgroundColor:'rgba(2,8,24,.96)',borderColor:'rgba(255,255,255,.1)',borderWidth:1,padding:9,
          callbacks:{label:ctx=>` RPS: ${ctx.parsed.y.toFixed(4)}`}}},
      scales:{y:{min:.14,max:.24,grid:{color:gridColor},ticks:{callback:v=>v.toFixed(2)}},
              x:{grid:{display:false}}}}
  });
})();

/* CHART: CALIBRATION */
(function() {
  const bins = BACK.calibration_bins;
  new Chart(document.getElementById('chart-calib'),{type:'scatter',
    data:{datasets:[
      {label:'Modelo',data:bins.map(b=>({x:b.pred_mean,y:b.obs_freq})),
       backgroundColor:'rgba(0,170,255,.5)',borderColor:'#00aaff',
       pointRadius:bins.map(b=>Math.min(14,4+b.n/5)),pointHoverRadius:14},
      {label:'Ideal',data:[{x:0,y:0},{x:1,y:1}],type:'line',
       borderColor:'rgba(255,255,255,.12)',borderDash:[5,4],pointRadius:0,
       borderWidth:1.5,backgroundColor:'transparent'}
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'bottom',labels:{boxWidth:9,padding:12,font:{size:10}}},
        tooltip:{backgroundColor:'rgba(2,8,24,.96)',borderColor:'rgba(255,255,255,.1)',borderWidth:1,padding:9,
          callbacks:{label:ctx=>ctx.dataset.label==='Modelo'
            ?`Previsto:${(ctx.parsed.x*100).toFixed(0)}% → Real:${(ctx.parsed.y*100).toFixed(0)}%`:''}}},
      scales:{
        x:{min:0,max:1,grid:{color:gridColor},title:{display:true,text:'Probabilidade prevista',color:'#3a5570'},ticks:{callback:v=>v*100+'%'}},
        y:{min:0,max:1,grid:{color:gridColor},title:{display:true,text:'Frequência real',color:'#3a5570'},ticks:{callback:v=>v*100+'%'}}
      }}
  });
})();

/* CHART: TOP ELO */
(function() {
  const top = RAT.slice(0,12);
  new Chart(document.getElementById('chart-elo'),{type:'bar',
    data:{labels:top.map(t=>short(t.team)),datasets:[{data:top.map(t=>t.elo),
      backgroundColor:top.map((_,i)=>i<3?'rgba(232,184,32,.22)':'rgba(59,130,246,.14)'),
      borderColor:top.map((_,i)=>i<3?'#e8b820':'#3b82f6'),
      borderWidth:1.5,borderRadius:5,borderSkipped:false}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},
        tooltip:{backgroundColor:'rgba(2,8,24,.96)',borderColor:'rgba(255,255,255,.1)',borderWidth:1,padding:9,
          callbacks:{label:ctx=>` Elo: ${ctx.parsed.x.toFixed(0)}`}}},
      scales:{x:{min:1500,grid:{color:gridColor},ticks:{callback:v=>v.toFixed(0)}},
              y:{grid:{display:false},ticks:{font:{size:10}}}}}
  });
})();

/* ═══ RECENT RESULTS ═══ */
(function() {
  const played = PRED.matches.filter(m=>m.played).slice(-12).reverse();
  document.getElementById('recent-results').innerHTML = played.map(m => {
    const p = m.prediction; const e = m.eval||{};
    return `<div class="rr-row" onclick="openModal(${JSON.stringify(m).replace(/</g,'\\u003c')})">
      <span class="small muted" style="width:74px;flex-shrink:0">${m.date}</span>
      <span class="small muted" style="width:26px;flex-shrink:0">${(m.group||'').replace('Group ','')}</span>
      <span style="flex:1;font-weight:700;min-width:0;font-size:13px">${F(m.home)} ${m.home} <span class="muted">×</span> ${m.away} ${F(m.away)}</span>
      <span class="score-big" style="width:50px;text-align:center;flex-shrink:0;color:${e.correct_1x2?'#c8d8ec':'#e04060'}">${m.actual[0]}-${m.actual[1]}</span>
      <span class="muted small" style="width:52px;flex-shrink:0;text-align:center">↗ <b style="color:#e8b820">${p.most_likely}</b></span>
      <span style="width:66px;flex-shrink:0;text-align:center">${e.correct_1x2?'<span class="pill pill-win">acertou</span>':'<span class="pill pill-lose">errou</span>'}</span>
      ${e.exact_score_hit?'<span class="pill pill-score">exato</span>':'<span style="width:50px"></span>'}
      <span class="muted small mono" style="width:42px;text-align:right;flex-shrink:0">${e.rps!=null?e.rps.toFixed(3):'—'}</span>
    </div>`;
  }).join('');
})();

/* ═══ TAB: JOGOS DISPUTADOS ═══ */
(function() {
  const matches = PRED.matches.filter(m=>m.played);
  const groups = [...new Set(matches.map(m=>m.group||''))].sort();
  const fbar = document.getElementById('played-filters');
  groups.forEach(g=>{
    const btn=document.createElement('button');
    btn.className='fbtn'; btn.dataset.gf=g; btn.textContent=g;
    fbar.appendChild(btn);
  });
  let ag='all', sk='date', sd=1;
  function render(){
    let rows = ag==='all' ? matches : matches.filter(m=>m.group===ag);
    rows=[...rows].sort((a,b)=>{
      let va=sk==='rps'?(a.eval?.rps??-1):a[sk]??'';
      let vb=sk==='rps'?(b.eval?.rps??-1):b[sk]??'';
      return (va>vb?1:va<vb?-1:0)*sd;
    });
    const correct=rows.filter(m=>m.eval?.correct_1x2).length;
    const exact=rows.filter(m=>m.eval?.exact_score_hit).length;
    document.getElementById('played-count').textContent=
      `${rows.length} jogos · ${correct} resultados acertados (${pct(correct/Math.max(1,rows.length))}) · ${exact} placares exatos`;
    document.getElementById('played-body').innerHTML=rows.map(m=>{
      const p=m.prediction; const e=m.eval||{};
      const mkt=m.models.market?' <span style="font-size:9px;color:#e89820;opacity:.7" title="odds disponíveis">●</span>':'';
      const mj = JSON.stringify(m).replace(/</g,'\\u003c');
      return `<tr onclick="openModal(${mj})">
        <td class="small muted">${m.date}</td>
        <td class="small muted">${(m.group||'').replace('Group ','')}</td>
        <td style="font-weight:700">${F(m.home)} ${m.home} <span class="muted small">×</span> ${m.away} ${F(m.away)}${mkt}</td>
        <td><span class="score-big" style="color:${e.correct_1x2?'#c8d8ec':'#4a6080'}">${m.actual[0]}-${m.actual[1]}</span></td>
        <td class="mono small" style="color:#e8b820">${p.most_likely}</td>
        <td>
          <div class="pbar"><div class="ph" style="flex:${p.p_home}"></div><div class="pd" style="flex:${p.p_draw}"></div><div class="pa" style="flex:${p.p_away}"></div></div>
          <div class="pnums">${pct(p.p_home)} · ${pct(p.p_draw)} · ${pct(p.p_away)}</div>
        </td>
        <td class="mono small">${e.rps!=null?e.rps.toFixed(3):'—'}</td>
        <td>${e.correct_1x2!=null?(e.correct_1x2?'<span class="pill pill-win">✓</span>':'<span class="pill pill-lose">✕</span>'):'—'}</td>
        <td>${e.exact_score_hit?'<span class="pill pill-score">✓</span>':'<span class="muted small">—</span>'}</td>
      </tr>`;
    }).join('');
  }
  fbar.addEventListener('click',e=>{
    const btn=e.target.closest('.fbtn'); if(!btn)return;
    fbar.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active'); ag=btn.dataset.gf; render();
  });
  document.querySelectorAll('#tab-played th[data-sk]').forEach(th=>{
    th.addEventListener('click',()=>{ const k=th.dataset.sk; sd=sk===k?-sd:1; sk=k; render(); });
  });
  render();
})();

/* ═══ TAB: PRÓXIMOS ═══ */
(function() {
  const upcoming=PRED.matches.filter(m=>!m.played);
  const groups=[...new Set(upcoming.map(m=>m.group||''))].sort();
  const fbar=document.getElementById('upcoming-filters');
  groups.forEach(g=>{
    const btn=document.createElement('button');
    btn.className='fbtn'; btn.dataset.uf=g; btn.textContent=g;
    fbar.appendChild(btn);
  });
  let ag='all';
  function render(){
    const rows=ag==='all'?upcoming:upcoming.filter(m=>m.group===ag);
    const grid=document.getElementById('upcoming-grid');
    const empty=document.getElementById('upcoming-empty');
    if(!rows.length){grid.innerHTML='';empty.style.display='block';return;}
    empty.style.display='none';
    grid.innerHTML=rows.map(m=>{
      const p=m.prediction;
      const hasMkt=!!m.models.market;
      const favH=p.p_home>p.p_away&&p.p_home>p.p_draw;
      const favA=p.p_away>p.p_home&&p.p_away>p.p_draw;
      const mj=JSON.stringify(m).replace(/</g,'\\u003c');
      return `<div class="gcard" onclick="openModal(${mj})">
        <div class="gc-meta">
          <span class="gc-group">${m.group} · ${m.round}</span>
          <span class="gc-date">${m.date}</span>
        </div>
        <div class="gc-matchup">
          <div class="gc-team" style="${favH?'background:rgba(59,130,246,.05);border-radius:7px;padding:4px':''}">
            <div class="tc-name">${F(m.home)} ${m.home}</div>
            <div class="tc-xg">xG ${p.xg_home}</div>
          </div>
          <div class="gc-vs">VS</div>
          <div class="gc-team" style="${favA?'background:rgba(224,64,96,.05);border-radius:7px;padding:4px':''}">
            <div class="tc-name">${m.away} ${F(m.away)}</div>
            <div class="tc-xg">xG ${p.xg_away}</div>
          </div>
        </div>
        <div class="gc-score">${p.most_likely}</div>
        <div class="gc-pbar">
          <div style="flex:${p.p_home};background:#3b82f6;border-radius:2px 0 0 2px"></div>
          <div style="flex:${p.p_draw};background:#8050d0"></div>
          <div style="flex:${p.p_away};background:#e04060;border-radius:0 2px 2px 0"></div>
        </div>
        <div class="gc-pnums">
          <span class="pn-h">${pct(p.p_home)} Casa</span>
          <span>${pct(p.p_draw)} Emp</span>
          <span class="pn-a">Fora ${pct(p.p_away)}</span>
        </div>
        ${hasMkt?`<div class="gc-mkt">Odds de ${m.models.market.n_books} casas</div>`:''}
        <div class="gc-hint">Ver detalhes →</div>
      </div>`;
    }).join('');
  }
  fbar.addEventListener('click',e=>{
    const btn=e.target.closest('.fbtn'); if(!btn)return;
    fbar.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active'); ag=btn.dataset.uf; render();
  });
  render();
})();

/* ═══ TAB: CLASSIFICAÇÃO ═══ */
(function() {
  const teamStats={};
  PRED.matches.forEach(m=>{
    const g=m.group||'';
    [m.home,m.away].forEach(t=>{
      if(!teamStats[t]) teamStats[t]={team:t,group:g,pts:0,gf:0,ga:0,gd:0,w:0,d:0,l:0,pld:0,form:[]};
    });
    if(m.played&&m.actual){
      const [gh,ga]=m.actual;
      teamStats[m.home].pld++; teamStats[m.away].pld++;
      teamStats[m.home].gf+=gh; teamStats[m.home].ga+=ga;
      teamStats[m.away].gf+=ga; teamStats[m.away].ga+=gh;
      teamStats[m.home].gd=teamStats[m.home].gf-teamStats[m.home].ga;
      teamStats[m.away].gd=teamStats[m.away].gf-teamStats[m.away].ga;
      if(gh>ga){teamStats[m.home].pts+=3;teamStats[m.home].w++;teamStats[m.home].form.push('W');teamStats[m.away].l++;teamStats[m.away].form.push('L');}
      else if(gh===ga){teamStats[m.home].pts+=1;teamStats[m.home].d++;teamStats[m.home].form.push('D');teamStats[m.away].pts+=1;teamStats[m.away].d++;teamStats[m.away].form.push('D');}
      else{teamStats[m.away].pts+=3;teamStats[m.away].w++;teamStats[m.away].form.push('W');teamStats[m.home].l++;teamStats[m.home].form.push('L');}
    }
  });
  const groupMap={};
  PRED.matches.forEach(m=>{
    const g=m.group||''; if(!groupMap[g])groupMap[g]=new Set();
    groupMap[g].add(m.home); groupMap[g].add(m.away);
  });
  const groupStandings={};
  Object.keys(groupMap).sort().forEach(g=>{
    groupStandings[g]=[...groupMap[g]]
      .map(t=>teamStats[t]||{team:t,group:g,pts:0,gf:0,ga:0,gd:0,w:0,d:0,l:0,pld:0,form:[]})
      .sort((a,b)=>b.pts-a.pts||b.gd-a.gd||b.gf-a.gf);
  });
  document.getElementById('standings-grid').innerHTML=Object.keys(groupStandings).map(g=>{
    const teams=groupStandings[g];
    const rows=teams.map((t,i)=>{
      const zone=i<2?'qual':i===2?'bubble':'';
      const formH=t.form.slice(-3).map(f=>
        f==='W'?'<div class="fp fp-w">V</div>':f==='D'?'<div class="fp fp-d">E</div>':'<div class="fp fp-l">D</div>'
      ).join('');
      return `<tr>
        <td class="rank">${i+1}</td>
        <td class="${zone}" style="font-weight:${i<2?700:400}">${F(t.team)} ${short(t.team.length>15?t.team.split(' ')[0]+' '+t.team.split(' ')[1]:t.team)}</td>
        <td class="pts">${t.pts}</td>
        <td class="gd">${t.gd>=0?'+'+t.gd:t.gd}</td>
        <td><div class="form-pills">${formH}</div></td>
      </tr>`;
    }).join('');
    return `<div class="sgroup">
      <div class="sg-head">${g}</div>
      <table class="sg-tbl">
        <thead><tr><th></th><th style="text-align:left">Seleção</th><th>Pts</th><th>SG</th><th>Forma</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  }).join('');

  // Bracket
  const qualified={};
  Object.keys(groupStandings).forEach(g=>{
    const letter=g.replace('Group ','');
    qualified[letter]=groupStandings[g].slice(0,2).map(t=>t.team);
  });
  const eloMap={};
  RAT.forEach(r=>{eloMap[r.team]=r.elo});
  const wp=(a,b)=>{const ea=eloMap[a]||1700,eb=eloMap[b]||1700;return 1/(1+Math.pow(10,(eb-ea)/400));};
  const r32=[
    ['A',1,'B',2],['C',1,'D',2],['E',1,'F',2],['G',1,'H',2],
    ['I',1,'J',2],['K',1,'L',2],
    ['B',1,'A',2],['D',1,'C',2],['F',1,'E',2],['H',1,'G',2],
    ['J',1,'I',2],['L',1,'K',2],
  ];
  function getTeam(grp,pos){return qualified[grp]?.[pos-1]||`${pos===1?'1°':'2°'}${grp}`;}
  function matchHTML(tA,tB,tagA='',tagB=''){
    const isStr=t=>typeof t==='string'&&t.length<=3;
    const pA=isStr(tA)||isStr(tB)?0.5:wp(tA,tB); const pB=1-pA; const favA=pA>pB;
    return `<div class="b-match">
      <div class="b-team ${favA?'b-fav':''}">
        ${tagA?`<span class="b-tag">${tagA}</span>`:''}
        <span class="b-name">${F(tA)} ${short(tA.split(' ').slice(0,2).join(' '))}</span>
        <span class="b-prob">${favA?'<b>':''}${(pA*100).toFixed(0)}%${favA?'</b>':''}</span>
      </div>
      <div class="b-team ${!favA?'b-fav':''}">
        ${tagB?`<span class="b-tag">${tagB}</span>`:''}
        <span class="b-name">${F(tB)} ${short(tB.split(' ').slice(0,2).join(' '))}</span>
        <span class="b-prob">${!favA?'<b>':''}${(pB*100).toFixed(0)}%${!favA?'</b>':''}</span>
      </div>
    </div>`;
  }
  function projWinner(tA,tB){const isStr=t=>typeof t==='string'&&t.length<=3;if(isStr(tA)||isStr(tB))return tA;return wp(tA,tB)>=0.5?tA:tB;}
  const r32M=r32.map(([gA,pA,gB,pB])=>({tA:getTeam(gA,pA),tB:getTeam(gB,pB),tagA:`${pA===1?'1°':'2°'}${gA}`,tagB:`${pB===1?'1°':'2°'}${gB}`}));
  const r32W=r32M.map(m=>projWinner(m.tA,m.tB));
  const r16P=[]; for(let i=0;i<r32W.length;i+=2) r16P.push([r32W[i],r32W[i+1]]);
  const r16W=r16P.map(([a,b])=>projWinner(a,b));
  const qfP=[]; for(let i=0;i<r16W.length;i+=2) qfP.push([r16W[i],r16W[i+1]]);
  const qfW=qfP.map(([a,b])=>projWinner(a,b));
  const sfP=[[qfW[0],qfW[1]],[qfW[2],qfW[3]]];
  const sfW=sfP.map(([a,b])=>projWinner(a,b));
  const half1=r32M.slice(0,6); const half2=r32M.slice(6,12);
  const qfM=qfP.map(([a,b])=>({tA:a,tB:b,tagA:'',tagB:''}));
  const sfM=sfP.map(([a,b])=>({tA:a,tB:b,tagA:'',tagB:''}));
  document.getElementById('bracket-view').innerHTML=`
    <div class="b-col"><div class="b-rnd-title">Oitavas — 1ª metade</div>${half1.map(m=>matchHTML(m.tA,m.tB,m.tagA,m.tagB)).join('')}</div>
    <div class="b-col"><div class="b-rnd-title">Oitavas — 2ª metade</div>${half2.map(m=>matchHTML(m.tA,m.tB,m.tagA,m.tagB)).join('')}</div>
    <div class="b-col b-col-narrow" style="justify-content:space-around;display:flex;flex-direction:column">
      <div class="b-rnd-title">Quartas</div>${qfM.map(m=>matchHTML(m.tA,m.tB)).join('')}
    </div>
    <div class="b-col b-col-narrow" style="justify-content:space-around;display:flex;flex-direction:column">
      <div class="b-rnd-title">Semifinais</div>${sfM.map(m=>matchHTML(m.tA,m.tB)).join('')}
    </div>
    <div class="b-col" style="max-width:200px;flex:.38;justify-content:center;display:flex;flex-direction:column">
      <div class="b-rnd-title">Final</div>${matchHTML(sfW[0],sfW[1])}
    </div>`;
})();

/* ═══ TAB: FRAMEWORK ═══ */
(function() {
  const cards=[
    {n:1,title:'Elo de Seleções',text:'Rating de força construído sobre <strong>~49 mil jogos internacionais</strong> (1872–2026). Calibrado para converter diferença de rating em gols esperados.'},
    {n:2,title:'Dixon-Coles',text:'Estima separadamente <strong>ataque e defesa</strong> de cada seleção por máxima verossimilhança. Jogos recentes têm mais peso. Inclui correção para placares baixos (ρ).'},
    {n:3,title:'Mercado de Apostas',text:'Odds de <strong>31+ casas de apostas</strong> com margem removida. Incorpora informação difícil de modelar: lesões de última hora, escalações, clima tático.'},
    {n:4,title:'Ensemble',text:'Junta os três modelos com pesos calibrados: Elo <code>22%</code> · Dixon-Coles <code>43%</code> · Mercado <code>35%</code>. Retorna probabilidades e placar mais provável.'},
    {n:5,title:'Stats Auxiliares',text:'Escanteios e faltas modelados por <strong>regressão Poisson calibrada</strong> (Casal et al. 2017). Cartões, BTTS e Over/Under derivados da força relativa de cada seleção.'},
    {n:6,title:'Sem Vazamento (RPS)',text:'Jogos já disputados foram previstos com dados <strong>anteriores à partida</strong>. Avaliação por RPS — penaliza erros proporcionalmente. Bom modelo: <code>0.18–0.21</code>.'},
  ];
  document.getElementById('fw-cards-container').innerHTML=cards.map(c=>
    `<div class="fw-card"><div class="fw-num">${c.n}</div><h4>${c.title}</h4><p>${c.text}</p></div>`
  ).join('');

  const DS_ICON = `<svg class="ds-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4.03 3-9 3S3 13.66 3 12"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/></svg>`;
  document.getElementById('ds-list').innerHTML=[
    {name:'Kaggle / martj42',desc:'~49 mil resultados internacionais desde 1872. Base principal de treino para Elo e Dixon-Coles.'},
    {name:'OpenFootball',desc:'Resultados e goleadores da Copa 2026, atualizados automaticamente. Grátis.'},
    {name:'The Odds API',desc:'Odds de 31+ casas para jogos futuros. Margem da banca removida matematicamente.'},
    {name:'StatsBomb Open Data',desc:'Eventos e xG de partidas históricas para validação e calibração.'},
    {name:'Casal et al. (2017)',desc:'Modelo de escanteios calibrado para futebol internacional. Base para stats auxiliares.'},
  ].map(d=>`<li class="ds-item">${DS_ICON}<div class="ds-info"><strong>${d.name}</strong><p>${d.desc}</p></div></li>`).join('');

  const w=PRED.weights;
  document.getElementById('model-params').innerHTML=[
    {n:'Peso Elo (com odds)',v:w.elo,c:'#3b82f6'},
    {n:'Peso Dixon-Coles',v:w.dixon_coles,c:'#e8b820'},
    {n:'Peso Mercado',v:w.market,c:'#00d470'},
    {n:'Peso Elo (sem odds)',v:w.sem_mercado.elo,c:'#3b82f6'},
    {n:'Peso DC (sem odds)',v:w.sem_mercado.dixon_coles,c:'#e8b820'},
  ].map(r=>`<div class="mbar-row">
    <span class="mbar-name">${r.n}</span>
    <div class="mbar-bg"><div class="mbar-fill" style="width:${r.v*100}%;background:${r.c}"></div></div>
    <span class="mbar-val">${(r.v*100).toFixed(0)}%</span>
  </div>`).join('')+`<div class="divider"></div>
  <p class="small muted">β Elo: ${PRED.elo_calibration.beta_sup_per_elo.toFixed(6)} &nbsp;·&nbsp; DC ρ: ${PRED.dc_params.rho.toFixed(4)}</p>`;

  const b=BACK.baselines;
  document.getElementById('accuracy-detail').innerHTML=[
    {n:'Ensemble (nosso)',v:BACK.mean_rps,c:'#e8b820',max:.25},
    {n:'Só Dixon-Coles',v:b.rps_dixon_coles_only,c:'#3b82f6',max:.25},
    {n:'Só Elo',v:b.rps_elo_only,c:'#8050d0',max:.25},
    {n:'Aleatório (33/33/33)',v:b.rps_naive_uniform,c:'#e04060',max:.25},
    {n:'Resultado certo',v:BACK.hit_rate_1x2,c:'#00d470',max:1},
    {n:'Placar exato',v:BACK.exact_score_hit_rate,c:'#00ccf5',max:1},
  ].map(r=>`<div class="mbar-row">
    <span class="mbar-name">${r.n}</span>
    <div class="mbar-bg"><div class="mbar-fill" style="width:${(r.v/r.max)*100}%;background:${r.c}"></div></div>
    <span class="mbar-val mono">${r.v<.5?r.v.toFixed(4):pct(r.v)}</span>
  </div>`).join('');

  const bins=BACK.calibration_bins;
  document.getElementById('calib-bins').innerHTML=bins.map(b=>{
    const hp=Math.round(b.pred_mean*50); const ho=Math.round(b.obs_freq*50);
    const good=Math.abs(b.pred_mean-b.obs_freq)<0.12; const col=good?'#00d470':'#e8b820';
    return `<div class="calbin">
      <div class="cbl">${b.bin}</div>
      <div class="cbars">
        <div class="cbar" style="height:${hp}px;background:#3b82f6"></div>
        <div class="cbar" style="height:${ho}px;background:${col}"></div>
      </div>
      <div class="cval" style="color:${col}">${(b.obs_freq*100).toFixed(0)}%</div>
      <div class="cn">n=${b.n}</div>
    </div>`;
  }).join('');
})();

/* ═══ TAB: RANKING ═══ */
(function() {
  let rk='elo', rd=-1;
  function render(){
    const rows=[...RAT].sort((a,b)=>(a[rk]>b[rk]?1:a[rk]<b[rk]?-1:0)*rd);
    const maxE=Math.max(...rows.map(r=>r.elo));
    document.getElementById('ranking-body').innerHTML=rows.map((r,i)=>{
      const bw=(r.elo/maxE*100).toFixed(1);
      const nc=r.net>=2.2?'#e8b820':r.net>=1.8?'#00d470':r.net>=1.2?'#3b82f6':'#3a5570';
      return `<tr>
        <td class="muted small">${i+1}</td>
        <td style="font-weight:700">${F(r.team)} ${r.team}</td>
        <td class="mono" style="font-weight:800;color:#c8d8ec">${r.elo}</td>
        <td class="mono" style="color:${r.att>=0?'#00d470':'#e04060'}">${r.att>=0?'+':''}${r.att}</td>
        <td class="mono" style="color:${r.def>=0?'#00d470':'#e04060'}">${r.def>=0?'+':''}${r.def}</td>
        <td class="mono" style="font-weight:800;color:${nc}">${r.net>=0?'+':''}${r.net}</td>
        <td><div class="rank-bar-bg"><div class="rank-bar-fill" style="width:${bw}%"></div></div></td>
      </tr>`;
    }).join('');
  }
  document.querySelectorAll('#tab-ranking th[data-rk]').forEach(th=>{
    th.addEventListener('click',()=>{ const k=th.dataset.rk; rd=rk===k?-rd:-1; rk=k; render(); });
  });
  render();
})();
</script>
</body>
</html>"""


def main():
    pred    = json.load(open(ANALYSIS / "wc2026_predictions.json", encoding="utf-8"))
    back    = json.load(open(ANALYSIS / "wc2026_backtest.json",    encoding="utf-8"))
    ratings = build_ratings()

    aux_path = ANALYSIS / "wc2026_aux_stats.json"
    aux = json.load(open(aux_path, encoding="utf-8")) if aux_path.exists() else {}

    html = (HTML_TEMPLATE
            .replace("__DATA_PRED__",    json.dumps(pred,    ensure_ascii=False))
            .replace("__DATA_BACK__",    json.dumps(back,    ensure_ascii=False))
            .replace("__DATA_RATINGS__", json.dumps(ratings, ensure_ascii=False))
            .replace("__DATA_AUX__",     json.dumps(aux,     ensure_ascii=False)))

    out = ROOT / "output" / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado: {out}  ({len(html)//1024} KB)")
    print(f"  {pred['n_matches']} jogos · {back['n_played']} avaliados · "
          f"RPS {back['mean_rps']} · Acerto {back['hit_rate_1x2']:.1%}")


if __name__ == "__main__":
    main()

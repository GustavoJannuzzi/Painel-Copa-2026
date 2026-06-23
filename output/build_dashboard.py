"""
Gera output/index.html — painel visual self-contained da Copa 2026.
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
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
/* ── RESET & BASE ───────────────────────────────── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  background:#020810;
  color:#d0dff0;
  font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  line-height:1.5;
  min-height:100vh;
  overflow-x:hidden;
}

/* ── BACKGROUND GRID ────────────────────────────── */
body::before{
  content:'';
  position:fixed;inset:0;
  background-image:
    linear-gradient(rgba(0,180,255,.04) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,180,255,.04) 1px,transparent 1px);
  background-size:40px 40px;
  pointer-events:none;z-index:0;
}
body::after{
  content:'';
  position:fixed;inset:0;
  background:radial-gradient(ellipse 80% 60% at 50% -10%,rgba(0,100,255,.12),transparent),
             radial-gradient(ellipse 50% 40% at 100% 80%,rgba(120,0,255,.08),transparent),
             radial-gradient(ellipse 50% 40% at 0% 60%,rgba(0,200,100,.06),transparent);
  pointer-events:none;z-index:0;
}

/* ── GLASS MIXIN ────────────────────────────────── */
.glass{
  background:rgba(8,18,40,.65);
  backdrop-filter:blur(16px);
  -webkit-backdrop-filter:blur(16px);
  border:1px solid rgba(255,255,255,.08);
  border-radius:16px;
}
.glass-bright{
  background:rgba(10,24,55,.75);
  backdrop-filter:blur(20px);
  -webkit-backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,.12);
  border-radius:16px;
}

/* ── HEADER ─────────────────────────────────────── */
.site-header{
  position:sticky;top:0;z-index:200;
  background:rgba(2,8,16,.85);
  backdrop-filter:blur(24px);
  -webkit-backdrop-filter:blur(24px);
  border-bottom:1px solid rgba(255,255,255,.07);
}
.header-inner{
  max-width:1320px;margin:0 auto;
  padding:16px 24px 0;
}
.header-top{
  display:flex;align-items:center;gap:16px;flex-wrap:wrap;
}
.logo{
  font-size:32px;
  filter:drop-shadow(0 0 18px rgba(250,200,20,.6));
  flex-shrink:0;
}
.header-text h1{
  font-size:20px;font-weight:800;letter-spacing:-.025em;
  background:linear-gradient(100deg,#f0c030 0%,#ff9500 50%,#ff4060 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
}
.header-text .tagline{font-size:11px;color:#5a7090;margin-top:2px}
.header-pills{
  margin-left:auto;display:flex;gap:8px;flex-wrap:wrap;
}
.hpill{
  display:inline-flex;align-items:center;gap:5px;
  padding:4px 12px;border-radius:20px;
  font-size:11px;font-weight:700;
  border:1px solid;backdrop-filter:blur(8px);
  transition:all .2s;
}
.hpill:hover{transform:translateY(-1px)}
.hpill-g{background:rgba(0,255,130,.07);border-color:rgba(0,255,130,.25);color:#00e57a}
.hpill-y{background:rgba(240,192,48,.07);border-color:rgba(240,192,48,.25);color:#f0c030}
.hpill-b{background:rgba(0,180,255,.07);border-color:rgba(0,180,255,.25);color:#00b4ff}

/* ── TABS ───────────────────────────────────────── */
.tab-bar{
  display:flex;gap:4px;padding:14px 0 0;
  overflow-x:auto;scrollbar-width:none;
}
.tab-bar::-webkit-scrollbar{display:none}
.tab-btn{
  position:relative;
  background:transparent;border:none;
  color:#4a6080;cursor:pointer;
  font-size:12px;font-weight:700;
  padding:8px 16px;border-radius:10px 10px 0 0;
  white-space:nowrap;letter-spacing:.01em;
  transition:all .2s;
}
.tab-btn::after{
  content:'';position:absolute;bottom:0;left:50%;right:50%;
  height:2px;background:linear-gradient(90deg,#f0c030,#ff9500);
  border-radius:2px;transition:all .25s;
}
.tab-btn:hover{color:#90a8c0}
.tab-btn.active{color:#f0c030}
.tab-btn.active::after{left:12px;right:12px}

/* ── LAYOUT ─────────────────────────────────────── */
.wrap{
  max-width:1320px;margin:0 auto;
  padding:28px 20px 100px;
  position:relative;z-index:1;
}
.tab-pane{display:none}
.tab-pane.active{display:block}
.section{margin-bottom:28px}
.section-title{
  font-size:16px;font-weight:800;
  color:#d0dff0;letter-spacing:-.01em;
  margin-bottom:18px;
  display:flex;align-items:center;gap:8px;
}
.section-title::after{
  content:'';flex:1;height:1px;
  background:linear-gradient(90deg,rgba(255,255,255,.1),transparent);
  margin-left:8px;
}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
@media(max-width:1024px){.grid4{grid-template-columns:repeat(2,1fr)}}
@media(max-width:860px){.grid2,.grid3,.grid4{grid-template-columns:1fr}}

/* ── KPI CARDS ──────────────────────────────────── */
.kpi-row{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  gap:14px;margin-bottom:28px;
}
.kpi{
  position:relative;overflow:hidden;
  background:rgba(8,18,40,.7);
  backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,.08);
  border-radius:16px;
  padding:20px;
  cursor:default;
  transition:transform .2s,border-color .2s,box-shadow .2s;
}
.kpi:hover{
  transform:translateY(-3px);
  border-color:rgba(255,255,255,.18);
  box-shadow:0 8px 40px rgba(0,0,0,.4),0 0 0 1px rgba(255,255,255,.06);
}
.kpi .glow{
  position:absolute;top:-30px;right:-30px;
  width:100px;height:100px;border-radius:50%;
  opacity:.12;blur(30px);
  transition:opacity .2s;
}
.kpi:hover .glow{opacity:.22}
.kpi .icon{font-size:20px;margin-bottom:10px;display:block}
.kpi .num{
  font-size:34px;font-weight:900;
  letter-spacing:-.04em;line-height:1;
  font-variant-numeric:tabular-nums;
}
.kpi .num.c-gold{color:#f0c030;text-shadow:0 0 30px rgba(240,192,48,.3)}
.kpi .num.c-green{color:#00e57a;text-shadow:0 0 30px rgba(0,229,122,.25)}
.kpi .num.c-cyan{color:#00d4ff;text-shadow:0 0 30px rgba(0,212,255,.25)}
.kpi .num.c-purple{color:#b070ff;text-shadow:0 0 30px rgba(176,112,255,.25)}
.kpi .num.c-orange{color:#ff9030;text-shadow:0 0 30px rgba(255,144,48,.25)}
.kpi .label{font-size:12px;font-weight:700;color:#90a8c0;margin-top:8px;text-transform:uppercase;letter-spacing:.06em}
.kpi .explain{font-size:11px;color:#3a5070;margin-top:4px;line-height:1.4}
.kpi .quality-bar{
  height:3px;margin-top:12px;border-radius:2px;
  background:rgba(255,255,255,.07);overflow:hidden;
}
.kpi .quality-fill{height:100%;border-radius:2px;transition:width 1s ease}

/* ── TOOLTIP ────────────────────────────────────── */
.tip{
  position:relative;display:inline-block;
  width:14px;height:14px;border-radius:50%;
  background:rgba(255,255,255,.08);
  color:#5a7090;font-size:9px;font-weight:700;
  text-align:center;line-height:14px;cursor:help;
  border:1px solid rgba(255,255,255,.12);
  vertical-align:middle;margin-left:4px;
}
.tip::before{
  content:attr(data-tip);
  position:absolute;bottom:calc(100% + 8px);left:50%;
  transform:translateX(-50%);
  background:rgba(5,15,35,.95);
  border:1px solid rgba(255,255,255,.15);
  border-radius:8px;padding:8px 12px;
  width:220px;font-size:11px;color:#90a8c0;
  line-height:1.5;white-space:normal;
  pointer-events:none;opacity:0;transition:opacity .15s;
  z-index:999;
}
.tip:hover::before{opacity:1}

/* ── CHART CONTAINERS ───────────────────────────── */
.chart-box{
  position:relative;
  padding:20px;
}
.chart-box .ch-title{
  font-size:13px;font-weight:700;color:#90a8c0;
  margin-bottom:14px;display:flex;align-items:center;gap:6px;
}
.chart-box .ch-sub{font-size:11px;color:#3a5070;margin-top:-10px;margin-bottom:12px}
.ch{position:relative;height:230px}
.ch-sm{position:relative;height:190px}

/* ── TABLES ─────────────────────────────────────── */
.tbl-wrap{
  overflow-x:auto;
  border-radius:14px;
  border:1px solid rgba(255,255,255,.07);
}
table{width:100%;border-collapse:collapse;font-size:12.5px}
thead th{
  background:rgba(5,14,32,.8);
  color:#4a6080;font-size:10px;font-weight:700;
  text-transform:uppercase;letter-spacing:.07em;
  padding:11px 14px;white-space:nowrap;
  border-bottom:1px solid rgba(255,255,255,.07);
  cursor:pointer;user-select:none;
  transition:color .15s;
}
thead th:hover{color:#90a8c0}
thead th .sort-arrow{opacity:.4;margin-left:3px}
tbody td{
  padding:11px 14px;
  border-bottom:1px solid rgba(255,255,255,.04);
  vertical-align:middle;white-space:nowrap;
}
tbody tr:last-child td{border-bottom:none}
tbody tr{transition:background .12s}
tbody tr:hover td{background:rgba(255,255,255,.03)}

/* ── PROB BAR ───────────────────────────────────── */
.pbar{display:flex;height:6px;border-radius:3px;overflow:hidden;gap:1px}
.pbar .ph{background:#3b82f6}
.pbar .pd{background:#9060e0}
.pbar .pa{background:#f04060}
.pnums{font-size:10px;color:#4a6080;margin-top:3px;font-variant-numeric:tabular-nums}

/* ── PILLS ──────────────────────────────────────── */
.pill{
  display:inline-flex;align-items:center;gap:3px;
  padding:2px 9px;border-radius:20px;
  font-size:10px;font-weight:700;border:1px solid;
}
.pill-win{background:rgba(0,229,122,.1);color:#00e57a;border-color:rgba(0,229,122,.3)}
.pill-lose{background:rgba(240,64,96,.1);color:#f04060;border-color:rgba(240,64,96,.25)}
.pill-score{background:rgba(240,192,48,.1);color:#f0c030;border-color:rgba(240,192,48,.3)}
.pill-pend{background:rgba(90,112,144,.1);color:#5a7090;border-color:rgba(90,112,144,.25)}

/* ── FILTERS ────────────────────────────────────── */
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}
.fbtn{
  background:rgba(8,18,40,.8);color:#4a6080;
  border:1px solid rgba(255,255,255,.07);
  border-radius:8px;padding:6px 14px;
  cursor:pointer;font-size:11px;font-weight:700;
  transition:all .15s;letter-spacing:.03em;
}
.fbtn:hover{color:#90a8c0;border-color:rgba(255,255,255,.14)}
.fbtn.active{
  background:rgba(240,192,48,.1);
  color:#f0c030;border-color:rgba(240,192,48,.35);
}

/* ── GAME CARDS (próximos) ──────────────────────── */
.gcards{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
  gap:14px;
}
.gcard{
  position:relative;overflow:hidden;
  background:rgba(8,18,40,.7);
  backdrop-filter:blur(16px);
  border:1px solid rgba(255,255,255,.08);
  border-radius:16px;padding:18px;
  transition:transform .2s,border-color .2s,box-shadow .2s;
}
.gcard:hover{
  transform:translateY(-3px);
  border-color:rgba(240,192,48,.3);
  box-shadow:0 10px 40px rgba(0,0,0,.5),0 0 30px rgba(240,192,48,.05);
}
.gcard::before{
  content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,.03),transparent 60%);
  pointer-events:none;
}
.gc-meta{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:14px;
}
.gc-group{font-size:10px;font-weight:700;color:#4a6080;text-transform:uppercase;letter-spacing:.07em}
.gc-date{font-size:11px;color:#2e4060}
.gc-matchup{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.gc-team{flex:1;text-align:center}
.gc-team .tc-name{font-size:14px;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gc-team .tc-xg{font-size:10px;color:#4a6080;margin-top:2px}
.gc-vs{color:#2e4060;font-size:13px;font-weight:700;flex-shrink:0}
.gc-score{
  text-align:center;
  font-size:28px;font-weight:900;letter-spacing:-.03em;
  color:#f0c030;
  text-shadow:0 0 24px rgba(240,192,48,.4);
  margin:4px 0 10px;
  font-variant-numeric:tabular-nums;
}
.gc-pbar{display:flex;height:5px;border-radius:3px;overflow:hidden;margin-bottom:6px;gap:1px}
.gc-pnums{
  display:flex;justify-content:space-between;
  font-size:10px;font-variant-numeric:tabular-nums;
  color:#4a6080;
}
.gc-pnums .pn-h{color:#3b82f6;font-weight:700}
.gc-pnums .pn-a{color:#f04060;font-weight:700}
.gc-mkt{
  font-size:10px;color:#3a5070;margin-top:8px;
  display:flex;align-items:center;gap:4px;
}

/* ── STANDINGS ──────────────────────────────────── */
.sgrids{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(255px,1fr));
  gap:14px;
}
.sgroup{
  background:rgba(8,18,40,.7);
  border:1px solid rgba(255,255,255,.07);
  border-radius:14px;overflow:hidden;
  transition:border-color .2s;
}
.sgroup:hover{border-color:rgba(255,255,255,.13)}
.sg-head{
  background:rgba(5,12,30,.8);padding:10px 14px;
  font-size:10px;font-weight:700;color:#4a6080;
  text-transform:uppercase;letter-spacing:.08em;
  border-bottom:1px solid rgba(255,255,255,.06);
}
.sg-tbl{width:100%;border-collapse:collapse;font-size:11.5px}
.sg-tbl td{padding:7px 10px;border-bottom:1px solid rgba(255,255,255,.04)}
.sg-tbl tr:last-child td{border:none}
.sg-tbl .rank{color:#2e4060;width:16px;font-weight:700}
.sg-tbl .qual{border-left:3px solid #00e57a}
.sg-tbl .bubble{border-left:3px solid #f0c030}
.sg-tbl .pts{font-weight:800;color:#d0dff0;text-align:center;width:24px}
.sg-tbl .gd{color:#4a6080;text-align:center;width:28px;font-size:10.5px}
.form-pills{display:flex;gap:2px}
.fp{width:13px;height:13px;border-radius:3px;font-size:8px;font-weight:800;display:flex;align-items:center;justify-content:center}
.fp-w{background:rgba(0,229,122,.2);color:#00e57a;border:1px solid rgba(0,229,122,.3)}
.fp-d{background:rgba(144,96,224,.15);color:#9060e0;border:1px solid rgba(144,96,224,.3)}
.fp-l{background:rgba(240,64,96,.15);color:#f04060;border:1px solid rgba(240,64,96,.25)}

/* ── BRACKET ────────────────────────────────────── */
.bracket-scroll{overflow-x:auto;padding-bottom:12px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.1) transparent}
.bracket{display:flex;gap:12px;min-width:1200px;align-items:stretch}
.b-col{flex:1;display:flex;flex-direction:column;gap:0}
.b-col-narrow{flex:.55}
.b-rnd-title{
  font-size:9px;font-weight:800;color:#3a5070;
  text-transform:uppercase;letter-spacing:.1em;
  text-align:center;padding:8px 0 10px;
  border-bottom:1px solid rgba(255,255,255,.06);
  margin-bottom:6px;
}
.b-match{
  background:rgba(5,14,32,.7);
  border:1px solid rgba(255,255,255,.07);
  border-radius:10px;padding:8px 10px;
  margin:3px 0;
  transition:border-color .15s;
  position:relative;overflow:hidden;
}
.b-match:hover{border-color:rgba(240,192,48,.3)}
.b-match::before{
  content:'';position:absolute;left:0;top:0;bottom:0;width:2px;
  background:linear-gradient(180deg,transparent,rgba(240,192,48,.3),transparent);
}
.b-team{
  display:flex;justify-content:space-between;align-items:center;
  padding:4px 0;font-size:11px;
}
.b-team:first-child{border-bottom:1px solid rgba(255,255,255,.05)}
.b-name{font-weight:700;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.b-tag{font-size:9px;color:#2e4060;margin-right:4px;flex-shrink:0}
.b-prob{font-size:10px;color:#4a6080;font-variant-numeric:tabular-nums;flex-shrink:0}
.b-fav .b-name{color:#f0c030}
.b-fav .b-prob{color:#f0c030;font-weight:700}

/* ── FRAMEWORK CARDS ────────────────────────────── */
.fw-cards{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
  gap:14px;margin-bottom:28px;
}
.fw-card{
  background:rgba(8,18,40,.65);
  border:1px solid rgba(255,255,255,.08);
  border-radius:14px;padding:20px;
  transition:border-color .2s,transform .2s;
  position:relative;overflow:hidden;
}
.fw-card:hover{border-color:rgba(240,192,48,.25);transform:translateY(-2px)}
.fw-card::before{
  content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,.02),transparent);pointer-events:none;
}
.fw-num{
  width:32px;height:32px;border-radius:50%;
  background:linear-gradient(135deg,#f0c030,#ff9030);
  color:#000;font-weight:900;font-size:14px;
  display:flex;align-items:center;justify-content:center;
  margin-bottom:12px;
  box-shadow:0 4px 14px rgba(240,192,48,.3);
}
.fw-card h4{font-size:14px;font-weight:800;color:#d0dff0;margin-bottom:8px}
.fw-card p{font-size:12px;color:#4a6080;line-height:1.65}
.fw-card code{
  background:rgba(240,192,48,.1);padding:1px 5px;
  border-radius:4px;font-size:11px;color:#f0c030;
  border:1px solid rgba(240,192,48,.2);
}

/* ── METRIC BARS ────────────────────────────────── */
.mbar-row{
  display:flex;align-items:center;gap:12px;
  padding:9px 0;border-bottom:1px solid rgba(255,255,255,.04);
  font-size:12px;
}
.mbar-row:last-child{border:none}
.mbar-name{width:130px;flex-shrink:0;color:#5a7090}
.mbar-bg{
  flex:1;height:6px;border-radius:3px;
  background:rgba(255,255,255,.06);overflow:hidden;
}
.mbar-fill{height:100%;border-radius:3px;transition:width .8s ease}
.mbar-val{width:52px;text-align:right;font-weight:700;font-variant-numeric:tabular-nums;color:#90a8c0}

/* ── DATA SOURCES ───────────────────────────────── */
.ds-list{list-style:none}
.ds-item{
  display:flex;gap:12px;align-items:flex-start;
  padding:11px 0;border-bottom:1px solid rgba(255,255,255,.05);
}
.ds-item:last-child{border:none}
.ds-icon{font-size:20px;flex-shrink:0;margin-top:1px}
.ds-info strong{font-size:13px;color:#90a8c0;font-weight:700}
.ds-info p{font-size:11px;color:#3a5070;margin-top:2px;line-height:1.5}

/* ── CALIBRATION BINS ───────────────────────────── */
.calbins{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.calbin{
  flex:1;min-width:58px;
  background:rgba(5,14,32,.7);
  border:1px solid rgba(255,255,255,.07);
  border-radius:10px;padding:10px 6px;
  text-align:center;font-size:10.5px;
  transition:border-color .15s;
}
.calbin:hover{border-color:rgba(255,255,255,.15)}
.calbin .cbl{color:#3a5070;margin-bottom:6px;font-size:9px;text-transform:uppercase;letter-spacing:.05em}
.calbin .cbars{height:56px;display:flex;align-items:flex-end;justify-content:center;gap:4px;margin-bottom:4px}
.calbin .cbar{width:12px;border-radius:3px 3px 0 0}
.calbin .cval{font-weight:800;font-size:12px}
.calbin .cn{font-size:9px;color:#2e4060}

/* ── RANKING ────────────────────────────────────── */
.rank-bar-bg{width:100px;height:5px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden;display:inline-block;vertical-align:middle}
.rank-bar-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,#3b82f6,#f0c030)}

/* ── MISC ───────────────────────────────────────── */
.mono{font-variant-numeric:tabular-nums}
.muted{color:#4a6080}
.small{font-size:11px}
.score-big{font-size:22px;font-weight:900;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.scroll-y{overflow-y:auto;max-height:500px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.1) transparent}
.divider{border:none;border-top:1px solid rgba(255,255,255,.06);margin:18px 0}
.empty{color:#2e4060;text-align:center;padding:48px;font-size:14px}
.footer{
  color:#2e4060;font-size:11px;
  margin-top:40px;padding:16px 0;
  border-top:1px solid rgba(255,255,255,.05);
  line-height:1.7;
}
.fade-in{animation:fadeIn .4s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}

/* ── SHIMMER ANIMATION ──────────────────────────── */
@keyframes shimmer{
  0%{background-position:200% center}
  100%{background-position:-200% center}
}
.shimmer-text{
  background:linear-gradient(90deg,#4a6080 0%,#d0dff0 50%,#4a6080 100%);
  background-size:200% auto;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
  animation:shimmer 3s linear infinite;
}

/* ── PULSE DOT ──────────────────────────────────── */
.pulse-dot{
  width:7px;height:7px;border-radius:50%;
  background:#00e57a;display:inline-block;
  box-shadow:0 0 0 0 rgba(0,229,122,.4);
  animation:pulseDot 2s infinite;
}
@keyframes pulseDot{
  0%{box-shadow:0 0 0 0 rgba(0,229,122,.4)}
  70%{box-shadow:0 0 0 6px rgba(0,229,122,0)}
  100%{box-shadow:0 0 0 0 rgba(0,229,122,0)}
}

/* ── RECENT RESULT ROWS ─────────────────────────── */
.rr-row{
  display:flex;align-items:center;gap:10px;
  padding:9px 0;border-bottom:1px solid rgba(255,255,255,.04);
  font-size:12px;
  transition:background .12s;
}
.rr-row:last-child{border:none}
.rr-row:hover{background:rgba(255,255,255,.02);border-radius:8px;padding-left:6px}

/* ── COUNT UP ANIMATION ─────────────────────────── */
.countup{display:inline-block}
</style>
</head>
<body>

<!-- ══ HEADER ══ -->
<div class="site-header">
  <div class="header-inner">
    <div class="header-top">
      <div class="logo">⚽</div>
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
      <button class="tab-btn active" data-tab="overview">🏆 Visão Geral</button>
      <button class="tab-btn" data-tab="played">⚽ Jogos Disputados</button>
      <button class="tab-btn" data-tab="upcoming">🔮 Próximos Jogos</button>
      <button class="tab-btn" data-tab="bracket">🌳 Chaveamento</button>
      <button class="tab-btn" data-tab="framework">🔬 Como Funciona</button>
      <button class="tab-btn" data-tab="ranking">📈 Ranking de Força</button>
    </nav>
  </div>
</div>

<!-- ══ MAIN ══ -->
<div class="wrap">

  <!-- ══════════════════ VISÃO GERAL ══════════════════ -->
  <div class="tab-pane active fade-in" id="tab-overview">

    <div class="kpi-row" id="kpi-cards"></div>

    <div class="grid2 section">
      <div class="glass chart-box">
        <div class="ch-title">📉 Evolução da Precisão ao longo da Copa<span class="tip" data-tip="Linha dourada = precisão acumulada do modelo. Quanto mais próxima da linha verde (meta), melhor. Cada ponto cinza = erro num jogo individual.">?</span></div>
        <div class="ch-sub">RPS acumulado — quanto mais baixo, mais preciso. Meta: abaixo da linha verde.</div>
        <div class="ch"><canvas id="chart-rps"></canvas></div>
      </div>
      <div class="glass chart-box">
        <div class="ch-title">🏅 Comparação com outras abordagens<span class="tip" data-tip="Compara o ensemble (combinação de modelos) com cada modelo individualmente e com uma previsão aleatória. Barra menor = modelo melhor.">?</span></div>
        <div class="ch-sub">Nosso ensemble vs métodos isolados. Barra menor = mais preciso.</div>
        <div class="ch"><canvas id="chart-models"></canvas></div>
      </div>
    </div>

    <div class="grid2 section">
      <div class="glass chart-box">
        <div class="ch-title">⚖️ Confiabilidade das previsões<span class="tip" data-tip="Pontos próximos da diagonal = modelo bem calibrado. Exemplo: quando prevemos 70%, o time venceu de fato ~70% das vezes.">?</span></div>
        <div class="ch-sub">Quando prevemos X% de chance, isso acontece de fato X% das vezes?</div>
        <div class="ch"><canvas id="chart-calib"></canvas></div>
      </div>
      <div class="glass chart-box">
        <div class="ch-title">💪 Seleções mais fortes da Copa<span class="tip" data-tip="Rating Elo: calculado sobre 49 mil jogos históricos. Quanto maior, mais forte. As 3 primeiras têm barra dourada.">?</span></div>
        <div class="ch-sub">Top 12 seleções por rating Elo (calculado em 49 mil jogos históricos).</div>
        <div class="ch"><canvas id="chart-elo"></canvas></div>
      </div>
    </div>

    <div class="glass section" style="padding:20px">
      <div class="section-title">⏱️ Últimos Resultados</div>
      <div id="recent-results"></div>
    </div>
  </div>

  <!-- ══════════════════ JOGOS DISPUTADOS ══════════════════ -->
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
          <th>Placar Exato?</th>
        </tr></thead>
        <tbody id="played-body"></tbody>
      </table>
    </div>
    <div class="muted small" style="margin-top:10px;padding-left:4px" id="played-count"></div>
  </div>

  <!-- ══════════════════ PRÓXIMOS JOGOS ══════════════════ -->
  <div class="tab-pane fade-in" id="tab-upcoming">
    <div class="filters" id="upcoming-filters">
      <button class="fbtn active" data-uf="all">Todos</button>
    </div>
    <div class="gcards" id="upcoming-grid"></div>
    <div class="empty" id="upcoming-empty" style="display:none">Nenhum jogo futuro encontrado.</div>
  </div>

  <!-- ══════════════════ CHAVEAMENTO ══════════════════ -->
  <div class="tab-pane fade-in" id="tab-bracket">
    <div class="section">
      <div class="section-title">📋 Classificação por Grupo</div>
      <p class="small muted" style="margin-bottom:18px">
        <span style="color:#00e57a">■</span> Verde = classificado ou virtual classificado &nbsp;
        <span style="color:#f0c030">■</span> Amarelo = na briga por 3° lugar &nbsp;
        Calculado sobre resultados reais + projeção dos jogos restantes.
      </p>
      <div class="sgrids" id="standings-grid"></div>
    </div>

    <div class="section">
      <div class="section-title">🏆 Projeção do Chaveamento — Oitavas de Final</div>
      <p class="small muted" style="margin-bottom:18px">
        Baseado nos prováveis classificados de cada grupo. WC 2026: 32 equipes nas oitavas.
        Probabilidades calculadas pelo modelo Elo. Percentual = chance de avançar no confronto.
      </p>
      <div class="bracket-scroll">
        <div class="bracket" id="bracket-view"></div>
      </div>
    </div>
  </div>

  <!-- ══════════════════ COMO FUNCIONA ══════════════════ -->
  <div class="tab-pane fade-in" id="tab-framework">
    <div class="section">
      <div class="section-title">🔬 Como o Modelo Prevê os Jogos</div>
      <div class="fw-cards" id="fw-cards-container"></div>
    </div>

    <div class="grid2 section">
      <div class="glass" style="padding:20px">
        <div class="section-title" style="font-size:14px">🗂️ De onde vêm os dados</div>
        <ul class="ds-list" id="ds-list"></ul>
      </div>
      <div class="glass" style="padding:20px">
        <div class="section-title" style="font-size:14px">⚙️ Configuração Atual do Modelo</div>
        <div id="model-params"></div>
      </div>
    </div>

    <div class="glass section" style="padding:20px">
      <div class="section-title" style="font-size:14px">📏 Resultados Detalhados de Acurácia</div>
      <div id="accuracy-detail"></div>
      <div class="divider"></div>
      <p class="small muted" style="margin-bottom:12px">
        <b style="color:#90a8c0">Calibração por faixa:</b> cada par de barras compara a probabilidade que prevemos (azul) com o que realmente aconteceu (verde). Ideal = iguais.
      </p>
      <div class="calbins" id="calib-bins"></div>
    </div>
  </div>

  <!-- ══════════════════ RANKING ══════════════════ -->
  <div class="tab-pane fade-in" id="tab-ranking">
    <div class="section">
      <div class="section-title">📈 Ranking de Força — Copa 2026</div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>#</th>
            <th>Seleção</th>
            <th data-rk="elo">Rating Elo<span class="sort-arrow">↓</span></th>
            <th data-rk="att">Potencial de Ataque</th>
            <th data-rk="def">Solidez Defensiva</th>
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
    ⚽ Copa do Mundo 2026 — Framework Preditivo &nbsp;·&nbsp;
    Elo + Dixon-Coles + Mercado de Apostas &nbsp;·&nbsp;
    Avaliado por RPS (Constantinou &amp; Fenton, 2012) &nbsp;·&nbsp;
    Fontes: Kaggle/martj42 · OpenFootball · The Odds API · StatsBomb &nbsp;·&nbsp;
    <code style="background:rgba(240,192,48,.1);padding:1px 5px;border-radius:4px;color:#f0c030;font-size:10px">output/build_dashboard.py</code>
  </div>
</div>

<!-- ══ DATA ══ -->
<script id="pred-data" type="application/json">__DATA_PRED__</script>
<script id="back-data" type="application/json">__DATA_BACK__</script>
<script id="rating-data" type="application/json">__DATA_RATINGS__</script>

<script>
/* ═══════════════════════════════════════════════════
   DATA
═══════════════════════════════════════════════════ */
const PRED = JSON.parse(document.getElementById('pred-data').textContent);
const BACK = JSON.parse(document.getElementById('back-data').textContent);
const RAT  = JSON.parse(document.getElementById('rating-data').textContent);

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
const F = t => FLAGS[t] || '🏳️';
const short = t => t.replace(' and Herzegovina','').replace('Ivory ','').replace('DR ','');

/* ═══════════════════════════════════════════════════
   HEADER & PILLS
═══════════════════════════════════════════════════ */
document.getElementById('tagline').textContent =
  `${PRED.n_matches} jogos modelados · ${BACK.n_played} já disputados · atualizado em ${PRED.generated_at.split('T')[0]}`;
document.getElementById('pill-rps').innerHTML  = `📉 Precisão ${BACK.mean_rps}`;
document.getElementById('pill-acc').innerHTML  = `✅ ${pct(BACK.hit_rate_1x2)} de acerto`;
document.getElementById('pill-games').innerHTML = `⚽ ${BACK.n_played}/${PRED.n_matches} jogos`;

/* ═══════════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════════ */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => { p.classList.remove('active'); });
    btn.classList.add('active');
    const pane = document.getElementById('tab-' + btn.dataset.tab);
    pane.classList.add('active');
    // re-trigger fade
    pane.classList.remove('fade-in');
    void pane.offsetWidth;
    pane.classList.add('fade-in');
  });
});

/* ═══════════════════════════════════════════════════
   COUNT-UP ANIMATION
═══════════════════════════════════════════════════ */
function countUp(el, target, duration=900, decimals=0, suffix='') {
  const start = performance.now();
  const isStr = typeof target === 'string';
  if (isStr) { el.textContent = target; return; }
  (function step(now) {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1-p, 3);
    el.textContent = (target * ease).toFixed(decimals) + suffix;
    if (p < 1) requestAnimationFrame(step);
  })(start);
}

/* ═══════════════════════════════════════════════════
   KPI CARDS
═══════════════════════════════════════════════════ */
const rpsScore = BACK.mean_rps < 0.17 ? 95 : BACK.mean_rps < 0.19 ? 80 : BACK.mean_rps < 0.21 ? 60 : 40;
const rpsLabel = BACK.mean_rps < 0.19 ? 'Excelente — bate o mercado' : BACK.mean_rps < 0.21 ? 'Bom — acima da média' : 'Regular';

const kpis = [
  {
    icon:'📉', id:'kpi-rps',
    val: BACK.mean_rps, dec:4, suffix:'',
    cls:'c-gold', glowColor:'rgba(240,192,48,.15)',
    label:'Precisão do Modelo',
    explain:`Mede o quanto erramos nas probabilidades. Menor = mais preciso. Nosso modelo: ${rpsLabel}.`,
    quality: rpsScore, qualityColor:'#f0c030',
    tip:'RPS (Ranked Probability Score): padrão científico para avaliar previsões de futebol. Bom modelo fica entre 0.18 e 0.21.'
  },
  {
    icon:'🎯', id:'kpi-acc',
    val: BACK.hit_rate_1x2*100, dec:1, suffix:'%',
    cls:'c-green', glowColor:'rgba(0,229,122,.12)',
    label:'Resultado Correto',
    explain:'Em quantos jogos previmos corretamente quem ganhou (ou que empataria).',
    quality: BACK.hit_rate_1x2*100, qualityColor:'#00e57a',
    tip:'Acerto 1X2: o resultado mais provável (vitória casa, empate, vitória fora) coincidiu com o resultado real.'
  },
  {
    icon:'🔬', id:'kpi-exact',
    val: BACK.exact_score_hit_rate*100, dec:1, suffix:'%',
    cls:'c-cyan', glowColor:'rgba(0,212,255,.1)',
    label:'Placar Exato Cravado',
    explain:`Previmos o placar certinho em ${Math.round(BACK.exact_score_hit_rate * BACK.n_played)} de ${BACK.n_played} jogos — resultado difícil de prever.`,
    quality: BACK.exact_score_hit_rate*200, qualityColor:'#00d4ff',
    tip:'Acerto de placar exato: o modelo previu o placar correto (ex: 2-0) com alta probabilidade e acertou.'
  },
  {
    icon:'⚽', id:'kpi-played',
    val: BACK.n_played, dec:0, suffix:'',
    cls:'c-purple', glowColor:'rgba(176,112,255,.1)',
    label:'Jogos Avaliados',
    explain:`${PRED.n_matches - BACK.n_played} jogos ainda a disputar na fase de grupos.`,
    quality: (BACK.n_played / PRED.n_matches)*100, qualityColor:'#b070ff',
    tip:'Total de jogos da fase de grupos já disputados e incluídos no cálculo de acurácia do modelo.'
  },
  {
    icon:'📊', id:'kpi-vsnaive',
    val: ((BACK.baselines.rps_naive_uniform - BACK.mean_rps) / BACK.baselines.rps_naive_uniform * 100),
    dec:1, suffix:'%',
    cls:'c-orange', glowColor:'rgba(255,144,48,.1)',
    label:'Melhor que o Aleatório',
    explain:'O modelo é este % mais preciso do que simplesmente dividir 33%/33%/33% entre os resultados.',
    quality: 70, qualityColor:'#ff9030',
    tip:'Comparação com um modelo ingênuo que atribui probabilidade igual (33%) para vitória, empate e derrota.'
  },
];

document.getElementById('kpi-cards').innerHTML = kpis.map(k =>
  `<div class="kpi" style="--glow:${k.glowColor}">
    <div class="glow" style="background:${k.glowColor};filter:blur(30px)"></div>
    <span class="icon">${k.icon}</span>
    <div class="num ${k.cls}" id="${k.id}">0</div>
    <div class="label">${k.label}<span class="tip" data-tip="${k.tip}">?</span></div>
    <div class="explain">${k.explain}</div>
    <div class="quality-bar"><div class="quality-fill" style="width:${Math.min(k.quality,100)}%;background:${k.qualityColor}"></div></div>
  </div>`
).join('');

// trigger count-up
setTimeout(() => {
  kpis.forEach(k => {
    countUp(document.getElementById(k.id), k.val, 800, k.dec, k.suffix);
  });
}, 100);

/* ═══════════════════════════════════════════════════
   CHART.JS GLOBAL DEFAULTS
═══════════════════════════════════════════════════ */
Chart.defaults.color = '#4a6080';
Chart.defaults.borderColor = 'rgba(255,255,255,.06)';
Chart.defaults.font.family = "-apple-system,'Segoe UI',sans-serif";
Chart.defaults.font.size = 11;

const gridColor = 'rgba(255,255,255,.05)';

/* ═══════════════════════════════════════════════════
   CHART: RPS TIMELINE
═══════════════════════════════════════════════════ */
(function() {
  const tl = BACK.rps_timeline;
  new Chart(document.getElementById('chart-rps'), {
    type:'line',
    data:{
      labels: tl.map((_,i)=>`J${i+1}`),
      datasets:[
        { label:'RPS por jogo', data:tl.map(d=>d.rps),
          borderColor:'rgba(90,112,144,.5)', backgroundColor:'transparent',
          pointRadius:2, pointHoverRadius:5, borderWidth:1.5, tension:.3 },
        { label:'RPS acumulado', data:tl.map(d=>d.cum_rps),
          borderColor:'#f0c030',
          backgroundColor:(ctx)=>{
            const g=ctx.chart.ctx.createLinearGradient(0,0,0,200);
            g.addColorStop(0,'rgba(240,192,48,.15)');
            g.addColorStop(1,'rgba(240,192,48,.01)');
            return g;
          },
          fill:true, pointRadius:0, borderWidth:2.5, tension:.4 },
        { label:'Meta (< 0.19)', data:tl.map(()=>0.19),
          borderColor:'#00e57a', borderDash:[5,4], pointRadius:0,
          borderWidth:1.5, backgroundColor:'transparent' },
        { label:'Ingênuo (0.22)', data:tl.map(()=>0.225),
          borderColor:'#f04060', borderDash:[5,4], pointRadius:0,
          borderWidth:1.5, backgroundColor:'transparent' },
      ]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{ position:'bottom', labels:{boxWidth:10,padding:14,font:{size:10}} },
        tooltip:{ backgroundColor:'rgba(2,8,24,.95)', borderColor:'rgba(255,255,255,.1)',
          borderWidth:1, padding:10, titleFont:{size:11},bodyFont:{size:11} }
      },
      scales:{
        y:{ min:0, max:.42, grid:{color:gridColor}, ticks:{callback:v=>v.toFixed(2)} },
        x:{ grid:{display:false}, ticks:{maxTicksLimit:12} }
      }
    }
  });
})();

/* ═══════════════════════════════════════════════════
   CHART: MODEL COMPARISON
═══════════════════════════════════════════════════ */
(function() {
  const b = BACK.baselines;
  const data = [
    {l:'Ensemble (nosso)',v:BACK.mean_rps,c:'#f0c030'},
    {l:'Dixon-Coles',v:b.rps_dixon_coles_only,c:'#3b82f6'},
    {l:'Elo',v:b.rps_elo_only,c:'#9060e0'},
    {l:'Aleatório (33/33/33)',v:b.rps_naive_uniform,c:'#f04060'},
  ];
  new Chart(document.getElementById('chart-models'),{
    type:'bar',
    data:{
      labels:data.map(d=>d.l),
      datasets:[{
        data:data.map(d=>d.v),
        backgroundColor:data.map(d=>d.c+'22'),
        borderColor:data.map(d=>d.c),
        borderWidth:1.5, borderRadius:8, borderSkipped:false,
      }]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{
        legend:{display:false},
        tooltip:{
          backgroundColor:'rgba(2,8,24,.95)', borderColor:'rgba(255,255,255,.1)',
          borderWidth:1, padding:10,
          callbacks:{ label:ctx=>` RPS: ${ctx.parsed.y.toFixed(4)}` }
        }
      },
      scales:{
        y:{ min:.14, max:.24, grid:{color:gridColor},
          ticks:{callback:v=>v.toFixed(2)} },
        x:{ grid:{display:false} }
      }
    }
  });
})();

/* ═══════════════════════════════════════════════════
   CHART: CALIBRATION
═══════════════════════════════════════════════════ */
(function() {
  const bins = BACK.calibration_bins;
  new Chart(document.getElementById('chart-calib'),{
    type:'scatter',
    data:{
      datasets:[
        { label:'Modelo', data:bins.map(b=>({x:b.pred_mean,y:b.obs_freq})),
          backgroundColor:'rgba(0,180,255,.5)', borderColor:'#00b4ff',
          pointRadius:bins.map(b=>Math.min(14,4+b.n/5)),
          pointHoverRadius:14,
        },
        { label:'Ideal', data:[{x:0,y:0},{x:1,y:1}],
          type:'line', borderColor:'rgba(255,255,255,.15)',
          borderDash:[5,4], pointRadius:0, borderWidth:1.5, backgroundColor:'transparent'
        }
      ]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{
        legend:{ position:'bottom', labels:{boxWidth:10,padding:14,font:{size:10}} },
        tooltip:{
          backgroundColor:'rgba(2,8,24,.95)', borderColor:'rgba(255,255,255,.1)',
          borderWidth:1, padding:10,
          callbacks:{
            label:ctx=>ctx.dataset.label==='Modelo'
              ? `Previsto: ${(ctx.parsed.x*100).toFixed(0)}% → Real: ${(ctx.parsed.y*100).toFixed(0)}%`
              : ''
          }
        }
      },
      scales:{
        x:{ min:0,max:1, grid:{color:gridColor},
          title:{display:true,text:'Probabilidade prevista',color:'#4a6080'},
          ticks:{callback:v=>v*100+'%'} },
        y:{ min:0,max:1, grid:{color:gridColor},
          title:{display:true,text:'Frequência real',color:'#4a6080'},
          ticks:{callback:v=>v*100+'%'} }
      }
    }
  });
})();

/* ═══════════════════════════════════════════════════
   CHART: TOP ELO
═══════════════════════════════════════════════════ */
(function() {
  const top = RAT.slice(0,12);
  new Chart(document.getElementById('chart-elo'),{
    type:'bar',
    data:{
      labels:top.map(t=>short(t.team)),
      datasets:[{
        data:top.map(t=>t.elo),
        backgroundColor:top.map((_,i)=>i<3?'rgba(240,192,48,.25)':'rgba(59,130,246,.15)'),
        borderColor:top.map((_,i)=>i<3?'#f0c030':'#3b82f6'),
        borderWidth:1.5, borderRadius:6, borderSkipped:false,
      }]
    },
    options:{
      indexAxis:'y',
      responsive:true, maintainAspectRatio:false,
      plugins:{
        legend:{display:false},
        tooltip:{
          backgroundColor:'rgba(2,8,24,.95)', borderColor:'rgba(255,255,255,.1)',
          borderWidth:1, padding:10,
          callbacks:{ label:ctx=>` Elo: ${ctx.parsed.x}` }
        }
      },
      scales:{
        x:{ min:1700, grid:{color:gridColor}, ticks:{callback:v=>v} },
        y:{ grid:{display:false} }
      }
    }
  });
})();

/* ═══════════════════════════════════════════════════
   RECENT RESULTS
═══════════════════════════════════════════════════ */
(function() {
  const played = PRED.matches.filter(m=>m.played).slice(-8).reverse();
  document.getElementById('recent-results').innerHTML = played.map(m=>{
    const p = m.prediction;
    const e = m.eval||{};
    return `<div class="rr-row">
      <span class="small muted" style="width:74px;flex-shrink:0">${m.date}</span>
      <span class="small muted" style="width:28px;flex-shrink:0">${(m.group||'').replace('Group ','')}</span>
      <span style="flex:1;font-weight:700;min-width:0;font-size:13px">${F(m.home)} ${m.home} <span class="muted">×</span> ${m.away} ${F(m.away)}</span>
      <span class="score-big" style="width:54px;text-align:center;flex-shrink:0;color:${e.correct_1x2?'#d0dff0':'#f04060'}">${m.actual[0]}-${m.actual[1]}</span>
      <span class="muted small" style="width:56px;flex-shrink:0;text-align:center">prev <b style="color:#f0c030">${p.most_likely}</b></span>
      <span style="width:70px;flex-shrink:0;text-align:center">${
        e.correct_1x2
          ? '<span class="pill pill-win">✓ acertou</span>'
          : '<span class="pill pill-lose">✕ errou</span>'
      }</span>
      ${e.exact_score_hit ? '<span class="pill pill-score">🎯 exato</span>' : '<span style="width:70px"></span>'}
      <span class="muted small mono" style="width:44px;text-align:right;flex-shrink:0">${e.rps!=null?e.rps.toFixed(3):'—'}</span>
    </div>`;
  }).join('');
})();

/* ═══════════════════════════════════════════════════
   TAB: JOGOS DISPUTADOS
═══════════════════════════════════════════════════ */
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
      const mkt=m.models.market?' <span style="font-size:9px;color:#f0a020;opacity:.7" title="odds disponíveis">💰</span>':'';
      return `<tr>
        <td class="small muted">${m.date}</td>
        <td class="small muted">${(m.group||'').replace('Group ','')}</td>
        <td style="font-weight:700">${F(m.home)} ${m.home} <span class="muted small">×</span> ${m.away} ${F(m.away)}${mkt}</td>
        <td><span class="score-big" style="color:${e.correct_1x2?'#d0dff0':'#5a7090'}">${m.actual[0]}-${m.actual[1]}</span></td>
        <td class="mono small" style="color:#f0c030">${p.most_likely}</td>
        <td>
          <div class="pbar"><div class="ph" style="flex:${p.p_home}"></div><div class="pd" style="flex:${p.p_draw}"></div><div class="pa" style="flex:${p.p_away}"></div></div>
          <div class="pnums">${pct(p.p_home)} · ${pct(p.p_draw)} · ${pct(p.p_away)}</div>
        </td>
        <td class="mono small">${e.rps!=null?e.rps.toFixed(3):'—'}</td>
        <td>${e.correct_1x2!=null?(e.correct_1x2?'<span class="pill pill-win">✓</span>':'<span class="pill pill-lose">✕</span>'):'—'}</td>
        <td>${e.exact_score_hit?'<span class="pill pill-score">🎯</span>':'<span class="muted small">—</span>'}</td>
      </tr>`;
    }).join('');
  }
  fbar.addEventListener('click',e=>{
    const btn=e.target.closest('.fbtn');if(!btn)return;
    fbar.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active'); ag=btn.dataset.gf; render();
  });
  document.querySelectorAll('#tab-played th[data-sk]').forEach(th=>{
    th.addEventListener('click',()=>{
      const k=th.dataset.sk; sd=sk===k?-sd:1; sk=k; render();
    });
  });
  render();
})();

/* ═══════════════════════════════════════════════════
   TAB: PRÓXIMOS JOGOS
═══════════════════════════════════════════════════ */
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
      return `<div class="gcard">
        <div class="gc-meta">
          <span class="gc-group">${m.group} · ${m.round}</span>
          <span class="gc-date">📅 ${m.date}</span>
        </div>
        <div class="gc-matchup">
          <div class="gc-team" style="${favH?'background:rgba(59,130,246,.06);border-radius:8px;padding:4px':''}">
            <div class="tc-name">${F(m.home)} ${m.home}</div>
            <div class="tc-xg">xG esperado: ${p.xg_home}</div>
          </div>
          <div class="gc-vs">VS</div>
          <div class="gc-team" style="${favA?'background:rgba(240,64,96,.06);border-radius:8px;padding:4px':''}">
            <div class="tc-name">${m.away} ${F(m.away)}</div>
            <div class="tc-xg">xG esperado: ${p.xg_away}</div>
          </div>
        </div>
        <div class="gc-score">${p.most_likely}</div>
        <div class="gc-pbar">
          <div style="flex:${p.p_home};background:#3b82f6;border-radius:3px 0 0 3px"></div>
          <div style="flex:${p.p_draw};background:#9060e0"></div>
          <div style="flex:${p.p_away};background:#f04060;border-radius:0 3px 3px 0"></div>
        </div>
        <div class="gc-pnums">
          <span class="pn-h">${pct(p.p_home)} Casa</span>
          <span>${pct(p.p_draw)} Empate</span>
          <span class="pn-a">Fora ${pct(p.p_away)}</span>
        </div>
        ${hasMkt?`<div class="gc-mkt">💰 Baseado em odds de ${m.models.market.n_books} casas de apostas</div>`:''}
      </div>`;
    }).join('');
  }
  fbar.addEventListener('click',e=>{
    const btn=e.target.closest('.fbtn');if(!btn)return;
    fbar.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active'); ag=btn.dataset.uf; render();
  });
  render();
})();

/* ═══════════════════════════════════════════════════
   TAB: CHAVEAMENTO
═══════════════════════════════════════════════════ */
(function() {
  // Build standings
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
    const g=m.group||'';
    if(!groupMap[g])groupMap[g]=new Set();
    groupMap[g].add(m.home); groupMap[g].add(m.away);
  });
  const groupStandings={};
  Object.keys(groupMap).sort().forEach(g=>{
    groupStandings[g]=[...groupMap[g]]
      .map(t=>teamStats[t]||{team:t,group:g,pts:0,gf:0,ga:0,gd:0,w:0,d:0,l:0,pld:0,form:[]})
      .sort((a,b)=>b.pts-a.pts||b.gd-a.gd||b.gf-a.gf);
  });

  // Render standings
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
  const wp=(a,b)=>{
    const ea=eloMap[a]||1700, eb=eloMap[b]||1700;
    return 1/(1+Math.pow(10,(eb-ea)/400));
  };

  const r32=[
    ['A',1,'B',2],['C',1,'D',2],['E',1,'F',2],['G',1,'H',2],
    ['I',1,'J',2],['K',1,'L',2],
    ['B',1,'A',2],['D',1,'C',2],['F',1,'E',2],['H',1,'G',2],
    ['J',1,'I',2],['L',1,'K',2],
  ];

  function getTeam(grp, pos){
    return qualified[grp]?.[pos-1] || `${pos===1?'1°':'2°'}${grp}`;
  }
  function matchHTML(tA, tB, tagA='', tagB=''){
    const isStr=(t)=>typeof t==='string'&&t.length<=3;
    const pA = isStr(tA)||isStr(tB) ? 0.5 : wp(tA, tB);
    const pB = 1-pA;
    const favA=pA>pB;
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
  function projWinner(tA, tB){
    const isStr=(t)=>typeof t==='string'&&t.length<=3;
    if(isStr(tA)||isStr(tB)) return tA;
    return wp(tA,tB)>=0.5?tA:tB;
  }

  const r32Matches=r32.map(([gA,pA,gB,pB])=>({
    tA:getTeam(gA,pA), tB:getTeam(gB,pB), tagA:`${pA===1?'1°':'2°'}${gA}`, tagB:`${pB===1?'1°':'2°'}${gB}`
  }));
  const r32W=r32Matches.map(m=>projWinner(m.tA,m.tB));

  const r16Pairs=[];
  for(let i=0;i<r32W.length;i+=2) r16Pairs.push([r32W[i],r32W[i+1]]);
  const r16W=r16Pairs.map(([a,b])=>projWinner(a,b));

  const qfPairs=[];
  for(let i=0;i<r16W.length;i+=2) qfPairs.push([r16W[i],r16W[i+1]]);
  const qfW=qfPairs.map(([a,b])=>projWinner(a,b));

  const sfPairs=[[qfW[0],qfW[1]],[qfW[2],qfW[3]]];
  const sfW=sfPairs.map(([a,b])=>projWinner(a,b));

  const half1=r32Matches.slice(0,6);
  const half2=r32Matches.slice(6,12);
  const qfMatches=qfPairs.map(([a,b])=>({tA:a,tB:b,tagA:'',tagB:''}));
  const sfMatches=sfPairs.map(([a,b])=>({tA:a,tB:b,tagA:'',tagB:''}));

  document.getElementById('bracket-view').innerHTML = `
    <div class="b-col">
      <div class="b-rnd-title">⚔️ Oitavas — 1ª metade</div>
      ${half1.map(m=>matchHTML(m.tA,m.tB,m.tagA,m.tagB)).join('')}
    </div>
    <div class="b-col">
      <div class="b-rnd-title">⚔️ Oitavas — 2ª metade</div>
      ${half2.map(m=>matchHTML(m.tA,m.tB,m.tagA,m.tagB)).join('')}
    </div>
    <div class="b-col b-col-narrow" style="justify-content:space-around;display:flex;flex-direction:column">
      <div class="b-rnd-title">🏅 Quartas</div>
      ${qfMatches.map(m=>matchHTML(m.tA,m.tB)).join('')}
    </div>
    <div class="b-col b-col-narrow" style="justify-content:space-around;display:flex;flex-direction:column">
      <div class="b-rnd-title">🔥 Semifinais</div>
      ${sfMatches.map(m=>matchHTML(m.tA,m.tB)).join('')}
    </div>
    <div class="b-col" style="max-width:200px;flex:.38;justify-content:center;display:flex;flex-direction:column">
      <div class="b-rnd-title">🏆 Final</div>
      ${matchHTML(sfW[0],sfW[1])}
    </div>
  `;
})();

/* ═══════════════════════════════════════════════════
   TAB: FRAMEWORK
═══════════════════════════════════════════════════ */
(function() {
  const cards=[
    {n:1,title:'Elo de Seleções',text:'Rating de força construído sobre <strong>~49 mil jogos internacionais</strong> (1872–2026). Cada vitória aumenta o rating e cada derrota diminui — mais do que em partidas importantes. Calibrado para converter a diferença de força em gols esperados.'},
    {n:2,title:'Dixon-Coles',text:'Estima separadamente o potencial de <strong>ataque e defesa</strong> de cada seleção usando máxima verossimilhança. Jogos recentes têm mais peso. Inclui correção para resultados de baixo placar, que são mais frequentes no futebol.'},
    {n:3,title:'Mercado de Apostas',text:'Odds de <strong>31+ casas de apostas</strong>, com a margem da casa removida. Funciona como a "sabedoria das multidões" — incorpora informações difíceis de modelar, como lesões de última hora e escalações.'},
    {n:4,title:'Ensemble (combinação)',text:'Junta os três métodos com pesos calibrados: Elo <code>22%</code> · Dixon-Coles <code>43%</code> · Mercado <code>35%</code>. Retorna a probabilidade de vitória/empate/derrota e o placar mais provável por Poisson bivariado.'},
    {n:5,title:'Avaliação (RPS)',text:'Usamos o <strong>Ranked Probability Score</strong> — padrão científico. Ele penaliza erros proporcionalmente: prever 90% para o time que perdeu é muito pior do que prever 55%. Bom modelo fica entre <code>0.18</code> e <code>0.21</code>.'},
    {n:6,title:'Sem "Cola" (No Leakage)',text:'Jogos já disputados são previstos usando apenas dados <strong>anteriores à partida</strong>. Isso garante que as métricas de acurácia refletem previsões reais — não há vantagem retroativa.'},
  ];
  document.getElementById('fw-cards-container').innerHTML=cards.map(c=>
    `<div class="fw-card"><div class="fw-num">${c.n}</div><h4>${c.title}</h4><p>${c.text}</p></div>`
  ).join('');

  document.getElementById('ds-list').innerHTML=[
    {icon:'📦',name:'Kaggle / martj42',desc:'~49 mil resultados internacionais desde 1872. Base principal de treino para Elo e Dixon-Coles.'},
    {icon:'⚽',name:'OpenFootball',desc:'Resultados da Copa 2026 atualizados automaticamente. Grátis, sem chave de API.'},
    {icon:'💰',name:'The Odds API',desc:'Odds de 31+ casas para jogos futuros. A margem da banca é removida matematicamente antes de usar.'},
    {icon:'📡',name:'StatsBomb Open Data',desc:'Eventos e xG de partidas históricas para validação e calibração dos gols esperados.'},
    {icon:'📰',name:'NewsData.io',desc:'Notícias sobre lesões, suspensões e contexto em português e inglês.'},
  ].map(d=>`<li class="ds-item"><span class="ds-icon">${d.icon}</span><div class="ds-info"><strong>${d.name}</strong><p>${d.desc}</p></div></li>`).join('');

  const w=PRED.weights;
  document.getElementById('model-params').innerHTML=[
    {n:'Peso Elo (com odds)',v:w.elo,c:'#3b82f6'},
    {n:'Peso Dixon-Coles',v:w.dixon_coles,c:'#f0c030'},
    {n:'Peso Mercado',v:w.market,c:'#00e57a'},
    {n:'Peso Elo (sem odds)',v:w.sem_mercado.elo,c:'#3b82f6'},
    {n:'Peso DC (sem odds)',v:w.sem_mercado.dixon_coles,c:'#f0c030'},
  ].map(r=>`<div class="mbar-row">
    <span class="mbar-name">${r.n}</span>
    <div class="mbar-bg"><div class="mbar-fill" style="width:${r.v*100}%;background:${r.c}"></div></div>
    <span class="mbar-val">${(r.v*100).toFixed(0)}%</span>
  </div>`).join('')+`<div class="divider"></div>
  <p class="small muted">
    <b style="color:#5a7090">Calibração Elo:</b> β = ${PRED.elo_calibration.beta_sup_per_elo.toFixed(6)}<br>
    <b style="color:#5a7090">Dixon-Coles ρ (correção):</b> ${PRED.dc_params.rho.toFixed(4)} · γ (mando) = ${PRED.dc_params.gamma.toFixed(4)}
  </p>`;

  const b=BACK.baselines;
  document.getElementById('accuracy-detail').innerHTML=[
    {n:'Ensemble (nosso)',v:BACK.mean_rps,c:'#f0c030',max:.25},
    {n:'Só Dixon-Coles',v:b.rps_dixon_coles_only,c:'#3b82f6',max:.25},
    {n:'Só Elo',v:b.rps_elo_only,c:'#9060e0',max:.25},
    {n:'Aleatório (33/33/33)',v:b.rps_naive_uniform,c:'#f04060',max:.25},
    {n:'Resultado certo',v:BACK.hit_rate_1x2,c:'#00e57a',max:1},
    {n:'Placar exato',v:BACK.exact_score_hit_rate,c:'#00d4ff',max:1},
  ].map(r=>`<div class="mbar-row">
    <span class="mbar-name">${r.n}</span>
    <div class="mbar-bg"><div class="mbar-fill" style="width:${(r.v/r.max)*100}%;background:${r.c}"></div></div>
    <span class="mbar-val mono">${r.v<1&&r.n.includes('Placar')||r.n.includes('certo')?pct(r.v):r.v.toFixed?r.v.toFixed(4):r.v}</span>
  </div>`).join('');

  const bins=BACK.calibration_bins;
  document.getElementById('calib-bins').innerHTML=bins.map(b=>{
    const hp=Math.round(b.pred_mean*52);
    const ho=Math.round(b.obs_freq*52);
    const good=Math.abs(b.pred_mean-b.obs_freq)<0.12;
    const col=good?'#00e57a':'#f0c030';
    return `<div class="calbin">
      <div class="cbl">${b.bin}</div>
      <div class="cbars">
        <div class="cbar" style="height:${hp}px;background:#3b82f6" title="Previsto: ${(b.pred_mean*100).toFixed(0)}%"></div>
        <div class="cbar" style="height:${ho}px;background:${col}" title="Real: ${(b.obs_freq*100).toFixed(0)}%"></div>
      </div>
      <div class="cval" style="color:${col}">${(b.obs_freq*100).toFixed(0)}%</div>
      <div class="cn">n=${b.n}</div>
    </div>`;
  }).join('');
})();

/* ═══════════════════════════════════════════════════
   TAB: RANKING
═══════════════════════════════════════════════════ */
(function() {
  let rk='elo', rd=-1;
  function render(){
    const rows=[...RAT].sort((a,b)=>(a[rk]>b[rk]?1:a[rk]<b[rk]?-1:0)*rd);
    const maxE=Math.max(...rows.map(r=>r.elo));
    document.getElementById('ranking-body').innerHTML=rows.map((r,i)=>{
      const bw=(r.elo/maxE*100).toFixed(1);
      const nc=r.net>=2.2?'#f0c030':r.net>=1.8?'#00e57a':r.net>=1.2?'#3b82f6':'#4a6080';
      return `<tr>
        <td class="muted small">${i+1}</td>
        <td style="font-weight:700">${F(r.team)} ${r.team}</td>
        <td class="mono" style="font-weight:800;color:#d0dff0">${r.elo}</td>
        <td class="mono" style="color:${r.att>=0?'#00e57a':'#f04060'}">${r.att>=0?'+':''}${r.att}</td>
        <td class="mono" style="color:${r.def>=0?'#00e57a':'#f04060'}">${r.def>=0?'+':''}${r.def}</td>
        <td class="mono" style="font-weight:800;color:${nc}">${r.net>=0?'+':''}${r.net}</td>
        <td>
          <div class="rank-bar-bg">
            <div class="rank-bar-fill" style="width:${bw}%"></div>
          </div>
        </td>
      </tr>`;
    }).join('');
  }
  document.querySelectorAll('#tab-ranking th[data-rk]').forEach(th=>{
    th.addEventListener('click',()=>{
      const k=th.dataset.rk; rd=rk===k?-rd:-1; rk=k; render();
    });
  });
  render();
})();
</script>
</body>
</html>"""


def main():
    pred = json.load(open(ANALYSIS / "wc2026_predictions.json", encoding="utf-8"))
    back = json.load(open(ANALYSIS / "wc2026_backtest.json", encoding="utf-8"))
    ratings = build_ratings()
    html = (HTML_TEMPLATE
            .replace("__DATA_PRED__", json.dumps(pred, ensure_ascii=False))
            .replace("__DATA_BACK__", json.dumps(back, ensure_ascii=False))
            .replace("__DATA_RATINGS__", json.dumps(ratings, ensure_ascii=False)))
    out = ROOT / "output" / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado: {out}  ({len(html)//1024} KB)")
    print(f"  {pred['n_matches']} jogos · {back['n_played']} avaliados · RPS {back['mean_rps']} · Acerto {back['hit_rate_1x2']:.1%}")


if __name__ == "__main__":
    main()

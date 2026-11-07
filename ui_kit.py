"""Habillage visuel de VeloFit AI Studio : feuille de style, icônes SVG et bandeau d'en-tête.

Direction artistique « télémétrie » : fond encre, trame de mesure, une seule couleur d'accent
(jaune « volt »), chiffres en police mono. Le thème est entièrement forcé en CSS : il reste
identique sur ordinateur et sur téléphone, que l'appareil soit en mode clair ou sombre.
"""
import re

ACCENT = "#c6f432"     # volt
ACCENT_2 = "#5ec8ff"   # bleu ciel (comparaisons, 2e série)
OK, WARN, BAD = "#34d399", "#fbbf24", "#fb7185"
TXT, MUT, GRID = "#eef2f7", "#8b97a8", "rgba(255,255,255,.07)"

_P = 'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"'
ICONS = {
    "video": f'<svg viewBox="0 0 24 24" {_P}><rect x="2" y="6" width="14" height="12" rx="2"/><path d="M22 8l-6 4 6 4z"/></svg>',
    "target": f'<svg viewBox="0 0 24 24" {_P}><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 1v4M12 19v4M1 12h4M19 12h4"/></svg>',
    "ruler": f'<svg viewBox="0 0 24 24" {_P}><path d="M3 17L17 3l4 4L7 21z"/><path d="M7 13l2 2M10 10l2 2M13 7l2 2"/></svg>',
    "compass": f'<svg viewBox="0 0 24 24" {_P}><circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/></svg>',
    "activity": f'<svg viewBox="0 0 24 24" {_P}><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>',
    "history": f'<svg viewBox="0 0 24 24" {_P}><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 7v5l3 2"/></svg>',
}

_HERO_SVG = """
<svg class="hero-art" viewBox="0 0 420 250" role="img" aria-label="Schéma de mesure d'une position de cycliste">
  <defs><linearGradient id="scan" x1="0" x2="1"><stop offset="0" stop-color="#c6f432" stop-opacity="0"/><stop offset="1" stop-color="#c6f432" stop-opacity=".16"/></linearGradient></defs>
  <g class="bike" fill="none" stroke="#6b7a90" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="90" cy="172" r="52"/><circle cx="330" cy="172" r="52"/>
    <path d="M90 172L190 174L165 98L90 172M165 98L300 104L190 174M300 104L330 172M300 104L306 92L326 94M150 94H184"/>
  </g>
  <g class="rider" fill="none" stroke="#eef2f7" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
    <path d="M165 88L255 52L290 82L310 94M165 88L224 128L202 180"/><circle cx="272" cy="36" r="11"/>
  </g>
  <path class="arc" d="M236 112A20 20 0 0 1 238 144" fill="none" stroke="#c6f432" stroke-width="2"/>
  <path class="arc" d="M188 88A26 26 0 0 1 200 76" fill="none" stroke="#5ec8ff" stroke-width="2"/>
  <g fill="#06090e" stroke="#c6f432" stroke-width="2">
    <circle class="node" cx="165" cy="88" r="5"/><circle class="node" cx="255" cy="52" r="5"/><circle class="node" cx="290" cy="82" r="5"/>
    <circle class="node" cx="224" cy="128" r="5"/><circle class="node" cx="202" cy="180" r="5"/>
  </g>
  <g font-family="JetBrains Mono, ui-monospace, monospace" font-size="10" letter-spacing=".05em" stroke="#0c1118" stroke-width="4" paint-order="stroke">
    <text x="238" y="152" fill="#c6f432">GENOU 147°</text><text x="112" y="64" fill="#5ec8ff">TRONC 44°</text>
  </g>
  <rect class="scan" x="0" y="8" width="70" height="232" fill="url(#scan)"/>
</svg>"""


def hero(title: str, text: str, badge: str = "Analyse biomécanique par IA") -> str:
    """Bandeau d'en-tête (HTML sur une ligne, prêt pour st.markdown)."""
    html = f"""
    <div class="hero">
      <div class="hero-txt">
        <span class="hero-badge"><i></i>{badge}</span>
        <h1>{title}</h1>
        <p>{text}</p>
      </div>
      <div class="hero-vis">{_HERO_SVG}</div>
    </div>"""
    return re.sub(r"\s*\n\s*", " ", html.strip())


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{
  --bg:#06090e; --panel:#0c1118; --panel2:#111823; --line:rgba(255,255,255,.09); --line2:rgba(255,255,255,.16);
  --txt:#eef2f7; --mut:#8b97a8; --acc:#c6f432; --acc2:#5ec8ff; --ok:#34d399; --warn:#fbbf24; --bad:#fb7185;
  --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace; --head:'Space Grotesk','Inter',sans-serif;
  color-scheme:dark;
}
html, body, .stApp{font-family:'Inter',-apple-system,'Segoe UI',sans-serif; color:var(--txt); color-scheme:dark; -webkit-text-size-adjust:100%;}
.stApp{background-color:var(--bg);
  background-image:radial-gradient(rgba(255,255,255,.07) 1px, transparent 1.2px), radial-gradient(900px 420px at 85% -8%, rgba(198,244,50,.07), transparent 65%);
  background-size:26px 26px, auto; background-attachment:fixed; overflow-x:hidden;}
header[data-testid="stHeader"]{background:transparent;}
[data-testid="stToolbar"], [data-testid="stDecoration"], .stAppDeployButton, #MainMenu, footer{display:none !important;}
.block-container{padding-top:3.2rem; max-width:1280px;}
h1,h2,h3,h4,h5{font-family:var(--head); color:var(--txt); letter-spacing:-.01em;}
.stApp p, .stApp li, .stApp label, .stApp span, .stApp [data-testid="stMarkdownContainer"]{color:inherit;}
.stApp [data-testid="stWidgetLabel"] p, .stApp label p, .stApp [data-testid="stMarkdownContainer"] p{color:var(--txt);}
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p{color:var(--mut);}
a{color:var(--acc);}

/* ---------- barre latérale ---------- */
[data-testid="stSidebar"]{background:#080c12; border-right:1px solid var(--line);}
[data-testid="stSidebar"] h3{font-family:var(--head); font-size:1.05rem; color:var(--txt);}
[data-testid="stSidebar"] h3::before{content:""; display:inline-block; width:10px; height:10px; background:var(--acc); border-radius:3px; margin-right:9px; transform:rotate(45deg);}
.side-sec{font-family:var(--mono); font-size:.68rem; text-transform:uppercase; letter-spacing:.16em; color:var(--mut); margin:20px 0 6px; padding-top:12px; border-top:1px solid var(--line);}

/* ---------- bandeau d'en-tête ---------- */
.hero{position:relative; display:grid; grid-template-columns:1.15fr .85fr; gap:12px; align-items:center; overflow:hidden;
  border:1px solid var(--line2); border-radius:20px; padding:36px 40px; margin-bottom:22px; background:rgba(12,17,24,.82);}
.hero::before{content:""; position:absolute; left:0; top:0; height:2px; width:100%; background:linear-gradient(90deg,var(--acc),transparent 70%);}
.hero::after{content:""; position:absolute; inset:0; pointer-events:none; opacity:.55;
  background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px); background-size:44px 44px;
  -webkit-mask-image:linear-gradient(100deg,transparent 35%,#000 100%); mask-image:linear-gradient(100deg,transparent 35%,#000 100%);}
.hero-txt{position:relative; z-index:1;} .hero-vis{position:relative; z-index:1;}
.hero-badge{display:inline-flex; align-items:center; gap:9px; font-family:var(--mono); font-size:.72rem; font-weight:500; letter-spacing:.12em; text-transform:uppercase; color:var(--acc);
  border:1px solid rgba(198,244,50,.35); padding:6px 12px; border-radius:6px; background:rgba(198,244,50,.06);}
.hero-badge i{width:7px; height:7px; border-radius:50%; background:var(--acc); animation:blink 2.4s ease-in-out infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}
.hero h1{font-family:var(--head); font-size:3.1rem; font-weight:700; line-height:1.04; margin:18px 0 12px; letter-spacing:-.035em; color:var(--txt);}
.hero p{max-width:600px; color:#a5b1c2; font-size:1.04rem; line-height:1.6; margin:0;}
.hero-art{width:100%; height:auto; display:block;}
.hero-art .scan{animation:scan 5.5s linear infinite;}
@keyframes scan{0%{transform:translateX(-70px); opacity:0}12%{opacity:1}88%{opacity:1}100%{transform:translateX(430px); opacity:0}}
.hero-art .node{animation:blink 2.4s ease-in-out infinite;}
@media (prefers-reduced-motion:reduce){.hero-art .scan,.hero-art .node,.hero-badge i{animation:none;}}

/* ---------- panneaux ---------- */
.glass{position:relative; background:rgba(12,17,24,.88); border:1px solid var(--line); border-radius:16px; padding:22px;}
.feat{height:100%; margin-bottom:14px; transition:border-color .2s ease, transform .2s ease;}
.feat:hover{border-color:rgba(198,244,50,.5); transform:translateY(-3px);}
.feat .ico{width:42px; height:42px; display:grid; place-items:center; border-radius:10px; margin-bottom:14px; color:var(--acc); border:1px solid rgba(198,244,50,.3); background:rgba(198,244,50,.07);}
.feat .ico svg{width:22px; height:22px;}
.feat h4{margin:0 0 6px; font-size:1.06rem; color:var(--txt);}
.feat p{margin:0; color:var(--mut); font-size:.9rem; line-height:1.55;}
.step{display:flex; gap:14px; align-items:flex-start; padding:14px 0; border-bottom:1px solid var(--line);}
.step:last-child{border-bottom:none;}
.step .n{flex:0 0 32px; height:32px; border-radius:8px; display:grid; place-items:center; font-family:var(--mono); font-weight:600; color:var(--acc); border:1px solid rgba(198,244,50,.4); background:rgba(198,244,50,.07);}
.step b{color:var(--txt);} .step span{color:var(--mut); font-size:.9rem;}

/* ---------- score ---------- */
.score-wrap{display:flex; gap:26px; align-items:center;}
.ring{--p:0; --c:var(--ok); flex:0 0 150px; width:150px; height:150px; border-radius:50%; background:conic-gradient(var(--c) calc(var(--p) * 1%), #1a2230 0); display:grid; place-items:center;}
.ring-in{width:124px; height:124px; border-radius:50%; background:var(--panel); display:grid; place-items:center; text-align:center; border:1px solid var(--line);}
.ring-val{font-family:var(--mono); font-size:2.5rem; font-weight:600; line-height:1; color:var(--txt);}
.ring-sub{font-family:var(--mono); font-size:.68rem; color:var(--mut); letter-spacing:.1em;}
.verdict h3{margin:0 0 4px; font-size:1.5rem; color:var(--txt);}
.verdict p{margin:0; color:var(--mut); font-size:.92rem; line-height:1.5;}
.chip{--c:var(--ok); display:inline-flex; align-items:center; gap:6px; font-family:var(--mono); font-size:.66rem; font-weight:500; letter-spacing:.07em; text-transform:uppercase; color:var(--c);
  border:1px solid var(--c); background:rgba(255,255,255,.04); padding:4px 9px; border-radius:6px; white-space:nowrap;}
.chip::before{content:""; width:6px; height:6px; border-radius:50%; background:var(--c);}
@supports (color: color-mix(in srgb, red 50%, blue)){
  .chip{border-color:color-mix(in srgb, var(--c) 50%, transparent); background:color-mix(in srgb, var(--c) 10%, transparent);}
  .insight{background:linear-gradient(90deg, color-mix(in srgb, var(--c) 6%, transparent), transparent 55%), rgba(12,17,24,.9);}
}
.mcard{background:rgba(12,17,24,.88); border:1px solid var(--line); border-radius:14px; padding:14px 16px 12px; margin-bottom:12px; transition:border-color .2s ease;}
.mcard:hover{border-color:var(--line2);}
.mcard-top{display:flex; justify-content:space-between; align-items:center; gap:8px;}
.mcard-label{font-family:var(--mono); font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; color:var(--mut);}
.mcard-value{font-family:var(--mono); font-size:2rem; font-weight:600; color:var(--txt); margin:8px 0 12px; line-height:1;}
.mcard-value small{font-size:1rem; color:var(--mut); margin-left:2px;}
.gauge{position:relative; height:6px; border-radius:99px; background:#1a2230;}
.gauge-zone{position:absolute; top:0; bottom:0; border-radius:99px; background:rgba(52,211,153,.55);}
.gauge-mark{position:absolute; top:-5px; width:3px; height:16px; border-radius:2px; transform:translateX(-50%); background:var(--c);}
.gauge-scale{display:flex; justify-content:space-between; font-family:var(--mono); font-size:.64rem; color:var(--mut); margin-top:9px;}
.insight{border:1px solid var(--line); border-left:3px solid var(--c); border-radius:12px; padding:16px 18px; margin:0 0 14px; background:rgba(12,17,24,.9);}
.insight-h{display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:6px;}
.insight-h b{font-family:var(--head); font-size:1.04rem; color:var(--txt);}
.insight p{margin:4px 0 8px; color:#b4bfce; font-size:.93rem; line-height:1.55;}
.insight ul{margin:0; padding-left:18px; color:#d9e0ea; font-size:.92rem; line-height:1.7;}
.why{color:var(--acc2) !important; font-size:.86rem !important;}
.prio{display:flex; gap:12px; align-items:center; padding:12px 14px; border:1px solid var(--line); border-radius:12px; margin-bottom:8px; background:rgba(12,17,24,.88);}
.prio .num{width:28px; height:28px; border-radius:7px; display:grid; place-items:center; font-family:var(--mono); font-weight:600; color:#06090e; background:var(--c);}
.prio .t{flex:1; font-size:.92rem;} .prio .t b{color:var(--txt);}
.note{font-size:.78rem; color:var(--mut); line-height:1.5; border:1px dashed var(--line2); border-radius:10px; padding:10px 14px; margin-top:10px;}

/* ---------- onglets ---------- */
.stTabs [data-baseweb="tab-list"]{gap:4px; border-bottom:1px solid var(--line); flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{background:transparent; border:none; border-radius:8px 8px 0 0; padding:10px 16px; color:var(--mut); font-weight:500;}
.stTabs [data-baseweb="tab"]:hover{color:var(--txt);}
.stTabs [data-baseweb="tab-highlight"]{background-color:var(--acc) !important; height:2px;}
.stTabs [data-baseweb="tab-border"]{display:none;}
.stTabs [aria-selected="true"]{color:var(--acc) !important;}

/* ---------- champs ---------- */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div{background:var(--panel2) !important; border-color:var(--line2) !important; border-radius:10px !important;}
[data-baseweb="input"]:focus-within, [data-baseweb="base-input"]:focus-within, [data-baseweb="select"] > div:focus-within{border-color:var(--acc) !important; box-shadow:0 0 0 1px var(--acc) !important;}
.stApp input, .stApp textarea{background:transparent !important; color:var(--txt) !important; -webkit-text-fill-color:var(--txt) !important; caret-color:var(--acc);}
.stApp input::placeholder, .stApp textarea::placeholder{color:#5f6b7c !important; -webkit-text-fill-color:#5f6b7c !important;}
[data-baseweb="select"] *, [data-baseweb="tag"] span{color:var(--txt);}
[data-baseweb="tag"]{background:rgba(198,244,50,.14) !important; border-radius:6px !important;}
[data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [data-baseweb="menu"]{background:#111823 !important; color:var(--txt) !important; border:1px solid var(--line2);}
[data-baseweb="popover"] li:hover, [data-baseweb="menu"] li:hover{background:rgba(198,244,50,.1) !important;}
[data-testid="stNumberInput"] button{background:var(--panel2) !important; color:var(--txt) !important; border-color:var(--line2) !important;}
[data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child, [data-baseweb="radio"] > div:first-child{border-color:var(--line2) !important;}
[data-testid="stSlider"] [role="slider"]{background:var(--acc) !important; box-shadow:none !important;}
[data-testid="stSliderThumbValue"], [data-testid="stSlider"] [data-testid="stTickBarMin"], [data-testid="stSlider"] [data-testid="stTickBarMax"]{color:var(--mut) !important; font-family:var(--mono);}
[data-testid="stForm"]{background:rgba(12,17,24,.88); border:1px solid var(--line2) !important; border-radius:16px; padding:22px;}
[data-testid="stExpander"]{border:1px solid var(--line) !important; border-radius:12px; background:rgba(12,17,24,.6);}
[data-testid="stExpander"] summary{color:var(--txt);}
[data-testid="stAlert"]{border-radius:12px; border:1px solid var(--line2); background:var(--panel2); color:var(--txt);}
[data-testid="stFileUploader"] section{background:rgba(12,17,24,.88); border:1.5px dashed rgba(198,244,50,.4); border-radius:16px; padding:22px;}
[data-testid="stFileUploader"] section *{color:var(--txt);}
[data-testid="stMetric"]{background:rgba(12,17,24,.88); border:1px solid var(--line); border-radius:14px; padding:14px;}
[data-testid="stMetricValue"]{font-family:var(--mono);}
[data-testid="stDataFrame"]{border:1px solid var(--line); border-radius:12px;}
[data-testid="stProgress"] > div > div > div{background-color:var(--acc) !important;}

/* ---------- boutons : toujours lisibles, quel que soit le thème de l'appareil ---------- */
.stApp button[kind], .stApp [data-testid^="stBaseButton"], .stApp [data-testid="stFormSubmitButton"] button, .stApp .stDownloadButton button, .stApp [data-testid="stLinkButton"] a{
  background:var(--panel2) !important; color:var(--txt) !important; border:1px solid var(--line2) !important; border-radius:10px !important;
  font-weight:600 !important; min-height:2.6rem; transition:border-color .15s ease, transform .15s ease, background .15s ease;}
.stApp button[kind] p, .stApp [data-testid^="stBaseButton"] p, .stApp [data-testid="stFormSubmitButton"] button p{color:inherit !important;}
.stApp button[kind]:hover, .stApp [data-testid^="stBaseButton"]:hover, .stApp [data-testid="stFormSubmitButton"] button:hover{border-color:var(--acc) !important; color:var(--acc) !important;}
.stApp button[kind="primary"], .stApp button[kind="primaryFormSubmit"], .stApp [data-testid="stBaseButton-primary"], .stApp [data-testid="stBaseButton-primaryFormSubmit"],
.stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]{
  background:var(--acc) !important; color:#0a0f05 !important; border:1px solid var(--acc) !important; font-weight:700 !important; letter-spacing:.01em;}
.stApp button[kind="primary"]:hover, .stApp button[kind="primaryFormSubmit"]:hover, .stApp [data-testid="stBaseButton-primary"]:hover, .stApp [data-testid="stBaseButton-primaryFormSubmit"]:hover{
  background:#d8ff55 !important; color:#0a0f05 !important; transform:translateY(-1px);}
.stApp [data-testid="stFormSubmitButton"] button, .stApp [data-testid="stFormSubmitButton"] button *{opacity:1 !important;}
[data-testid="stFormSubmitButton"] button{width:100%;}

/* ---------- téléphone ---------- */
@media (max-width: 640px){
  .block-container{padding:3.6rem .85rem 3rem;}
  .hero{grid-template-columns:1fr; padding:22px 18px; border-radius:16px; margin-bottom:16px;}
  .hero h1{font-size:2.1rem; margin:14px 0 8px;}
  .hero p{font-size:.94rem;}
  .hero-badge{font-size:.62rem; padding:5px 9px; letter-spacing:.1em;}
  .hero-vis{margin-top:6px;}
  .glass{padding:16px; border-radius:14px;}
  .feat h4{font-size:1rem;}
  .score-wrap{flex-direction:column; text-align:center; gap:14px;}
  .ring{flex:0 0 auto; width:132px; height:132px;}
  .ring-in{width:108px; height:108px;}
  .ring-val{font-size:2.1rem;}
  .verdict h3{font-size:1.25rem;}
  .mcard{padding:12px 14px 10px;}
  .mcard-top{flex-wrap:wrap; gap:6px;}
  .mcard-value{font-size:1.7rem;}
  .insight{padding:13px 14px;}
  .prio{flex-wrap:wrap; gap:8px;}
  .stTabs [data-baseweb="tab-list"]{flex-wrap:nowrap; overflow-x:auto; -webkit-overflow-scrolling:touch; scrollbar-width:none;}
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar{display:none;}
  .stTabs [data-baseweb="tab"]{padding:9px 12px; white-space:nowrap; flex:0 0 auto; font-size:.88rem;}
  [data-testid="stForm"]{padding:16px;}
  [data-testid="stFileUploader"] section{padding:14px;}
  [data-testid="stMetric"]{padding:10px;}
  .step{padding:10px 0;}
}
</style>
"""

"""Habillage visuel de Axon : feuille de style, icônes SVG et bandeau d'en-tête.

Direction artistique « télémétrie » : fond encre, trame de mesure, une seule couleur d'accent
(jaune « volt »), chiffres en police mono. Le thème est entièrement forcé en CSS : il reste
identique sur ordinateur et sur téléphone, que l'appareil soit en mode clair ou sombre.
"""
import html as _esc
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

BRAND = "Axon"
BRAND_TAGLINE = "Étude posturale vélo"

# ------------------------------------------------------------------------------
#  LOGO AXON : emblème (cycliste en points articulaires sur un vélo dont le cadre forme un X) et nom dessiné
# ------------------------------------------------------------------------------
_EMB_WHEELS = '<circle cx="70" cy="160" r="45" fill="none" stroke="TIRE" stroke-width="6"/><circle cx="70" cy="160" r="40.5" fill="none" stroke="RIM" stroke-width="3"/><circle cx="70" cy="160" r="33" fill="none" stroke="RIM" stroke-width="1" opacity="0.5"/><path d="M75.0 160.0L103.0 160.0M74.2 162.7L97.8 177.8M73.1 163.9L90.6 185.8M70.5 165.0L73.4 192.8M68.9 164.9L62.7 192.2M66.4 163.5L46.5 183.2M65.5 162.2L40.3 174.3M65.0 159.4L37.2 156.0M65.5 157.8L40.3 145.7M67.4 155.7L52.7 131.9M68.9 155.1L62.7 127.8M71.7 155.3L81.1 128.9M73.1 156.1L90.6 134.2M74.7 158.4L101.2 149.3" stroke="RIM" stroke-width="0.8" opacity="0.55"/><circle cx="70" cy="160" r="5" fill="RIM"/><circle cx="230" cy="160" r="45" fill="none" stroke="TIRE" stroke-width="6"/><circle cx="230" cy="160" r="40.5" fill="none" stroke="RIM" stroke-width="3"/><circle cx="230" cy="160" r="33" fill="none" stroke="RIM" stroke-width="1" opacity="0.5"/><path d="M235.0 160.0L263.0 160.0M234.2 162.7L257.8 177.8M233.1 163.9L250.6 185.8M230.5 165.0L233.4 192.8M228.9 164.9L222.7 192.2M226.4 163.5L206.5 183.2M225.5 162.2L200.3 174.3M225.0 159.4L197.2 156.0M225.5 157.8L200.3 145.7M227.4 155.7L212.7 131.9M228.9 155.1L222.7 127.8M231.7 155.3L241.1 128.9M233.1 156.1L250.6 134.2M234.7 158.4L261.2 149.3" stroke="RIM" stroke-width="0.8" opacity="0.55"/><circle cx="230" cy="160" r="5" fill="RIM"/>'
_EMB_PARTS = '<path d="M70 154L128 156M70 166L128 184" stroke="RIM" stroke-width="1.6" opacity="0.7"/><circle cx="70" cy="160" r="7" fill="none" stroke="RIM" stroke-width="2"/><circle cx="128" cy="170" r="14.5" fill="none" stroke="RIM" stroke-width="3" stroke-dasharray="2.2 1.4"/><circle cx="128" cy="170" r="10" fill="none" stroke="RIM" stroke-width="2"/><path d="M128.5 173.0L152.0 167.8A2.0 2.0 0 0 1 151.3 163.9L127.5 167.0A3.0 3.0 0 0 1 128.5 173.0Z" fill="RIM"/><path d="M127.5 167.0L104.0 172.2A2.0 2.0 0 0 1 104.7 176.1L128.5 173.0A3.0 3.0 0 0 1 127.5 167.0Z" fill="RIM" opacity="0.7"/><circle cx="128" cy="170" r="4" fill="TIRE"/><rect x="144.6" y="163.8" width="14" height="4" rx="2" fill="RIM"/><rect x="97.4" y="172.2" width="14" height="4" rx="2" fill="RIM" opacity="0.7"/><path d="M89.5 67.3L132.1 119.0A4.8 4.8 0 0 1 139.7 113.2L100.5 58.7A7.0 7.0 0 0 1 89.5 67.3Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M132.2 113.2L93.8 164.3A3.2 3.2 0 0 1 99.0 168.3L139.6 119.0A4.8 4.8 0 0 1 132.2 113.2Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M90.6 171.5L111.1 178.3A2.5 2.5 0 0 1 112.9 173.7L93.4 164.5A3.8 3.8 0 0 1 90.6 171.5Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M89.5 67.3L132.1 119.0A4.8 4.8 0 0 1 139.7 113.2L100.5 58.7A7.0 7.0 0 0 1 89.5 67.3Z" fill="DIM"/><path d="M132.2 113.2L93.8 164.3A3.2 3.2 0 0 1 99.0 168.3L139.6 119.0A4.8 4.8 0 0 1 132.2 113.2Z" fill="DIM"/><path d="M90.6 171.5L111.1 178.3A2.5 2.5 0 0 1 112.9 173.7L93.4 164.5A3.8 3.8 0 0 1 90.6 171.5Z" fill="DIM"/><path d="M76 61Q80 55 92 56L118 58Q121 59 118 61L94 64Q84 65 76 61Z" fill="TIRE" stroke="RIM" stroke-width="1.5"/><path d="M208 50L226 46" stroke="RIM" stroke-width="5" stroke-linecap="round"/><path d="M226 46H234Q246 46 246 58V70Q246 78 238 78H234" fill="none" stroke="RIM" stroke-width="4" stroke-linecap="round"/><path d="M232 46L240 44L242 52Z" fill="RIM"/><path d="M91.5 69.6L151.9 98.7A5.0 5.0 0 0 1 156.5 89.9L98.5 56.4A7.5 7.5 0 0 1 91.5 69.6Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M149.2 93.6L142.4 157.3A3.2 3.2 0 0 1 148.8 158.1L159.2 95.0A5.0 5.0 0 0 1 149.2 93.6Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M139.7 163.5L162.1 170.3A2.5 2.5 0 0 1 163.9 165.7L142.3 156.5A3.8 3.8 0 0 1 139.7 163.5Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M164.6 30.9L191.4 60.3A3.5 3.5 0 0 1 196.6 55.7L171.4 25.1A4.5 4.5 0 0 1 164.6 30.9Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M194.3 61.7L236.2 57.7A2.8 2.8 0 0 1 235.8 52.3L193.7 54.3A3.8 3.8 0 0 1 194.3 61.7Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M98.0 68.5L100.3 65.9L102.6 63.5L105.1 61.1L107.6 58.8L110.3 56.7L113.0 54.7L115.8 52.7L118.6 50.9L121.4 48.9L124.3 47.1L127.2 45.3L130.2 43.7L133.3 42.1L136.4 40.7L139.6 39.4L142.8 38.2L146.1 37.0L149.4 35.9L152.7 34.9L156.1 34.1L159.5 33.4L163.0 32.8L166.5 32.3L170.0 32.0L170.0 20.0L166.0 19.8L162.0 19.8L158.0 19.9L154.0 20.2L150.0 20.7L146.0 21.3L142.0 22.0L138.1 22.9L134.2 24.0L130.4 25.3L126.6 26.8L122.8 28.3L119.1 30.1L115.5 31.9L112.0 33.9L108.5 36.1L105.3 38.6L102.1 41.2L99.1 44.0L96.3 46.9L93.5 49.9L90.9 53.0L88.4 56.2L86.0 59.5Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M173.1 28.9L183.9 25.4A3.5 3.5 0 0 1 182.1 18.6L170.9 21.1A4.0 4.0 0 0 1 173.1 28.9Z" fill="none" stroke="RING" stroke-width="5" stroke-linejoin="round"/><path d="M98.0 68.5L100.3 65.9L102.6 63.5L105.1 61.1L107.6 58.8L110.3 56.7L113.0 54.7L115.8 52.7L118.6 50.9L121.4 48.9L124.3 47.1L127.2 45.3L130.2 43.7L133.3 42.1L136.4 40.7L139.6 39.4L142.8 38.2L146.1 37.0L149.4 35.9L152.7 34.9L156.1 34.1L159.5 33.4L163.0 32.8L166.5 32.3L170.0 32.0L170.0 20.0L166.0 19.8L162.0 19.8L158.0 19.9L154.0 20.2L150.0 20.7L146.0 21.3L142.0 22.0L138.1 22.9L134.2 24.0L130.4 25.3L126.6 26.8L122.8 28.3L119.1 30.1L115.5 31.9L112.0 33.9L108.5 36.1L105.3 38.6L102.1 41.2L99.1 44.0L96.3 46.9L93.5 49.9L90.9 53.0L88.4 56.2L86.0 59.5Z" fill="url(#axon-skin)"/><path d="M173.1 28.9L183.9 25.4A3.5 3.5 0 0 1 182.1 18.6L170.9 21.1A4.0 4.0 0 0 1 173.1 28.9Z" fill="url(#axon-skin)"/><path d="M91.5 69.6L151.9 98.7A5.0 5.0 0 0 1 156.5 89.9L98.5 56.4A7.5 7.5 0 0 1 91.5 69.6Z" fill="url(#axon-skin)"/><path d="M149.2 93.6L142.4 157.3A3.2 3.2 0 0 1 148.8 158.1L159.2 95.0A5.0 5.0 0 0 1 149.2 93.6Z" fill="url(#axon-skin)"/><path d="M139.7 163.5L162.1 170.3A2.5 2.5 0 0 1 163.9 165.7L142.3 156.5A3.8 3.8 0 0 1 139.7 163.5Z" fill="url(#axon-skin)"/><path d="M164.6 30.9L191.4 60.3A3.5 3.5 0 0 1 196.6 55.7L171.4 25.1A4.5 4.5 0 0 1 164.6 30.9Z" fill="url(#axon-skin)"/><path d="M194.3 61.7L236.2 57.7A2.8 2.8 0 0 1 235.8 52.3L193.7 54.3A3.8 3.8 0 0 1 194.3 61.7Z" fill="url(#axon-skin)"/><path d="M139.7 163.5L162.1 170.3A2.5 2.5 0 0 1 163.9 165.7L142.3 156.5A3.8 3.8 0 0 1 139.7 163.5Z" fill="SHOE"/><path d="M90.6 171.5L111.1 178.3A2.5 2.5 0 0 1 112.9 173.7L93.4 164.5A3.8 3.8 0 0 1 90.6 171.5Z" fill="SHOE" opacity="0.8"/><circle cx="190" cy="21" r="10" fill="url(#axon-skin)" stroke="RING" stroke-width="3"/><path d="M176 18C175 5 197 -1 207 12L203 15C195 12 185 14 176 18Z" fill="ACC" stroke="RING" stroke-width="2.5" stroke-linejoin="round"/><path d="M186 8L192 7M182 11L188 9.5" stroke="RING" stroke-width="1.5" stroke-linecap="round" opacity="0.6"/><path d="M191 19.5H200Q201.5 19.5 201 21.5L200.5 23H192Z" fill="RING"/>'
_EMB_JOINTS = [(95, 63), (145.6, 157.7), (154.2, 94.3), (168, 28), (194, 58), (236, 55)]

_EMB_PAL = {
    "color": dict(frame="url(#axon-x-color)", skin="url(#axon-skin)", ring="#06090e", tire="#2a3340", rim="#b7c1ce", dim="#7b8696",
                  shoe="#e9eef4", wheel="#aeb8c6", nodes=["#c6f432", "#7ee98c", "#6fe597", "#49dcbc", "#36d3d6", "#22c5f0"]),
    "ink": dict(frame="url(#axon-x-ink)", skin="url(#axon-skin-ink)", ring="#f4f6f8", tire="#4a5566", rim="#4a5566", dim="#8a94a3",
                shoe="#06090e", wheel="#4a5566", nodes=["#4f7d00", "#1f8a52", "#1a885a", "#0f8a7a", "#0c848f", "#0a7fa8"]),
}
_EMB_DEFS = ('<defs><linearGradient id="axon-x-color" gradientUnits="userSpaceOnUse" x1="40" y1="0" x2="260" y2="0">'
             '<stop offset="0" stop-color="#c6f432"/><stop offset="0.5" stop-color="#4fe3a8"/><stop offset="1" stop-color="#22c5f0"/></linearGradient>'
             '<linearGradient id="axon-x-ink" gradientUnits="userSpaceOnUse" x1="40" y1="0" x2="260" y2="0">'
             '<stop offset="0" stop-color="#4f7d00"/><stop offset="0.5" stop-color="#0f8a6a"/><stop offset="1" stop-color="#0a7fa8"/></linearGradient>'
             '<linearGradient id="axon-skin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#cdd6e2"/></linearGradient>'
             '<linearGradient id="axon-skin-ink" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a3340"/><stop offset="1" stop-color="#06090e"/></linearGradient></defs>')


def _emb_fill(src: str, p: dict) -> str:
    for token, key in (("TIRE", "tire"), ("RIM", "rim"), ("RING", "ring"), ("DIM", "dim"), ("SHOE", "shoe")):
        src = src.replace(f'"{token}"', f'"{p[key]}"')
    return src.replace('"ACC"', f'"{p["nodes"][5]}"').replace('"url(#axon-skin)"', f'"{p["skin"]}"')


def emblem_svg(width=None, mode: str = "color", shade: str = "#1b2530", detail: bool = True, label: bool = True) -> str:
    """Emblème Axon en SVG (viewBox 300 x 220) : un cycliste dont les articulations sont marquées, sur un vélo dont le cadre forme un X.
    mode : "color" (fond sombre) ou "ink" (fond clair). detail=False : seulement le X et les roues (petites tailles)."""
    p = _EMB_PAL.get(mode, _EMB_PAL["color"])
    n = p["nodes"]
    size = f' width="{width}" height="{round(width * 220 / 300)}"' if width else ""
    aria = ' role="img" aria-label="Logo Axon : un cycliste sur un vélo dont le cadre forme un X"' if label else ' aria-hidden="true"'
    out = [f'<svg viewBox="0 0 300 220"{size}{aria}>', _EMB_DEFS]
    if detail:
        out.append(_emb_fill(_EMB_WHEELS, p))
    else:
        out += [f'<circle cx="{cx}" cy="160" r="46" fill="none" stroke="{p["wheel"]}" stroke-width="7"/>' for cx in (70, 230)]
    out += [f'<polygon points="238.7,30 257.3,30 79.3,160 60.7,160" fill="{p["frame"]}"/>',
            f'<polygon points="42.7,30 61.3,30 239.3,160 220.7,160" fill="{p["frame"]}" stroke="{p["ring"]}" stroke-width="5" paint-order="stroke"/>']
    if detail:
        out.append(_emb_fill(_EMB_PARTS, p))
        for (x, y), c in zip(_EMB_JOINTS, n):
            out.append(f'<circle cx="{x}" cy="{y}" r="4.6" fill="{c}" stroke="{p["ring"]}" stroke-width="2"/>')
    out += [f'<circle cx="70" cy="160" r="5.5" fill="{n[0]}" stroke="{p["ring"]}" stroke-width="2"/>',
            f'<circle cx="230" cy="160" r="5.5" fill="{n[5]}" stroke="{p["ring"]}" stroke-width="2"/>', "</svg>"]
    return "".join(out)


def wordmark_svg(height: int = 48, mode: str = "color") -> str:
    """Le nom AXON dessiné : A sans barre (petit trait en dégradé), X en deux bandes entrelacées, O carré arrondi, N géométrique."""
    ink, accent, bg = {"color": ("#f4f7fb", "url(#axon-word-color)", "#06090e"),
                       "ink": ("#06090e", "url(#axon-word-ink)", "#f4f6f8")}.get(mode, ("#f4f7fb", "url(#axon-word-color)", "#06090e"))
    w = round(height * 476 / 100)
    return (f'<svg class="axon-word" viewBox="0 0 476 100" width="{w}" height="{height}" role="img" aria-label="AXON">'
            '<defs><linearGradient id="axon-word-color" gradientUnits="userSpaceOnUse" x1="120" y1="0" x2="232" y2="0">'
            '<stop offset="0" stop-color="#c6f432"/><stop offset="1" stop-color="#22c5f0"/></linearGradient>'
            '<linearGradient id="axon-word-ink" gradientUnits="userSpaceOnUse" x1="120" y1="0" x2="232" y2="0">'
            '<stop offset="0" stop-color="#4f7d00"/><stop offset="1" stop-color="#0a7fa8"/></linearGradient></defs>'
            f'<polygon points="0,100 40,0 64,0 104,100 80,100 52,30 24,100" fill="{ink}"/>'
            f'<rect x="38" y="66" width="28" height="11" fill="{accent}"/>'
            f'<polygon points="206,0 232,0 146,100 120,100" fill="{accent}"/>'
            f'<polygon points="120,0 146,0 232,100 206,100" fill="{accent}" stroke="{bg}" stroke-width="5" paint-order="stroke"/>'
            '<path d="M280 0H324Q354 0 354 30V70Q354 100 324 100H280Q250 100 250 70V30Q250 0 280 0ZM286 22Q272 22 272 36V64Q272 78 286 78H318Q332 78 332 64V36Q332 22 318 22Z" '
            f'fill="{ink}" fill-rule="evenodd"/>'
            f'<polygon points="372,100 372,0 396,0 452,64 452,0 474,0 474,100 450,100 394,36 394,100" fill="{ink}"/></svg>')


def emblem_3d(layers: int = 11, depth: float = 18.0) -> str:
    """Emblème en relief qui tourne sur lui-même (CSS 3D, sans JavaScript) : copies en couleur empilées en profondeur,
    de plus en plus sombres vers le milieu, pour que les tranches gardent les couleurs du logo."""
    parts = []
    for i in range(layers):
        t = i / (layers - 1)
        z = (t - 0.5) * depth
        edge = i in (0, layers - 1)
        bright = 1.0 if edge else round(0.42 + 0.38 * abs(t - 0.5) * 2, 2)
        style = f"transform:translateZ({z:.1f}px)" + ("" if edge else f";filter:brightness({bright}) saturate(1.25)")
        parts.append(f'<div class="ly" style="{style}">{emblem_svg(None, "color", label=(i == layers - 1))}</div>')
    return f'<div class="emb3d"><div class="spin">{"".join(parts)}</div></div>'


def logo_mark(size: int = 40) -> str:
    """Petit symbole (en-tête, barre latérale) : l'emblème simplifié (X et roues) sur une tuile sombre."""
    return (f'<span class="axon-mark" style="width:{size}px;height:{size}px">'
            f'{emblem_svg(round(size * 0.9), detail=False, label=False)}</span>')


def logo(size: str = "lg", tagline: bool = True) -> str:
    """Logo complet (symbole + nom dessiné). size = "lg", "md" ou "sm"."""
    px, word = {"lg": (64, 44), "md": (40, 28), "sm": (32, 20)}[size]
    tag = f'<span class="axon-tag">{_esc.escape(BRAND_TAGLINE)}</span>' if tagline else ""
    return (f'<div class="axon-logo {size}" role="img" aria-label="{BRAND}">{logo_mark(px)}<div class="axon-words">'
            f'{wordmark_svg(word)}{tag}</div></div>')


def hero(title: str, text: str, badge: str = "", brand: bool = False) -> str:
    """Bandeau d'en-tête (HTML sur une ligne, prêt pour st.markdown). brand=True : le logo Axon remplace le titre."""
    top = f'<span class="hero-badge"><i></i>{badge}</span>' if badge else ""
    head = (f'<div class="hero-word">{wordmark_svg(72)}<span class="axon-tag">{_esc.escape(BRAND_TAGLINE)}</span></div>'
            if brand else f"<h1>{title}</h1>")
    html = f"""
    <div class="hero">
      <div class="hero-txt">
        {top}
        {head}
        <p>{text}</p>
      </div>
      <div class="hero-vis">{emblem_3d()}</div>
    </div>"""
    return re.sub(r"\s*\n\s*", " ", html.strip())


def _one(html: str) -> str:
    return re.sub(r"\s*\n\s*", " ", html.strip())


_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'


def appbar(brand: str, tagline: str = "", who: str = "") -> str:
    """En-tête compact des pages connectées. `brand` et `who` sont échappés."""
    w = f'<div class="who">{who}</div>' if who else ""
    return _one(f"""
    <div class="appbar">
      <div class="brand">{logo_mark(38)}
        <div><div class="name">{wordmark_svg(26) if brand == BRAND else _esc.escape(brand)}</div><div class="tag">{_esc.escape(tagline)}</div></div></div>
      {w}
    </div>""")


def stepper(steps) -> str:
    """Bandeau d'étapes. `steps` : liste de (titre, détail, état) avec état = "done", "now" ou "todo"."""
    out = []
    for i, (title, detail, state) in enumerate(steps, 1):
        mark = _CHECK if state == "done" else str(i)
        out.append(f'<div class="stp {state}"><div class="n">{mark}</div><div class="x"><div class="t">{_esc.escape(title)}</div>'
                   f'<div class="d">{_esc.escape(detail)}</div></div></div>')
    return '<div class="steps">' + "".join(out) + "</div>"


_MAIL_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
              '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5L12 13l8.5-6.5"/></svg>')


def contact_card(email: str) -> str:
    """Encart « Nous contacter » avec l'adresse cliquable."""
    e = _esc.escape(email)
    return (f'<div class="contact"><div class="ct-h">Nous contacter</div>'
            f'<p>Une question sur une analyse, votre compte ou un abonnement ? Écrivez-nous à cette adresse.</p>'
            f'<a class="ct-mail" href="mailto:{e}">{_MAIL_ICON}<span>{e}</span></a></div>')


def section(title: str, sub: str = "", first: bool = False) -> str:
    s = f'<div class="s">{sub}</div>' if sub else ""
    return f'<div class="sec{" first" if first else ""}"><div class="h">{_esc.escape(title)}</div>{s}</div>'


def form_section(title: str, sub: str = "", first: bool = False) -> str:
    s = f"<small>{_esc.escape(sub)}</small>" if sub else ""
    return f'<div class="fsec{" first" if first else ""}">{_esc.escape(title)}{s}</div>'


def cta(title: str, text: str) -> str:
    return f'<div class="cta"><b>{_esc.escape(title)}</b><p>{text}</p></div>'


def profile_card(name: str, rows) -> str:
    """Fiche du profil actif. `rows` : liste de (libellé, valeur, manquant?)."""
    body = "".join(f'<div class="row"><span>{_esc.escape(k)}</span><span class="{"miss" if miss else ""}">{_esc.escape(str(v))}</span></div>' for k, v, miss in rows)
    return f'<div class="pcard"><b>{_esc.escape(name)}</b>{body}</div>'


_WARN_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M12 3L2 20h20L12 3z"/><path d="M12 10v4.5M12 17.5v.5"/></svg>')


def banner(level: str, title: str, text: str, reasons=(), action: str = "") -> str:
    """Avertissement très visible en tête des résultats. level = "bad" (rouge) ou "warn" (orange).
    `title`, `reasons` et `action` sont échappés ; `text` peut contenir du HTML."""
    col = BAD if level == "bad" else WARN
    li = "".join(f"<li>{_esc.escape(r)}</li>" for r in reasons)
    act = f'<div class="do"><b>Que faire :</b> {_esc.escape(action)}</div>' if action else ""
    return (f'<div class="banner {level}" style="--c:{col}" role="alert"><div class="ic">{_WARN_ICON}</div><div class="bx">'
            f'<div class="bt">{_esc.escape(title)}</div><p>{text}</p>{"<ul>" + li + "</ul>" if li else ""}{act}</div></div>')


_ADJ_COLOR = {"bad": BAD, "warn": WARN, "info": ACCENT_2, "ok": OK}


def adjust_item(a: dict) -> str:
    """Une ligne de la liste des réglages (numéro identique à celui du vélo 3D)."""
    reasons = " · ".join(_esc.escape(r) for r in a.get("reasons", []))
    conf = ""
    if a.get("conflicts"):
        conf = "<em>À réévaluer après ce réglage : " + " · ".join(_esc.escape(c) for c in a["conflicts"]) + "</em>"
    return (f'<div class="adj" style="--c:{_ADJ_COLOR.get(a.get("status"), ACCENT_2)}"><div class="num">{int(a["n"])}</div>'
            f'<div class="t"><b>{_esc.escape(a["title"])}</b><span>{reasons}</span>{conf}</div></div>')


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{
  --bg:#06090e; --panel:#0c1118; --panel2:#111823; --line:rgba(255,255,255,.09); --line2:rgba(255,255,255,.16);
  --txt:#eef2f7; --mut:#9aa6b8; --acc:#c6f432; --acc2:#5ec8ff; --ok:#34d399; --warn:#fbbf24; --bad:#fb7185;
  --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace; --head:'Space Grotesk','Inter',sans-serif;
  color-scheme:dark;
}
html, body, .stApp{font-family:'Inter',-apple-system,'Segoe UI',sans-serif; color:var(--txt); color-scheme:dark; -webkit-text-size-adjust:100%;}
.stApp{background-color:var(--bg);
  background-image:radial-gradient(rgba(255,255,255,.07) 1px, transparent 1.2px), radial-gradient(900px 420px at 85% -8%, rgba(198,244,50,.07), transparent 65%);
  background-size:26px 26px, auto; background-attachment:fixed; overflow-x:hidden;}
header[data-testid="stHeader"]{background:transparent;}
[data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stDecoration"], .stAppDeployButton, #MainMenu, footer{display:none !important;}
/* le bouton qui ouvre / ferme la barre latérale doit toujours rester visible */
[data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"]{display:flex !important; visibility:visible !important; opacity:1 !important;}
[data-testid="stSidebarCollapsedControl"] button, [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] button{color:var(--acc) !important; background:var(--panel2) !important; border:1px solid var(--line2) !important; border-radius:10px !important; min-height:2.2rem;}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{visibility:visible !important;}
.block-container{padding-top:3.2rem; max-width:1280px;}
h1,h2,h3,h4,h5{font-family:var(--head); color:var(--txt); letter-spacing:-.01em;}
.stApp :where(p, li, label, span), .stApp :where([data-testid="stMarkdownContainer"]){color:inherit;}
.stApp [data-testid="stWidgetLabel"] p, .stApp label p{color:var(--txt);}
.stApp :where([data-testid="stMarkdownContainer"]) :where(p, li){color:var(--txt);}
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p{color:var(--mut); font-size:.88rem; line-height:1.5;}
a{color:var(--acc);}

/* ---------- barre latérale ---------- */
[data-testid="stSidebar"]{background:#080c12; border-right:1px solid var(--line);}
[data-testid="stSidebar"] h3{font-family:var(--head); font-size:1.05rem; color:var(--txt);}
[data-testid="stSidebar"] h3::before{content:""; display:inline-block; width:10px; height:10px; background:var(--acc); border-radius:3px; margin-right:9px; transform:rotate(45deg);}
.side-sec{font-family:var(--mono); font-size:.72rem; text-transform:uppercase; letter-spacing:.16em; color:var(--mut); margin:20px 0 6px; padding-top:12px; border-top:1px solid var(--line);}

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
.chip{--c:var(--ok); display:inline-flex; align-items:center; gap:6px; font-family:var(--mono); font-size:.7rem; font-weight:500; letter-spacing:.06em; text-transform:uppercase; color:var(--c);
  border:1px solid var(--c); background:rgba(255,255,255,.04); padding:4px 9px; border-radius:6px; white-space:nowrap;}
.chip::before{content:""; width:6px; height:6px; border-radius:50%; background:var(--c);}
@supports (color: color-mix(in srgb, red 50%, blue)){
  .chip{border-color:color-mix(in srgb, var(--c) 50%, transparent); background:color-mix(in srgb, var(--c) 10%, transparent);}
  .insight{background:linear-gradient(90deg, color-mix(in srgb, var(--c) 6%, transparent), transparent 55%), rgba(12,17,24,.9);}
}
.mcard{background:rgba(12,17,24,.88); border:1px solid var(--line); border-radius:14px; padding:14px 16px 12px; margin-bottom:12px; transition:border-color .2s ease;}
.mcard:hover{border-color:var(--line2);}
.mcard-top{display:flex; justify-content:space-between; align-items:center; gap:8px;}
.mcard-label{font-size:.92rem; font-weight:600; color:var(--txt);}
.mcard-value{font-family:var(--mono); font-size:2rem; font-weight:600; color:var(--txt); margin:8px 0 12px; line-height:1;}
.mcard-value small{font-size:1rem; color:var(--mut); margin-left:2px;}
.gauge{position:relative; height:6px; border-radius:99px; background:#1a2230;}
.gauge-zone{position:absolute; top:0; bottom:0; border-radius:99px; background:rgba(52,211,153,.55);}
.gauge-mark{position:absolute; top:-5px; width:3px; height:16px; border-radius:2px; transform:translateX(-50%); background:var(--c);}
.gauge-scale{display:flex; justify-content:space-between; font-family:var(--mono); font-size:.72rem; color:var(--mut); margin-top:9px;}
.insight{border:1px solid var(--line); border-left:3px solid var(--c); border-radius:12px; padding:16px 18px; margin:0 0 14px; background:rgba(12,17,24,.9);}
.insight-h{display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:6px;}
.insight-h b{font-family:var(--head); font-size:1.04rem; color:var(--txt);}
.insight p{margin:4px 0 8px; color:#b4bfce; font-size:.93rem; line-height:1.55;}
.insight ul{margin:0; padding-left:18px; color:#d9e0ea; font-size:.92rem; line-height:1.7;}
.why{color:var(--acc2) !important; font-size:.86rem !important;}
.prio{display:flex; gap:12px; align-items:center; padding:12px 14px; border:1px solid var(--line); border-radius:12px; margin-bottom:8px; background:rgba(12,17,24,.88);}
.prio .num{width:28px; height:28px; border-radius:7px; display:grid; place-items:center; font-family:var(--mono); font-weight:600; color:#06090e; background:var(--c);}
.prio .t{flex:1; font-size:.92rem;} .prio .t b{color:var(--txt);}
.note{font-size:.86rem; color:var(--mut); line-height:1.55; border:1px dashed var(--line2); border-radius:10px; padding:10px 14px; margin-top:10px;}

/* ---------- onglets : niveau 1 = navigation (soulignée), niveau 2 = rubriques (pastilles), niveau 3 = sous-rubriques ---------- */
:is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-list"]{gap:4px; border-bottom:1px solid var(--line); flex-wrap:wrap;}
:is(.stTabs,[data-testid="stTabs"]) button[role="tab"]{background:transparent; border:none; border-radius:8px 8px 0 0; padding:11px 18px; color:var(--mut); font-weight:600; font-size:1rem; min-height:0; height:auto;}
.stApp button[role="tab"] p{color:inherit !important; font-size:inherit !important; font-weight:inherit !important;}
:is(.stTabs,[data-testid="stTabs"]) button[role="tab"]:hover{color:var(--txt);}
:is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-highlight"]{background-color:var(--acc) !important; height:3px;}
:is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-border"]{display:none;}
:is(.stTabs,[data-testid="stTabs"]) button[role="tab"][aria-selected="true"]{color:var(--acc) !important; box-shadow:inset 0 -3px 0 var(--acc);}

:is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-list"]{gap:8px; border-bottom:none; padding:2px 0 12px;}
:is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) button[role="tab"]{background:var(--panel2); border:1px solid var(--line2); border-radius:999px; padding:9px 17px; color:#c9d2de; font-weight:600; font-size:.93rem; box-shadow:none;}
:is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) button[role="tab"]:hover{border-color:var(--acc); color:var(--acc);}
:is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-highlight"]{display:none !important;}
:is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) button[role="tab"][aria-selected="true"]{background:var(--acc) !important; border-color:var(--acc) !important; color:#0a0f05 !important; box-shadow:none;}

:is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-list"]{gap:2px; border-bottom:1px solid var(--line); padding:0; margin-bottom:6px;}
:is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) button[role="tab"]{background:transparent !important; border:none; border-radius:6px 6px 0 0; padding:9px 15px; color:var(--mut) !important; font-weight:500; font-size:.93rem;}
:is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) button[role="tab"]:hover{color:var(--txt) !important;}
:is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) button[role="tab"][aria-selected="true"]{color:var(--acc2) !important; box-shadow:inset 0 -2px 0 var(--acc2);}

/* ---------- en-tête compact, étapes, titres de section ---------- */
.appbar{display:flex; align-items:center; justify-content:space-between; gap:14px; flex-wrap:wrap; margin:0 0 16px;}
.appbar .brand{display:flex; align-items:center; gap:12px; min-width:0;}
.appbar .axon-mark{flex:0 0 38px;}

/* ---------- logo Axon ---------- */
.axon-logo{display:flex; align-items:center; gap:14px;}
.axon-mark{display:inline-flex; align-items:center; justify-content:center; flex:0 0 auto; border-radius:22%; background:#111823; border:1px solid rgba(255,255,255,.12); box-sizing:border-box;}
.axon-mark svg{display:block;}
.axon-word{display:block; height:auto;}
.hero-word{display:flex; flex-direction:column; gap:14px; margin:6px 0 20px;}
.hero-word .axon-word{width:min(100%, 340px);}
.hero-word .axon-tag{font-size:.82rem; letter-spacing:.32em; color:#c9d2de; margin-top:0;}
/* emblème en relief qui tourne sur lui-même */
.emb3d{perspective:1000px; display:flex; align-items:center; justify-content:center; padding:10px 0;}
.emb3d .spin{position:relative; width:min(100%, 400px); aspect-ratio:300 / 220; transform-style:preserve-3d; animation:axspin 9s linear infinite;}
.emb3d .ly{position:absolute; inset:0;}
.emb3d .ly svg{width:100%; height:100%; display:block;}
@keyframes axspin{from{transform:rotateX(-8deg) rotateY(0deg)} to{transform:rotateX(-8deg) rotateY(360deg)}}
@media (prefers-reduced-motion:reduce){.emb3d .spin{animation:none; transform:rotateX(-8deg) rotateY(-20deg);}}
.axon-words{display:flex; flex-direction:column; line-height:1;}
.axon-name{font-family:var(--head); font-weight:700; letter-spacing:.14em; color:var(--txt);}
.axon-tag{font-family:var(--mono); font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; color:var(--acc); margin-top:7px;}
.axon-logo.lg{gap:18px;} .axon-logo.md{gap:12px;}
.axon-logo.sm .axon-tag{font-size:.6rem; margin-top:6px;} .axon-logo.sm{gap:10px; margin:2px 0 6px;}
.hero-logo{margin:4px 0 18px;}

/* ---------- nous contacter ---------- */
.side-contact{font-size:.82rem; color:var(--mut); margin-top:10px; line-height:1.5; word-break:break-all;}
.side-contact a{color:var(--acc) !important;}
.contact{border:1px solid var(--line2); border-radius:16px; padding:22px; background:rgba(12,17,24,.88);}
.contact .ct-h{font-family:var(--head); font-size:1.3rem; font-weight:700; color:var(--txt); margin:0 0 6px;}
.contact p{color:var(--mut) !important; margin:0 0 14px !important; line-height:1.55;}
.contact .ct-mail{display:inline-flex; align-items:center; gap:10px; font-family:var(--mono); font-size:1.05rem; color:var(--acc) !important; text-decoration:none;
  border:1px solid rgba(198,244,50,.45); background:rgba(198,244,50,.07); border-radius:10px; padding:10px 14px; word-break:break-all;}
.contact .ct-mail:hover{background:rgba(198,244,50,.14);}
.contact .ct-mail svg{width:20px; height:20px; flex:0 0 20px;}
.appbar .name{font-family:var(--head); font-size:1.5rem; font-weight:700; letter-spacing:-.02em; line-height:1.1; color:var(--txt);}
.appbar .tag{font-size:.9rem; color:var(--mut); margin-top:2px; line-height:1.35;}
.appbar .who{font-size:.88rem; color:var(--mut); text-align:right; line-height:1.4;}
.appbar .who b{color:var(--txt); font-weight:600;}
.steps{display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:4px 0 20px;}
.stp{display:flex; gap:12px; align-items:center; padding:12px 14px; border:1px solid var(--line); border-radius:12px; background:rgba(12,17,24,.88); min-width:0;}
.stp .n{flex:0 0 30px; width:30px; height:30px; border-radius:50%; display:grid; place-items:center; font-family:var(--mono); font-weight:600; font-size:.9rem; border:1.5px solid var(--line2); color:var(--mut);}
.stp .n svg{width:16px; height:16px;}
.stp .x{min-width:0;}
.stp .t{font-weight:600; font-size:.96rem; color:var(--mut); line-height:1.25;}
.stp .d{font-size:.84rem; color:var(--mut); line-height:1.35; overflow:hidden; text-overflow:ellipsis;}
.stp.done .n{background:rgba(52,211,153,.14); border-color:var(--ok); color:var(--ok);}
.stp.done .t{color:var(--txt);}
.stp.now{border-color:var(--acc); background:rgba(198,244,50,.06);}
.stp.now .n{background:var(--acc); border-color:var(--acc); color:#0a0f05;}
.stp.now .t{color:var(--txt);} .stp.now .d{color:#c9d2de;}
.sec{margin:28px 0 14px;}
.sec.first{margin-top:4px;}
.sec .h{font-family:var(--head); font-size:1.25rem; font-weight:600; letter-spacing:-.01em; color:var(--txt); display:flex; align-items:center; gap:10px; line-height:1.25;}
.sec .h::before{content:""; flex:0 0 4px; height:20px; border-radius:2px; background:var(--acc);}
.sec .s{margin:5px 0 0 14px; color:var(--mut); font-size:.93rem; line-height:1.55; max-width:78ch;}
.fsec{font-family:var(--head); font-size:1.02rem; font-weight:600; color:var(--txt); margin:18px 0 2px; padding-top:14px; border-top:1px solid var(--line);}
.fsec.first{border-top:none; padding-top:0; margin-top:6px;}
.fsec small{display:block; font-family:'Inter',sans-serif; font-weight:400; font-size:.86rem; color:var(--mut); margin-top:2px;}
.cta{border:1px solid rgba(198,244,50,.45); background:rgba(198,244,50,.06); border-radius:14px; padding:16px 18px; margin:0 0 14px;}
.cta b{font-family:var(--head); font-size:1.1rem; color:var(--txt);}
.cta p{margin:4px 0 0; color:#b4bfce; font-size:.94rem; line-height:1.55;}
.sum-chips{display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 0;}

/* ---------- avertissement de fiabilité : doit se voir avant tout le reste ---------- */
.banner{--c:var(--bad); display:flex; gap:16px; align-items:flex-start; border:2px solid var(--c); border-radius:14px; padding:18px 20px; margin:4px 0 18px; background:rgba(251,113,133,.13);}
.banner.warn{background:rgba(251,191,36,.11);}
.banner .ic{flex:0 0 44px; width:44px; height:44px; border-radius:12px; display:grid; place-items:center; background:var(--c); color:#0a0f05;}
.banner .ic svg{width:26px; height:26px;}
.banner .bx{flex:1; min-width:0;}
.banner .bt{font-family:var(--head); font-size:1.3rem; font-weight:700; line-height:1.25; color:var(--c);}
.banner p{margin:6px 0 0 !important; color:var(--txt) !important; font-size:.98rem; line-height:1.55;}
.banner ul{margin:8px 0 0; padding-left:18px; color:#c9d2de; font-size:.92rem; line-height:1.6;}
.banner li{color:#c9d2de !important;}
.banner .do{margin-top:10px; padding:10px 12px; border-radius:10px; background:rgba(6,9,14,.55); color:var(--txt); font-size:.95rem; line-height:1.5;}
.banner .do b{color:var(--c);}

/* ---------- liste numérotée des réglages (mêmes numéros que sur le vélo 3D) ---------- */
.adj{--c:var(--acc2); display:flex; gap:12px; align-items:flex-start; padding:12px 14px; border:1px solid var(--line); border-left:3px solid var(--c); border-radius:12px; margin-bottom:8px; background:rgba(12,17,24,.88);}
.adj .num{flex:0 0 28px; width:28px; height:28px; border-radius:50%; display:grid; place-items:center; font-weight:700; font-size:.9rem; color:#06090e; background:var(--c);}
.adj .t{flex:1; min-width:0;}
.adj .t b{display:block; color:var(--txt); font-size:.98rem; line-height:1.35; font-weight:600;}
.adj .t span{display:block; color:var(--mut); font-size:.87rem; line-height:1.45; margin-top:2px;}
.adj .t em{display:block; font-style:normal; color:var(--warn); font-size:.85rem; line-height:1.45; margin-top:3px;}
.adj-h{font-family:var(--mono); font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--mut); margin:14px 0 8px;}
.adj-h:first-child{margin-top:0;}

/* ---------- fiche du profil actif (barre latérale) ---------- */
.pcard{border:1px solid var(--line2); border-radius:12px; padding:12px 14px; background:rgba(17,24,35,.9);}
.pcard b{display:block; font-size:1rem; color:var(--txt); margin-bottom:4px; overflow:hidden; text-overflow:ellipsis;}
.pcard .row{display:flex; justify-content:space-between; gap:10px; font-size:.86rem; padding:3px 0; color:var(--mut);}
.pcard .row span:last-child{color:var(--txt); text-align:right;}
.pcard .miss{color:var(--warn) !important;}

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


/* ---------- saisie lisible sur iPhone / Safari (texte, points du mot de passe, remplissage automatique) ---------- */
.stApp [data-baseweb="input"] input, .stApp [data-baseweb="base-input"] input, .stApp [data-testid="stTextInputRootElement"] input,
.stApp [data-testid="stNumberInputContainer"] input, .stApp textarea{
  color:#eef2f7 !important; -webkit-text-fill-color:#eef2f7 !important; opacity:1 !important; background-color:transparent !important;
  font-size:16px !important; -webkit-appearance:none; appearance:none;}
.stApp input:-webkit-autofill, .stApp input:-webkit-autofill:hover, .stApp input:-webkit-autofill:focus, .stApp input:-internal-autofill-selected{
  -webkit-text-fill-color:#eef2f7 !important; caret-color:#c6f432; -webkit-box-shadow:0 0 0 1000px #111823 inset !important; box-shadow:0 0 0 1000px #111823 inset !important;
  transition:background-color 9999s ease-out 0s;}
.stApp [data-testid="stTextInputRootElement"], .stApp [data-testid="stNumberInputContainer"]{background:#111823 !important; border-radius:10px;}


/* ---------- messages (erreur, succès, info) : toujours lisibles ---------- */
.stApp [data-testid="stAlert"]{background:#111823 !important; border:1px solid var(--line2) !important; border-radius:12px !important;}
.stApp [data-testid="stAlert"] *{color:#eef2f7 !important; -webkit-text-fill-color:#eef2f7 !important; opacity:1 !important;}
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"]){background:rgba(251,113,133,.14) !important; border-color:rgba(251,113,133,.65) !important;}
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) *{color:#ffc2cb !important; -webkit-text-fill-color:#ffc2cb !important;}
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]){background:rgba(251,191,36,.12) !important; border-color:rgba(251,191,36,.6) !important;}
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) *{color:#fde7a6 !important; -webkit-text-fill-color:#fde7a6 !important;}
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]){background:rgba(52,211,153,.12) !important; border-color:rgba(52,211,153,.6) !important;}
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) *{color:#b6f3dc !important; -webkit-text-fill-color:#b6f3dc !important;}
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]){background:rgba(94,200,255,.1) !important; border-color:rgba(94,200,255,.5) !important;}
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) *{color:#cdeeff !important; -webkit-text-fill-color:#cdeeff !important;}
/* champ en état d'erreur ou rempli : le texte reste clair */
.stApp input[aria-invalid="true"], .stApp [aria-invalid="true"] input, .stApp input:focus, .stApp input:not(:placeholder-shown){
  color:#eef2f7 !important; -webkit-text-fill-color:#eef2f7 !important; background-color:transparent !important;}
.stApp [data-baseweb="input"][aria-invalid="true"], .stApp [data-baseweb="base-input"][aria-invalid="true"]{background:#111823 !important; border-color:#fb7185 !important;}

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
  :is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-list"]{flex-wrap:nowrap !important; overflow-x:auto; -webkit-overflow-scrolling:touch; scrollbar-width:none;}
  :is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-list"]::-webkit-scrollbar{display:none;}
  :is(.stTabs,[data-testid="stTabs"]) button[role="tab"]{padding:10px 13px; white-space:nowrap; flex:0 0 auto; font-size:.93rem;}
  :is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-list"]{flex-wrap:wrap !important; overflow-x:visible; gap:6px;}
  :is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) button[role="tab"]{padding:8px 13px; font-size:.9rem;}
  :is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) :is(.stTabs,[data-testid="stTabs"]) [data-baseweb="tab-list"]{flex-wrap:nowrap !important; overflow-x:auto; gap:2px;}
  .appbar .name{font-size:1.25rem;} .appbar .who{display:none;}
  .hero-word .axon-word{width:min(100%, 260px);} .hero-word{margin-bottom:14px;}
  .emb3d .spin{width:min(100%, 300px);}
  .contact{padding:16px;} .contact .ct-mail{font-size:.95rem;}
  .steps{grid-template-columns:1fr; gap:6px; margin-bottom:16px;}
  .stp{padding:9px 12px;}
  .sec{margin:22px 0 12px;} .sec .h{font-size:1.12rem;} .sec .s{margin-left:0;}
  .adj{padding:11px 12px;}
  .banner{padding:14px; gap:12px;} .banner .ic{flex-basis:36px; width:36px; height:36px;} .banner .ic svg{width:21px; height:21px;} .banner .bt{font-size:1.1rem;}
  [data-testid="stForm"]{padding:16px;}
  [data-testid="stFileUploader"] section{padding:14px;}
  [data-testid="stMetric"]{padding:10px;}
  .step{padding:10px 0;}
}
</style>
"""

#!/usr/bin/env python3
"""
Builds the README's SVG panels in light and dark.

    pip install fonttools brotli
    python3 assets/build.py

Fonts are subset to the glyphs each panel uses and embedded as WOFF2, because GitHub serves
README images through a proxy that blocks any external font. Newsreader and Hanken Grotesk are
open-licence stand-ins for Delvaux's Genath and Atlas Grotesk (SIL OFL 1.1, see fonts/).
"""
import base64
import io
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).parent
FONTS = HERE / "fonts"

# Three colours, swapped between themes: ink, paper and one grey. The hero card is the
# inverse of the page, so it reads as ink-on-white in light mode and white-on-ink in dark.
THEMES = {
    "light": dict(ink="#1D1D1B", paper="#F2F2F0", grey="#8E8E8C"),
    "dark": dict(ink="#F2F2F0", paper="#1D1D1B", grey="#8A8A88"),
}

# Animation: transform + opacity only, strong ease-out for entrances, ease-in-out for the rule.
EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)"
EASE_IN_OUT = "cubic-bezier(0.77, 0, 0.175, 1)"

LICENCE = ("<!-- Fonts: Newsreader (c) 2020 The Newsreader Project Authors; Hanken Grotesk (c) 2021 "
           "The Hanken Grotesk Project Authors. Subsets embedded under the SIL Open Font License 1.1. -->")


class Face:
    def __init__(self, family, file, axes):
        self.family = family
        self.font = instancer.instantiateVariableFont(TTFont(FONTS / file), axes)
        self.upm = self.font["head"].unitsPerEm
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font["hmtx"]
        self.used = set()

    def width(self, text, size, tracking=0.0):
        adv = sum(self.hmtx[self.cmap[ord(c)]][0] for c in text if ord(c) in self.cmap)
        return adv * size / self.upm + tracking * size * max(len(text) - 1, 0)

    def use(self, text):
        self.used.update(text + text.upper())  # caps are set with text-transform
        return text

    def css(self):
        buf = io.BytesIO()
        self.font.save(buf)
        buf.seek(0)
        f = TTFont(buf)
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "case"]
        opts.notdef_outline = True
        s = subset.Subsetter(opts)
        s.populate(text="".join(sorted(self.used)) + " ")
        s.subset(f)
        out = io.BytesIO()
        f.flavor = "woff2"
        f.save(out)
        data = base64.b64encode(out.getvalue()).decode()
        return f"@font-face {{ font-family: '{self.family}'; src: url(data:font/woff2;base64,{data}) format('woff2'); }}"


def faces():
    return (Face("JP Display", "Newsreader.ttf", {"wght": 300, "opsz": 72}),
            Face("JP Sans", "HankenGrotesk.ttf", {"wght": 400}),
            Face("JP Sans Light", "HankenGrotesk.ttf", {"wght": 300}))


def base_css(t, extra=""):
    return f"""
    .disp {{ font-family: 'JP Display', serif; fill: {t['ink']}; }}
    .caps {{ font-family: 'JP Sans', sans-serif; fill: {t['grey']}; text-transform: uppercase; }}
    .body {{ font-family: 'JP Sans Light', sans-serif; fill: {t['ink']}; }}
    .grey {{ fill: {t['grey']}; }}
    .rule {{ stroke: {t['grey']}; stroke-opacity: 0.45; stroke-width: 1; }}
    .from-left {{ transform-box: fill-box; transform-origin: left center; }}
    .bx {{ transform-box: fill-box; transform-origin: center; }}

    /* Each keyframe names only its starting point: the resting state is the plain, visible one,
       so a renderer that skips CSS animation still shows everything in place. */
    @media (prefers-reduced-motion: no-preference) {{
      .rise {{ animation: rise 1s {EASE_OUT} both; }}
      .draw {{ animation: draw 1.1s {EASE_IN_OUT} both; }}
      .fade {{ animation: fade 0.8s {EASE_OUT} both; }}
      .lift {{ animation: lift 0.8s {EASE_OUT} both; }}
      .rise {{ transform-box: fill-box; }}
      /* Constant motion is linear; the pulse is a slow breath, not a blink. */
      .pulse {{ animation: pulse 2.4s {EASE_IN_OUT} infinite; }}
      .odo {{ animation: odo {ODO_CYCLE}s {EASE_IN_OUT} 2.2s infinite; }}
    }}
    @keyframes pulse {{ 50% {{ opacity: 0.3; }} }}
    /* Odometer: hold each phrase, then a short eased step up to the next. The last row repeats
       the first, so the jump back to 0 is invisible. At rest it shows the first phrase. */
    @keyframes odo {{
      0%, 21% {{ transform: translateY(0); }}
      25%, 46% {{ transform: translateY(-{ODO_LH}px); }}
      50%, 71% {{ transform: translateY(-{2 * ODO_LH}px); }}
      75%, 96% {{ transform: translateY(-{3 * ODO_LH}px); }}
      100% {{ transform: translateY(-{4 * ODO_LH}px); }}
    }}
    @keyframes rise {{ from {{ transform: translateY(105%); }} }}
    @keyframes draw {{ from {{ transform: scaleX(0); }} }}
    @keyframes fade {{ from {{ opacity: 0; }} }}
    @keyframes lift {{ from {{ opacity: 0; transform: translateY(10px); }} }}
{extra}"""


def write(name, w, h, title, desc, body, css_fn, used_faces):
    for theme, t in THEMES.items():
        fonts = "\n    ".join(f.css() for f in used_faces)
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">
  {LICENCE}
  <title id="t">{title}</title>
  <desc id="d">{desc}</desc>
  <style>
    {fonts}
    {css_fn(t)}
  </style>
{body(t)}
</svg>
"""
        (HERE / f"{name}-{theme}.svg").write_text(svg)


def delay(s):
    return f' style="animation-delay:{s:.2f}s"'


# ---------------------------------------------------------------- hero
ODO = [("Now", "software engineer at Balerion"),
       ("Side quest", "an e-commerce tool that shows shops their real profit"),
       ("Off the clock", "writing music"),
       ("Always", "build with purpose")]
ODO_LH, ODO_CYCLE = 40, 13
TICKER = ["Go", "TypeScript", "React", "Next.js", "TanStack", "PostgreSQL", "Redis", "GCP", "Docker"]


def build_hero():
    disp, sans, light = faces()
    W, H, M, SIZE, TRACK = 880, 460, 36, 178, -0.022

    # The name is set letter by letter so each can rise on its own; positions come from the font.
    name = disp.use("Josh Perry")
    letters, x = [], float(M - 8)
    for ch in name:
        if ch != " ":
            letters.append((ch, x))
        x += disp.width(ch, SIZE) + TRACK * SIZE

    # Ticker: the strip is several copies of one sequence and slides left by exactly one copy,
    # measured from the font, so the loop has no seam and the strip never runs out.
    gap = "\u00a0\u00a0\u00a0/\u00a0\u00a0\u00a0"
    seq = sans.use("".join(f"{w}{gap}" for w in TICKER))

    def copy_w(size, ls):
        return sans.width(seq.upper(), size) + ls * len(seq)

    w_wide, w_narrow = copy_w(13, 1.2), copy_w(30, 1.0)
    copies = int(W / w_wide) + 2
    strip = seq * max(copies, int(W / w_narrow * 2.2) + 2)
    speed = 28  # px per second at desktop size
    for k, v in ODO:
        light.use(f"{k} — {v}")

    def body(t):
        name_svg = "\n".join(
            f'      <text class="disp rise" x="{lx:.1f}" y="262" font-size="{SIZE}" style="fill:{t["paper"]};animation-delay:{0.15 + i * 0.045:.3f}s">{ch}</text>'
            for i, (ch, lx) in enumerate(letters))
        base_y = 342
        rows = ODO + ODO[:1]
        odo_svg = "\n".join(
            f'          <text class="body" x="{M + 22}" y="{base_y + i * ODO_LH}" font-size="21" style="fill:{t["paper"]}">'
            f'<tspan style="fill:{t["grey"]}">{k} — </tspan>{v}</text>'
            for i, (k, v) in enumerate(rows))
        return f"""  <defs>
    <clipPath id="card"><rect width="{W}" height="{H}" rx="6"/></clipPath>
    <clipPath id="name"><rect x="0" y="80" width="{W}" height="222"/></clipPath>
    <clipPath id="slot"><rect x="{M + 16}" y="{base_y - 27}" width="{W - M * 2}" height="{ODO_LH}"/></clipPath>
  </defs>
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="{t['ink']}"/>

    <g class="fade"{delay(0.05)}>
      <text class="caps" x="{M}" y="50" font-size="13" letter-spacing="0.6">Full-Stack Developer</text>
      <text class="caps" x="{W - M}" y="50" font-size="13" letter-spacing="0.6" text-anchor="end">Bangkok</text>
    </g>
    <line class="rule draw from-left" x1="{M}" y1="72.5" x2="{W - M}" y2="72.5"{delay(0.1)}/>

    <g clip-path="url(#name)">
{name_svg}
    </g>

    <g class="status-n">
      <g class="lift"{delay(0.9)}>
        <circle class="pulse" cx="{M + 5}" cy="335" r="4.5" fill="{t['paper']}"/>
        <g clip-path="url(#slot)"><g class="odo">
{odo_svg}
        </g></g>
      </g>
    </g>

    <line class="rule draw from-left" x1="0" y1="386.5" x2="{W}" y2="386.5"{delay(0.6)}/>
    <g class="fade"{delay(1.1)}>
      <text class="caps ticker" x="{M}" y="430" font-size="13" letter-spacing="1.2">{strip}</text>
    </g>
  </g>"""

    extra = f"""
    @media (prefers-reduced-motion: no-preference) {{
      .ticker {{ animation: ticker {w_wide / speed:.1f}s linear infinite; }}
    }}
    .ticker {{ font-kerning: none; font-feature-settings: "kern" 0, "liga" 0; }}  /* match the measured width */
    @keyframes ticker {{ to {{ transform: translateX(-{w_wide:.2f}px); }} }}
    @keyframes ticker-n {{ to {{ transform: translateX(-{w_narrow:.2f}px); }} }}
    .status-n {{ transform-box: view-box; transform-origin: 36px 335px; }}
    @media (max-width: 560px) {{
      .caps {{ font-size: 30px; letter-spacing: 1px; }}
      .status-n {{ transform: scale(1.9); }}
      .ticker {{ animation-name: ticker-n; }}
    }}
"""
    write("hero", W, H, "Josh Perry",
          "Josh Perry. Software engineer, Bangkok. " + " ".join(f"{k}: {v}." for k, v in ODO)
          + f" Usually built with {', '.join(TICKER)}.",
          body, lambda t: base_css(t, extra), (disp, sans, light))


# ---------------------------------------------------------------- index
ROWS = [
    ("About", [("Full-stack developer. I like systems that scale and hold up under pressure, and I sweat "
                "the details, from the database schema to the last bit of motion. British and Thai, based in Bangkok.", "ink"),
               ("Once played ice hockey for Thailand’s U20 squad, which still surprises people. "
                "These days I write music and take apart things that were working fine.", "grey")]),
    ("Now", [("Software engineer at Balerion, building the systems that keep businesses moving.", "ink"),
             ("Side quest: an e-commerce tool that shows shops their real profit, and how to grow it safely.", "grey")]),
    ("Usually built with", [("Go, TypeScript, React, Next.js, TanStack, PostgreSQL, Redis, GCP, Docker.", "ink")]),
]


def wrap(face, text, size, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and face.width(trial, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    if len(lines) > 1 and len(lines[-1].split()) == 1:  # no single-word last line
        head, moved = lines[-2].rsplit(" ", 1)
        lines[-2:] = [head, f"{moved} {lines[-1]}"]
    return lines


def build_index(variant):
    _, sans, light = faces()
    if variant == "wide":
        W, label_w, size, lh, label_size = 880, 300, 22, 34, 13
    else:
        W, label_w, size, lh, label_size = 480, 0, 21, 31, 14
    max_w = W - label_w

    # Each line sits in its own clip and rises out of it, a beat after the line above.
    rows, clips, y, n = [], [], 0.5, 0
    for i, (label, paras) in enumerate(ROWS):
        top, t0 = y, 0.25 + i * 0.18
        rows.append(f'  <line class="rule draw from-left" x1="0" y1="{top:.1f}" x2="{W}" y2="{top:.1f}"{delay(0.05 + i * 0.12)}/>')
        label_y = top + 44
        num = sans.use(f"{i + 1:02d}")
        rows.append(f'  <text class="caps fade" x="0" y="{label_y:.1f}" font-size="{label_size}" letter-spacing="0.4"{delay(t0)}>'
                    f'<tspan style="fill:{{INK}}">{num}</tspan>&#160;&#160;&#160;{sans.use(label)}</text>')
        ty = label_y if variant == "wide" else label_y + 40
        k = 0
        for pi, (text, tone) in enumerate(paras):
            if pi:
                ty += 14
            for line in wrap(light, text, size, max_w):
                cls = "body grey rise" if tone == "grey" else "body rise"
                clips.append(f'<clipPath id="l{n}"><rect x="{label_w}" y="{ty - size * 1.05:.1f}" width="{max_w}" height="{lh:.1f}"/></clipPath>')
                rows.append(f'  <g clip-path="url(#l{n})"><text class="{cls}" x="{label_w}" y="{ty:.1f}" font-size="{size}"'
                            f'{delay(t0 + 0.05 + k * 0.07)}>{light.use(line)}</text></g>')
                ty += lh
                k += 1
                n += 1
        y = ty - lh + 44
    rows.append(f'  <line class="rule draw from-left" x1="0" y1="{y:.1f}" x2="{W}" y2="{y:.1f}"{delay(0.05 + len(ROWS) * 0.12)}/>')
    rows.insert(0, "  <defs>" + "".join(clips) + "</defs>")
    H = int(y + 2)

    desc = " ".join(f"{label}: " + " ".join(t for t, _ in paras) for label, paras in ROWS)
    suffix = "" if variant == "wide" else "-narrow"
    write(f"index{suffix}", W, H, "About Josh Perry", desc, lambda t: "\n".join(rows).replace("{INK}", t["ink"]),
          lambda t: base_css(t), (sans, light))


# ---------------------------------------------------------------- links
# Icons are drawn at 16px. The X mark is X's published glyph in plain ink, as its brand rules
# allow. LinkedIn asks that its logo not be redrawn, so that button uses a generic briefcase.
ICONS = {
    "linkedin": lambda c: (f'<g fill="none" stroke="{c}" stroke-width="1.2" stroke-linejoin="round">'
                           f'<rect x="0.6" y="4.1" width="14.8" height="10.3" rx="1.6"/>'
                           f'<path d="M5.2 4.1V2.6a1 1 0 0 1 1-1h3.6a1 1 0 0 1 1 1v1.5M0.6 8.6h14.8"/></g>'),
    "x": lambda c: (f'<g transform="scale(0.6667)"><path fill="{c}" d="M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406'
                    f'l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z"/></g>'),
    "email": lambda c: (f'<g fill="none" stroke="{c}" stroke-width="1.2" stroke-linejoin="round">'
                        f'<rect x="0.6" y="2.6" width="14.8" height="10.8" rx="1.6"/>'
                        f'<path d="M1 3.4l7 5.4 7-5.4"/></g>'),
}
LINKS = [("linkedin", "LinkedIn"), ("x", "X"), ("email", "Email")]


def build_links():
    for slug, label in LINKS:
        _, sans, _ = faces()
        size, h, pad = 12, 40, 16
        tw = sans.width(sans.use(label.upper()), size, 0.8 / size)
        tx = pad + 16 + 10
        ax = tx + tw + 10
        w = int(ax + 7 + pad)

        def body(t, label=label, slug=slug, ax=ax, tx=tx, w=w):
            return f"""  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="3" fill="none" stroke="{t['grey']}" stroke-opacity="0.55"/>
  <g transform="translate({pad} 12)">{ICONS[slug](t['ink'])}</g>
  <text class="caps" x="{tx}" y="24.5" font-size="{size}" letter-spacing="0.8" style="fill:{t['ink']}">{label}</text>
  <path d="M{ax:.1f} 23.5 L{ax + 7:.1f} 16.5 M{ax + 1.5:.1f} 16.5 H{ax + 7:.1f} V22" stroke="{t['grey']}" stroke-width="1.1" fill="none"/>"""

        write(f"link-{slug}", w, h, label, f"{label}, opens in a new page", body, lambda t: base_css(t), (sans,))


def build_signoff():
    disp, _, _ = faces()
    text = disp.use("Devil’s in the details.")
    w = int(disp.width(text, 24) + 8)

    def body(t):
        return f'  <text class="disp fade" x="2" y="26" font-size="24" style="fill:{t["grey"]};animation-delay:.4s">{text}</text>'

    write("signoff", w, 36, "Devil’s in the details.", "Devil’s in the details.", body, lambda t: base_css(t), (disp,))


if __name__ == "__main__":
    build_hero()
    build_index("wide")
    build_index("narrow")
    build_links()
    build_signoff()
    print("built", sorted(p.name for p in HERE.glob("*.svg")))

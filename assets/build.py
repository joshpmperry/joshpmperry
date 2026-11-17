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

# Three colours per theme: ink, a quiet grey, and the page itself (left transparent).
THEMES = {
    "light": dict(ink="#1D1D1B", grey="#8E8E8C"),
    "dark": dict(ink="#F2F2F0", grey="#8A8A88"),
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

    /* Each keyframe names only its starting point: the resting state is the plain, visible one,
       so a renderer that skips CSS animation still shows everything in place. */
    @media (prefers-reduced-motion: no-preference) {{
      .rise {{ animation: rise 1s {EASE_OUT} both; }}
      .draw {{ animation: draw 1.1s {EASE_IN_OUT} both; }}
      .fade {{ animation: fade 0.8s {EASE_OUT} both; }}
      .lift {{ animation: lift 0.8s {EASE_OUT} both; }}
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
def build_hero():
    disp, sans, light = faces()
    W, H, SIZE = 880, 268, 132
    words = ["Josh", "Perry"]
    space = disp.width(" ", SIZE)
    xs, x = [], 0.0
    for wd in words:
        xs.append(x)
        x += disp.width(disp.use(wd), SIZE) + space
    role, city = sans.use("Software Engineer"), sans.use("Bangkok")

    def body(t):
        word_svg = "\n".join(
            f'    <g class="rise"{delay(0.1 + i * 0.09)}><text class="disp" x="{xs[i] - 6:.1f}" y="152" '
            f'font-size="{SIZE}" letter-spacing="-3">{wd}</text></g>'
            for i, wd in enumerate(words))
        return f"""  <defs><clipPath id="name"><rect x="0" y="0" width="{W}" height="190"/></clipPath></defs>
  <g clip-path="url(#name)">
{word_svg}
  </g>
  <line class="rule draw from-left" x1="0" y1="214.5" x2="{W}" y2="214.5"{delay(0.45)}/>
  <g class="fade"{delay(0.85)}>
    <text class="caps" x="0" y="252" font-size="13" letter-spacing="0.4">{role}</text>
    <text class="caps" x="{W}" y="252" font-size="13" letter-spacing="0.4" text-anchor="end">{city}</text>
  </g>"""

    narrow = "    @media (max-width: 560px) { .caps { font-size: 30px; letter-spacing: 0.6px; } }\n"
    write("hero", W, H, "Josh Perry", "Josh Perry. Software engineer, Bangkok.", body,
          lambda t: base_css(t, narrow), (disp, sans))


# ---------------------------------------------------------------- index
ROWS = [
    ("About", [("I build software that solves real problems, with an eye for the details people feel: "
                "clean interfaces and motion that's there on purpose.", "ink"),
               ("British and Thai. Off the clock: music, ice hockey, taking things apart.", "grey")]),
    ("Now", [("Building something to make the web easier to search.", "ink")]),
    ("Stack", [("Go, TypeScript, React, Next.js, PostgreSQL, Redis, GCP, Docker.", "ink")]),
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

    rows, y, i = [], 0.5, 0
    for label, paras in ROWS:
        top = y
        items = [f'  <line class="rule draw from-left" x1="0" y1="{top:.1f}" x2="{W}" y2="{top:.1f}"{delay(0.05 + i * 0.08)}/>']
        label_y = top + 44
        items.append(f'    <text class="caps" x="0" y="{label_y:.1f}" font-size="{label_size}" letter-spacing="0.4">{sans.use(label)}</text>')
        ty = label_y if variant == "wide" else label_y + 40
        for pi, (text, tone) in enumerate(paras):
            if pi:
                ty += 14
            for line in wrap(light, text, size, max_w):
                cls = "body grey" if tone == "grey" else "body"
                items.append(f'    <text class="{cls}" x="{label_w}" y="{ty:.1f}" font-size="{size}">{light.use(line)}</text>')
                ty += lh
        y = ty - lh + 44
        rows.append(items[0] + f'\n  <g class="lift"{delay(0.2 + i * 0.08)}>\n' + "\n".join(items[1:]) + "\n  </g>")
        i += 1
    rows.append(f'  <line class="rule draw from-left" x1="0" y1="{y:.1f}" x2="{W}" y2="{y:.1f}"{delay(0.05 + i * 0.08)}/>')
    H = int(y + 2)

    desc = " ".join(f"{label}: " + " ".join(t for t, _ in paras) for label, paras in ROWS)
    suffix = "" if variant == "wide" else "-narrow"
    write(f"index{suffix}", W, H, "About Josh Perry", desc, lambda t: "\n".join(rows),
          lambda t: base_css(t), (sans, light))


# ---------------------------------------------------------------- links
LINKS = ["LinkedIn", "X", "Email"]


def build_links():
    for label in LINKS:
        _, sans, _ = faces()
        size, h = 13, 24
        tw = sans.width(sans.use(label.upper()), size, 0.4 / size)
        w = int(tw + 22)
        ax = tw + 9

        def body(t, label=label, ax=ax):
            return f"""  <text class="caps" x="0" y="17" font-size="{size}" letter-spacing="0.4" style="fill:{t['ink']}">{label}</text>
  <path d="M{ax:.1f} 15.5 L{ax + 7:.1f} 8.5 M{ax + 1.5:.1f} 8.5 H{ax + 7:.1f} V14" stroke="{t['ink']}" stroke-width="1.1" fill="none"/>"""

        write(f"link-{label.lower()}", w, h, label, f"{label}, opens in a new page", body,
              lambda t: base_css(t), (sans,))


if __name__ == "__main__":
    build_hero()
    build_index("wide")
    build_index("narrow")
    build_links()
    print("built", sorted(p.name for p in HERE.glob("*.svg")))

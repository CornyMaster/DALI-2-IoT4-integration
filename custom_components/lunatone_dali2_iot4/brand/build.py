import io, resvg_py
from PIL import Image

def tmpl(fg):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512" role="img" aria-label="Lunatone DALI-2">
  <defs><mask id="moon"><rect width="512" height="512" fill="black"/>
    <circle cx="452" cy="224" r="34" fill="white"/><circle cx="430" cy="236" r="27" fill="black"/></mask></defs>
  <text x="214" y="322" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-weight="900" font-size="158" letter-spacing="-2" fill="{fg}">DALI</text>
  <g mask="url(#moon)"><rect width="512" height="512" fill="{fg}"/></g>
  <text x="430" y="252" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-weight="800" font-size="50" fill="{fg}">2</text>
</svg>'''

out = "custom_components/lunatone_dali2_iot4/brand"
variants = {"icon": "#111111", "dark_icon": "#FFFFFF", "logo": "#111111", "dark_logo": "#FFFFFF"}
for name, fg in variants.items():
    big = Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=tmpl(fg))))).convert("RGBA")
    big.save(f"{out}/{name}@2x.png")
    big.resize((256, 256), Image.LANCZOS).save(f"{out}/{name}.png")
open(f"{out}/icon.svg", "w", encoding="utf-8").write(tmpl("#111111"))
print("ok")

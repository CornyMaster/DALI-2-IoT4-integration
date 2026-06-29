import resvg_py
svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512" role="img" aria-label="Lunatone DALI-2">
  <defs>
    <mask id="moon">
      <rect width="512" height="512" fill="black"/>
      <circle cx="452" cy="224" r="34" fill="white"/>
      <circle cx="430" cy="236" r="27" fill="black"/>
    </mask>
  </defs>
  <rect width="512" height="512" fill="#111111"/>
  <text x="214" y="322" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-weight="900" font-size="158" letter-spacing="-2" fill="#FFFFFF">DALI</text>
  <g mask="url(#moon)"><rect width="512" height="512" fill="#FFFFFF"/></g>
  <text x="430" y="252" text-anchor="middle" font-family="Arial, Helvetica, sans-serif"
        font-weight="800" font-size="50" fill="#FFFFFF">2</text>
</svg>'''
open('brand/icon.svg', 'w', encoding='utf-8').write(svg)
png = bytes(resvg_py.svg_to_bytes(svg_string=svg))
open('brand/icon@2x.png', 'wb').write(png)
from PIL import Image
import io
im = Image.open(io.BytesIO(png)).convert('RGBA')          # 512x512
im.save('brand/icon@2x.png')
im.resize((256, 256), Image.LANCZOS).save('brand/icon.png')
print('ok', im.size)

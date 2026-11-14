"""Make the deployed acceptance screenshots easy to inspect as one local artifact."""
import html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/e2e'
shots=sorted(p for p in OUT.glob('*.png') if re.fullmatch(r'(1440|390)-\d\d[a-z]?-[a-z-]+\.png',p.name))
content='<!doctype html><html><meta charset="utf-8"><title>Tieto deployed acceptance</title><style>body{margin:32px;background:#FAFAF7;color:#3A1D4D;font:16px system-ui}section{margin:32px 0}img{display:block;max-width:100%;height:auto;border:1px solid #E4E1E8}a{color:inherit}h2{font-size:18px}</style><h1>Tieto deployed acceptance</h1><p>Headless Chromium, real production URL, real user actions. Desktop and mobile receipts are saved alongside these screenshots.</p>'
for p in shots:content+='<section><h2>'+html.escape(p.stem)+'</h2><a href="'+p.name+'"><img loading="lazy" src="'+p.name+'" alt="'+html.escape(p.stem)+'"></a></section>'
(OUT/'index.html').write_text(content+'</html>');print('Screenshots indexed:',len(shots))

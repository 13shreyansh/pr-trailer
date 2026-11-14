"""Pin AIDev source snapshots for repeatable local removal trials."""
import io
import json
from pathlib import Path
import tarfile
import urllib.request
ROOT=Path(__file__).resolve().parents[2]
for n in (9,24):
 root=ROOT / f'evidence/source/reduino-{n}'
 pr=json.loads((root/'provenance.json').read_text())['pr']
 for kind in ('base','head'):
  target=root/kind
  if target.exists(): continue
  target.mkdir()
  sha=pr[kind]['sha']
  raw=urllib.request.urlopen(f'https://codeload.github.com/Jackhammer9/Reduino/tar.gz/{sha}',timeout=45).read()
  (root/(kind+'.tar.gz')).write_bytes(raw)
  with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
   for member in tar:
    parts=Path(member.name).parts[1:]
    if not parts or member.issym() or member.islnk(): continue
    rel=Path(*parts)
    if '..' in rel.parts: raise ValueError('unsafe path')
    dest=target/rel
    if member.isdir(): dest.mkdir(parents=True,exist_ok=True)
    elif member.isfile():
     dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(member).read())
 print(n,pr['title'])

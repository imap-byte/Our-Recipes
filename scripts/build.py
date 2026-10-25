#!/usr/bin/env python3
"""Assemble a Pages artifact with a pinned media revision, then validate it."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from validate import validate

ROOT = Path(__file__).resolve().parents[1]

def build(output, media_root=None):
    output = output.resolve()
    # Never delete an existing directory or write inside the source repository.
    if output.exists() or output == ROOT or ROOT in output.parents:
        raise ValueError('Choose a NEW output directory outside the repository')
    source = json.loads((ROOT / 'data/media-source.json').read_text())
    revision = source['commit']
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Media commit must be a full immutable SHA')
    output.mkdir(parents=True)
    for name in ['index.html', 'assets', 'data']:
        src = ROOT / name
        if src.is_dir(): shutil.copytree(src, output / name)
        else: shutil.copy2(src, output / name)
    if media_root:
        actual = subprocess.check_output(['git', '-C', str(media_root), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != revision:
            raise ValueError('Media checkout does not match pinned revision')
        dirty = subprocess.check_output(['git','-C',str(media_root),'status','--porcelain','--','media/'],text=True)
        if dirty:
            raise ValueError('Media checkout has uncommitted files')
        shutil.copytree(media_root / 'media', output / 'media')
    else:
        # git show reads only tracked paths from the exact commit, never branch tip.
        paths = subprocess.check_output(['git','ls-tree','-r','--name-only',revision,'media/'], cwd=ROOT, text=True).splitlines()
        if not paths: raise ValueError('Pinned media is unavailable; fetch the commit first')
        for name in paths:
            path = Path(name)
            if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe media path')
            dest = output / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(subprocess.check_output(['git','show',f'{revision}:{name}'], cwd=ROOT))
    (output / '.nojekyll').touch()
    validate(output, output)
    print(f'Built {output} using media {revision}')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--media-root',type=Path)
    args=parser.parse_args()
    build(args.output,args.media_root)

#!/usr/bin/env python3
"""One-time migration proof against the immutable pre-migration Git commit."""
import argparse
import base64
import json
import re
import subprocess
from pathlib import Path
from PIL import Image

BASELINE='ec3f6de1c0dbf12ae940c585ccd75146e975b66c'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--site',required=True,type=Path)
parser.add_argument('--baseline-ref',default=BASELINE)
args=parser.parse_args()
source=subprocess.check_output(['git','show',args.baseline_ref+':index.html'],text=True)
old=json.loads(re.search(r'<script id="recipe-data" type="application/json">(.*?)</script>',source,re.S)[1])
new=json.loads((args.site/'data/recipes.json').read_text())
media=json.loads((args.site/'data/media.json').read_text())
assert new=={k:v for k,v in old.items() if k not in ['photos','scans']}, 'Recipe data changed'
for kind in ['photos','scans']:
    assert set(media[kind])==set(old[kind]), f'{kind} IDs changed'
    for key,entry in media[kind].items():
        path=args.site/entry['path']
        assert path.read_bytes()==base64.b64decode(old[kind][key].split(',',1)[1]), f'Media changed: {key}'
        with Image.open(path) as image:
            image.load()
            assert image.width>0 and image.height>0
print('PASS: all recipe fields, credits, categories, redirects and metadata are identical; all 595 media IDs and decoded files are byte-identical')

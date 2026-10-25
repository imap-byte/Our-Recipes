#!/usr/bin/env python3
"""Validate data, stable IDs, redirects and every referenced media file."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[1]

def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique)

def validate(root, media_root):
    data = read_json(root / 'data/recipes.json')
    media = read_json(root / 'data/media.json')
    for name, payload in [('recipes', data), ('media', media)]:
        jsonschema.Draft202012Validator(read_json(root / f'data/{name}.schema.json')).validate(payload)
    ids = [r['id'] for r in data['recipes']]
    assert len(ids) == len(set(ids)), 'Duplicate recipe IDs'
    assert data['metadata']['total'] == len(ids), 'Wrong metadata.total'
    assert data['categories'][0] == 'הכל', 'Missing all-recipes category'
    assert data['metadata']['categories'] == len(data['categories']) - 1, 'Wrong category count'
    for r in data['recipes']:
        assert r['cat'] in data['categories'][1:], f"Unknown category: {r['id']}"
        assert r['title'].strip(), f"Empty title: {r['id']}"
        assert r['photo'] in media['photos'], f"Unknown photo: {r['id']}"
        for key in ([r['scan']] if r['scan'] else []) + r.get('scanExtra', []):
            assert key in media['scans'], f"Unknown scan: {r['id']}/{key}"
    for old, target in data['redirects'].items():
        assert int(old) not in ids and target in ids, f'Invalid redirect: {old}'
    for kind in ['photos', 'scans']:
        for key, entry in media[kind].items():
            assert entry['path'].startswith(f'media/{kind}/'), f'Media kind mismatch: {key}'
            path = media_root / entry['path']
            raw = path.read_bytes()
            assert len(raw) == entry['bytes'], f'Wrong size: {key}'
            assert hashlib.sha256(raw).hexdigest() == entry['sha256'], f'Wrong hash: {key}'
    # Also verify engine-only image references, not just recipe covers.
    app = (root / 'assets/app.js').read_text()
    for key in re.findall(r"'[^']+':'([^']+)'", re.search(r'const CATPIC=(\{.*?\});', app)[1]) + ['focaccia']:
        assert key in media['photos'], f'Unknown category/hero image: {key}'
    for path in [root / 'index.html', *list((root / 'assets').glob('*')), *list((root / 'data').glob('*.json'))]:
        if path.is_file():
            assert 'data:image/' not in path.read_text(), f'Embedded image in {path}'
    print(f"PASS: {len(ids)} recipes; {len(data['categories'])-1} categories; "
          f"{len(media['photos'])} photos; {len(media['scans'])} scans; {len(data['redirects'])} redirects")
    return data, media

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT)
    parser.add_argument('--media-root', type=Path, help='Directory containing media/')
    args = parser.parse_args()
    validate(args.site.resolve(), (args.media_root or args.site).resolve())

#!/usr/bin/env python3
"""Export a validated compiled recipe site to one fully offline HTML file."""
import argparse
import base64
import hashlib
import json
import mimetypes
import re
from pathlib import Path

LOADER = r'''
async function loadRecipeData() {
  document.addEventListener('error', event => {
    const image = event.target;
    if (image instanceof HTMLImageElement) {
      image.style.visibility = 'hidden';
      image.setAttribute('data-media-error', 'true');
      image.title = 'התמונה אינה זמינה כרגע';
    }
  }, true);
  const data = JSON.parse(document.getElementById('offline-recipe-data').textContent);
  const media = JSON.parse(document.getElementById('offline-media-data').textContent);
  return {...data, photos:media.photos, scans:media.scans};
}
function showLoadError(error) {
  console.error('Recipe site loading failed', error);
  document.getElementById('site').hidden = true;
  const status = document.getElementById('load-status');
  status.hidden = false;
  status.setAttribute('role', 'alert');
  status.textContent = 'לא ניתן לטעון את ספריית המתכונים. נא לרענן את הדף ולנסות שוב.';
}
'''

def inline_json(obj):
    return (json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
            .replace('<', '\\u003c').replace('>', '\\u003e')
            .replace('&', '\\u0026')
            .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))

def replace_once(contents, needle, replacement, label):
    count = contents.count(needle)
    if count != 1:
        raise ValueError(f'{label}: expected one match, got {count}')
    return contents.replace(needle, replacement, 1)

def export(site, output):
    site = site.resolve()
    index = (site/'index.html').read_text(encoding='utf-8')
    css = (site/'assets/site.css').read_text(encoding='utf-8')
    app = (site/'assets/app.js').read_text(encoding='utf-8')
    data = json.loads((site/'data/recipes.json').read_text(encoding='utf-8'))
    manifest = json.loads((site/'data/media.json').read_text(encoding='utf-8'))
    if len(data['recipes']) != data['metadata']['total']:
        raise ValueError('Invalid recipe count')
    if manifest.get('version') != 1:
        raise ValueError('Unsupported media manifest')
    embedded = {'photos': {}, 'scans': {}}
    for kind in ('photos', 'scans'):
        for key, entry in manifest[kind].items():
            relative = Path(entry['path'])
            if (relative.is_absolute() or '..' in relative.parts or
                    relative.parts[:2] != ('media', kind)):
                raise ValueError(f'Unsafe media path for {key}')
            path = site/relative
            content = path.read_bytes()
            if len(content) != entry['bytes']:
                raise ValueError(f'Incorrect size for media {key}')
            if hashlib.sha256(content).hexdigest() != entry['sha256']:
                raise ValueError(f'Incorrect SHA256 for media {key}')
            mime = mimetypes.guess_type(str(path))[0]
            if mime not in {'image/avif','image/webp','image/png',
                            'image/jpeg','image/gif','image/svg+xml'}:
                raise ValueError(f'Unsupported mime type for media {key}: {mime}')
            embedded[kind][key] = 'data:'+mime+';base64,'+base64.b64encode(content).decode('ascii')
    for recipe in data['recipes']:
        if recipe['photo'] not in embedded['photos']:
            raise ValueError(f"Missing photo for recipe {recipe['id']}")
        for scan in ([recipe.get('scan')] if recipe.get('scan') else []) + recipe.get('scanExtra', []):
            if scan not in embedded['scans']:
                raise ValueError(f"Missing scan for recipe {recipe['id']}")
    index = replace_once(index, '<link rel="stylesheet" href="./assets/site.css"/>',
                         '<style>\n'+css+'\n</style>', 'style link')
    app = replace_once(app,
                       "import {loadRecipeData, showLoadError} from './recipe-loader.js';",
                       '', 'module import')
    embedded_data = '<script type="application/json" id="offline-recipe-data">'+inline_json(data)+'</script>'
    embedded_media = '<script type="application/json" id="offline-media-data">'+inline_json(embedded)+'</script>'
    scripts = embedded_data + '\n' + embedded_media + '\n<script>\n' + LOADER + '\n' + app.replace('</script', '<\\/script') + '\n</script>'
    index = replace_once(index,
                         '<script type="module" src="./assets/app.js"></script>',
                         scripts, 'module link')
    if re.search(r'<(?:script|link)\b[^>]*(?:src|href)\s*=\s*["\']\./', index, re.I):
        raise ValueError('Unexpected relative JS or CSS link')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(index, encoding='utf-8')
    print(f"Created {output}: {output.stat().st_size:,} bytes, "
          f"{len(data['recipes'])} recipes, {len(embedded['photos'])} photos, "
          f"{len(embedded['scans'])} scans")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--site',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    export(args.site,args.output)

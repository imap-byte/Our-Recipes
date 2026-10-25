#!/usr/bin/env python3
"""Negative tests for the release validator: corrupt input must fail closed."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate import validate

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'site'
        shutil.copytree(SITE,self.root)
    def tearDown(self):self.temp.cleanup()
    def edit(self,name,fn):
        p=self.root/'data'/name;d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d))
    def rejected(self):
        with self.assertRaises(Exception),contextlib.redirect_stdout(io.StringIO()):validate(self.root,self.root)
    def test_schema(self):
        self.edit('recipes.json',lambda d:d['recipes'][0].update(ingredients='invalid'));self.rejected()
    def test_duplicate_id(self):
        self.edit('recipes.json',lambda d:d['recipes'][1].update(id=d['recipes'][0]['id']));self.rejected()
    def test_unknown_photo(self):
        self.edit('recipes.json',lambda d:d['recipes'][0].update(photo='missing'));self.rejected()
    def test_unknown_scan(self):
        self.edit('recipes.json',lambda d:d['recipes'][0].update(scanExtra=['missing']));self.rejected()
    def test_invalid_redirect(self):
        self.edit('recipes.json',lambda d:d['redirects'].update({'99999':99998}));self.rejected()
    def test_media_corruption(self):
        media=json.loads((self.root/'data/media.json').read_text());p=self.root/next(iter(media['photos'].values()))['path'];p.write_bytes(b'corrupt');self.rejected()
    def test_duplicate_json_key(self):
        p=self.root/'data/recipes.json';p.write_text(p.read_text().replace('"recipes":','"recipes": [], "recipes":',1));self.rejected()
    def test_wrong_total(self):
        self.edit('recipes.json',lambda d:d['metadata'].update(total=1));self.rejected()
    def test_unsafe_path(self):
        self.edit('media.json',lambda d:next(iter(d['photos'].values())).update(path='../wrong.avif'));self.rejected()

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--site',required=True,type=Path);args=parser.parse_args();SITE=args.site
    unittest.main(argv=[sys.argv[0]])

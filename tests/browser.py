#!/usr/bin/env python3
"""Exercise the assembled site under a GitHub Pages project subpath."""
import argparse
import functools
import json
import re
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from playwright.sync_api import sync_playwright

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = unquote(urlsplit(path).path)
        if path.startswith('/Our-Recipes/'):
            return str(self.site / path[len('/Our-Recipes/'):])
        if self.baseline and path.startswith('/baseline/'):
            return str(self.baseline / path[len('/baseline/'):])
        return '/nonexistent'
    def log_message(self, *args): pass

def ready(page, url):
    page.goto(url, wait_until='networkidle')
    page.wait_for_function("document.querySelectorAll('#recipes article').length === 48")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', required=True, type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--screenshots', type=Path)
    args=parser.parse_args()
    Handler.site=args.site.resolve(); Handler.baseline=args.baseline.resolve() if args.baseline else None
    data=json.loads((args.site/'data/recipes.json').read_text())
    media=json.loads((args.site/'data/media.json').read_text())
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    base=origin+'/Our-Recipes/'
    with sync_playwright() as p:
        launch={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
        if shutil.which('chromium'): launch['executable_path']=shutil.which('chromium')
        browser=p.chromium.launch(**launch)
        page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        ready(page,base)
        assert page.locator('#hero-count').inner_text()==str(len(data['recipes']))
        assert page.locator('#hero-categories').inner_text()==str(len(data['categories'])-1)
        assert page.locator('#category-cards button').count()==len(data['categories'])-1
        assert page.locator('#sidebar-nav .navcount').first.inner_text()==str(len(data['recipes']))
        print('PASS project subpath, initial count and categories')
        if args.screenshots:
            from PIL import Image,ImageChops
            args.screenshots.mkdir(parents=True,exist_ok=True)
            for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
                page.set_viewport_size({'width':width,'height':height})
                for label,url in [('before',origin+'/baseline/'),('after',base)]:
                    ready(page,url)
                    page.evaluate('Promise.all(Array.from(document.images, i => i.decode().catch(() => {})))')
                    page.screenshot(path=str(args.screenshots/f'{name}-{label}.png'))
                a=Image.open(args.screenshots/f'{name}-before.png').convert('RGB')
                b=Image.open(args.screenshots/f'{name}-after.png').convert('RGB')
                diff=ImageChops.difference(a,b)
                changed=sum(pixel != (0,0,0) for pixel in diff.get_flattened_data())
                peak=max(maximum for minimum,maximum in diff.getextrema())
                # Rounded image edges may differ by 1-2 levels after external decode.
                assert peak<=2 and changed/(a.width*a.height)<0.001, f'{name} visual regression: {diff.getbbox()}, peak={peak}, pixels={changed}'
                print(f'PASS baseline screenshot: {name}; changed pixels={changed}; maximum channel delta={peak}')
            page.set_viewport_size({'width':1440,'height':1000})
            ready(page,base)
        # Load all cards; assert each stable ID resolves to its own manifest path.
        while page.locator('#more').is_visible(): page.locator('#loadmore').click()
        assert page.locator('#recipes article').count()==len(data['recipes'])
        page.wait_for_function("Array.from(document.querySelectorAll('#recipes img')).every(i=>i.complete && i.naturalWidth>0)")
        cards=page.locator('#recipes article').evaluate_all("els=>els.map(e=>({id:Number(e.querySelector('[data-open]').dataset.open),src:e.querySelector('img').getAttribute('src')}))")
        byid={r['id']:r for r in data['recipes']}
        for card in cards: assert card['src']==base+media['photos'][byid[card['id']]['photo']]['path']
        print('PASS all 421 cards and cover images, exact ID-to-media mapping')
        # Every category, including scroll target.
        for category in data['categories'][1:]:
            button=page.locator('#sidebar-nav [data-cat]').filter(has_text=category).first
            button.click()
            expected=sum(r['cat']==category for r in data['recipes'])
            assert page.locator('#display-progress').inner_text()==f'מוצגים {min(48,expected)} מתוך {expected} מתכונים'
            page.wait_for_timeout(350)
            assert page.evaluate('window.scrollY')>0
            assert page.locator('#search-scroll-anchor').evaluate('(e)=>e.getBoundingClientRect().top')<page.viewport_size['height']
        print('PASS all 11 category filters and scroll target')
        page.locator('#sidebar-nav [data-cat="דגים"]').click()
        page.locator('[data-fish="סלמון"]').click()
        assert all('סלמון' in t for t in page.locator('#recipes .rtitle').all_inner_texts())
        # Surprise must select a recipe within the current fish filter.
        allowed=page.locator('#recipes .coverbtn').evaluate_all('els=>els.map(e=>Number(e.dataset.open))')
        page.locator('#surprise-floating').click()
        assert int(page.url.rsplit('-',1)[1]) in allowed
        page.locator('#close-dialog').click()
        page.locator('#clear').click()
        first=data['recipes'][0]
        page.locator('#search').fill(first['title'])
        assert page.locator(f'.coverbtn[data-open="{first["id"]}"]').count()==1
        page.locator('#search').fill('zzzz_no_recipe_12345')
        assert page.locator('#empty').is_visible()
        page.locator('#clear-empty').click()
        assert page.locator('#recipes article').count()==48
        page.locator('#search').fill(first['author'])
        assert page.locator(f'.coverbtn[data-open="{first["id"]}"]').count()==1
        page.locator('#clear').click()
        page.locator('#year').select_option('2023')
        assert all('2023' in t for t in page.locator('#recipes .rmeta').all_inner_texts())
        page.locator('#clear').click()
        page.locator('#sort').select_option('new')
        expected=sorted(data['recipes'],key=lambda r:(-r['year'],-r['id']))[0]['id']
        assert page.locator('.coverbtn').first.get_attribute('data-open')==str(expected)
        page.locator('#clear').click()
        page.locator('#recipes [data-fav]').first.click()
        page.locator('#fav-top').click()
        assert page.locator('#recipes article').count()==1
        page.reload(wait_until='networkidle')
        page.locator('#fav-top').click()
        assert page.locator('#recipes article').count()==1
        page.locator('#fav-top').click()
        print('PASS search, empty reset, year, sorting, favorites persistence and filtered surprise')
        # Representative corrected image groups, scans and continuation pages.
        samples=[]
        for prefix in ['generated-top10-','generated-fixed-11-20-','generated-21-30-','generated-31-40-','generated-41-50-','generated-51-60-','photo-checked-','illustrated-']:
            samples.append(next(r for r in data['recipes'] if r['photo'].startswith(prefix)))
        scan_samples=[next((r for r in data['recipes'] if r['scan']),None),next((r for r in data['recipes'] if r.get('scanExtra')),None)]
        samples.extend(r for r in scan_samples if r is not None and r not in samples)
        for r in samples:
            page.goto(base+f'#recipe-{r["id"]}',wait_until='networkidle')
            assert page.get_by_role('dialog').is_visible()
            assert page.locator('.dialog h2').inner_text()==r['title']
            assert page.locator('.dhero img').get_attribute('src')==base+media['photos'][r['photo']]['path']
            assert page.locator('.dialog .creditbadge').inner_text().endswith(r['creditLabel'])
            scan_keys=([r['scan']] if r['scan'] else [])+r.get('scanExtra',[])
            assert page.locator('.scanpage').count()==len(scan_keys)
            for image,key in zip(page.locator('.scanpage').all(),scan_keys):
                assert image.get_attribute('src')==base+media['scans'][key]['path']
                assert image.evaluate('(i)=>i.complete && i.naturalWidth>0')
        # Preserve recipe actions and adjacent-recipe navigation.
        page.evaluate('window.__printed=false; window.print=()=>{window.__printed=true}')
        page.locator('#print-dialog').click()
        assert page.evaluate('window.__printed')
        assert page.locator('#printonly h1').inner_text()==samples[-1]['title']
        page.context.grant_permissions(['clipboard-read','clipboard-write'])
        page.locator('#copy-dialog').click()
        assert samples[-1]['title'] in page.evaluate('navigator.clipboard.readText()')
        page.locator('#recipe-next').click()
        assert page.locator('.dialog h2').inner_text()!=samples[-1]['title']
        page.locator('#recipe-prev').click()
        assert page.locator('.dialog h2').inner_text()==samples[-1]['title']
        print('PASS print, copy and previous/next navigation')
        print('PASS representative corrected photo groups and original scans; sample IDs:',[r['id'] for r in samples])
        for old,target in data['redirects'].items():
            page.goto(base+f'#recipe-{old}',wait_until='networkidle')
            assert page.locator('.dialog h2').inner_text()==byid[target]['title']
        page.keyboard.press('Escape'); assert page.get_by_role('dialog').count()==0
        page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
        page.wait_for_function('Math.abs(window.scrollY - (document.documentElement.scrollHeight-window.innerHeight)) < 2')
        page.locator('#back-to-top').click()
        page.wait_for_function('window.scrollY === 0')
        print('PASS all 20 legacy redirects, dialog Escape and back-to-top')
        assert errors==[],errors
        # Failed data files and corrupt references must not expose a partial library.
        cases=[('data/recipes.json',None),('data/media.json',None),('data/recipes.json',{**data,'metadata':{**data['metadata'],'total':2},'recipes':[data['recipes'][0],data['recipes'][0]]}),('data/recipes.json',{**data,'metadata':{**data['metadata'],'total':1},'recipes':[{**data['recipes'][0],'photo':'missing-id'}]})]
        for path,payload in cases:
            bad=browser.new_page()
            if payload is None:bad.route('**/'+path,lambda route:route.fulfill(status=503,body='Unavailable'))
            else:bad.route('**/'+path,lambda route,request,payload=payload:route.fulfill(status=200,json=payload))
            bad.goto(base,wait_until='networkidle')
            assert bad.locator('#load-status[role="alert"]').is_visible()
            assert not bad.locator('#site').is_visible()
            assert bad.locator('#recipes article').count()==0
            bad.close()
        bad=browser.new_page(); broken=media['photos'][first['photo']]['path']
        bad.route('**/'+broken,lambda route:route.fulfill(status=404,body='Missing'))
        ready(bad,base)
        image=bad.locator(f'.coverbtn[data-open="{first["id"]}"] img')
        assert image.get_attribute('src')==base+broken
        assert image.get_attribute('data-media-error')=='true'
        assert image.evaluate('(i)=>getComputedStyle(i).visibility')=='hidden'
        assert bad.locator('#hero-count').inner_text()==str(len(data['recipes']))
        bad.close()
        print('PASS failed JSON, invalid IDs, broken mapping, missing image isolation; no substituted images')
        browser.close()
    server.shutdown()
    print('ALL BROWSER TESTS PASSED')

if __name__=='__main__':main()

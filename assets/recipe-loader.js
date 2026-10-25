// Resolve against this module, so /Our-Recipes/ and preview subpaths both work.
const siteBase = new URL('../', import.meta.url);
const requiredStrings = ['cat','title','mid','note','photo','author','creditKind','creditLabel','sourceSharer','sourceSharerKind','creditEvidence'];
const fail = message => { throw new Error(message); };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const strings = value => Array.isArray(value) && value.every(item => typeof item === 'string');

export function validateData(data, media) {
  if (!object(data) || !Array.isArray(data.recipes) || !data.recipes.length ||
      !strings(data.categories) || data.categories[0] !== 'הכל' ||
      new Set(data.categories).size !== data.categories.length || !object(data.metadata) ||
      data.metadata.total !== data.recipes.length || data.metadata.categories !== data.categories.length-1 || !object(data.redirects)) fail('Invalid recipe data');
  if (!object(media) || media.version !== 1) fail('Invalid media manifest');
  const maps = {};
  for (const kind of ['photos', 'scans']) {
    if (!object(media[kind])) fail('Missing media map: ' + kind);
    maps[kind] = Object.create(null);
    for (const [id, entry] of Object.entries(media[kind])) {
      if (!object(entry) || !/^[a-zA-Z0-9_-]+$/.test(id) ||
          typeof entry.path !== 'string' || !new RegExp('^media/' + kind + '/[a-zA-Z0-9_-]+\\.(avif|webp|png|jpg|jpeg|gif|svg)$').test(entry.path) ||
          !/^[a-f0-9]{64}$/.test(entry.sha256) || !Number.isSafeInteger(entry.bytes) || entry.bytes <= 0) fail('Invalid media entry: ' + id);
      maps[kind][id] = new URL(entry.path, siteBase).href;
    }
  }
  const ids = new Set();
  for (const r of data.recipes) {
    if (!object(r) || !Number.isSafeInteger(r.id) || r.id <= 0 || ids.has(r.id) ||
        !requiredStrings.every(key => typeof r[key] === 'string') || !r.title ||
        !Number.isSafeInteger(r.year) || !strings(r.ingredients) || !strings(r.steps) ||
        typeof r.new !== 'boolean' || typeof r.continuation !== 'boolean' ||
        !data.categories.slice(1).includes(r.cat) || !Object.hasOwn(maps.photos,r.photo) ||
        (r.scan !== null && (typeof r.scan !== 'string' || !Object.hasOwn(maps.scans,r.scan))) ||
        (r.scanExtra !== undefined && (!strings(r.scanExtra) || !r.scanExtra.every(key => Object.hasOwn(maps.scans,key)))) ||
        (r.aliases !== undefined && !strings(r.aliases))) fail('Invalid recipe or media reference: ' + r?.id);
    ids.add(r.id);
  }
  for (const [oldId, target] of Object.entries(data.redirects)) {
    if (!/^[1-9][0-9]*$/.test(oldId) || ids.has(Number(oldId)) || !ids.has(target)) fail('Invalid redirect: ' + oldId);
  }
  return {...data, ...maps};
}

async function readJSON(path) {
  const response = await fetch(new URL(path, siteBase), {cache:'no-cache'});
  if (!response.ok) fail(path + ': HTTP ' + response.status);
  return response.json();
}

export async function loadRecipeData() {
  // A failed image stays unavailable; never substitute another recipe's image.
  document.addEventListener('error', event => {
    const image = event.target;
    if (image instanceof HTMLImageElement) {
      image.style.visibility = 'hidden';
      image.setAttribute('data-media-error', 'true');
      image.title = 'התמונה אינה זמינה כרגע';
    }
  }, true);
  const [data, media] = await Promise.all([readJSON('data/recipes.json'), readJSON('data/media.json')]);
  return validateData(data, media);
}

export function showLoadError(error) {
  console.error('Recipe site loading failed', error);
  document.getElementById('site').hidden = true;
  const status = document.getElementById('load-status');
  status.hidden = false;
  status.setAttribute('role', 'alert');
  status.textContent = 'לא ניתן לטעון את ספריית המתכונים. נא לרענן את הדף ולנסות שוב.';
}

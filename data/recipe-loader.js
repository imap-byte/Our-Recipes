/* Recipe data bootstrap. Load this from the HTML after media bundles.
   Does not change the live site until integrated with index.html. */
(function () {
  'use strict';
  const dataUrl = new URL('recipes.json', document.currentScript.src);
  window.RECIPE_DATA_READY = fetch(dataUrl, { cache: 'no-cache' })
    .then(function (response) {
      if (!response.ok) throw new Error('Recipe data HTTP ' + response.status);
      return response.json();
    })
    .then(function (payload) {
      if (!payload || !Array.isArray(payload.recipes)) {
        throw new Error('Invalid recipes.json: recipes array missing');
      }
      window.RECIPE_DATA = payload;
      window.dispatchEvent(new CustomEvent('recipe-data-ready', {
        detail: { count: payload.recipes.length }
      }));
      return payload;
    })
    .catch(function (error) {
      console.error('Recipe data loading failed', error);
      window.dispatchEvent(new CustomEvent('recipe-data-error', {
        detail: { message: String(error.message || error) }
      }));
      throw error;
    });
})();

'use strict';
// Local assets keep the league selector usable when an external image host is down.
const leagueBrands = {
  PL: { file: 'PL.svg', country: 'EN' },
  PD: { file: 'PD.svg', country: 'ES' },
  SA: { file: 'SA.svg', country: 'IT' },
  BL1: { file: 'BL1.svg', country: 'DE' },
  FL1: { file: 'FL1.svg', country: 'FR' },
};

function leagueLogo(id) {
  const brand = leagueBrands[id];
  if (!brand) return '';
  // Adjacent league names provide the accessible label; the image is decorative.
  return `<img class="league-logo" src="assets/leagues/${brand.file}" alt="" width="36" height="36" data-country="${brand.country}">`;
}

document.addEventListener(
  'error',
  (event) => {
    const image = event.target;
    if (!(image instanceof HTMLImageElement) || !image.classList.contains('league-logo')) return;
    const fallback = document.createElement('span');
    fallback.className = 'league-fallback';
    fallback.textContent = image.dataset.country;
    fallback.setAttribute('aria-hidden', 'true');
    image.replaceWith(fallback);
  },
  true,
);

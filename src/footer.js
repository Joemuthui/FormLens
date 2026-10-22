/* FormLens site footer — the same centred footer on every page.
 * Fills any <footer class="site-footer"> on the page. Contact links come from
 * src/contact.js (window.FORMLENS_CONTACT); links left blank there are omitted.
 */
(function () {
  'use strict';

  function link(text, href, external) {
    const a = document.createElement('a');
    a.textContent = text;
    a.href = href;
    if (external) { a.target = '_blank'; a.rel = 'noopener'; }
    return a;
  }

  function render(footer) {
    const c = window.FORMLENS_CONTACT || {};
    footer.textContent = '';
    const inner = document.createElement('div');
    inner.className = 'sf-inner';

    const brand = document.createElement('div');
    brand.className = 'sf-brand';
    const name = document.createElement('span');
    name.className = 'sf-name';
    name.textContent = 'FormLens';
    brand.append(name, ' by A.M. Labs · The Gambia · © ' + new Date().getFullYear());
    inner.appendChild(brand);

    const links = [];
    if (c.email) links.push(link('Email', 'mailto:' + c.email, false));
    if (c.whatsapp) links.push(link('WhatsApp', 'https://wa.me/' + c.whatsapp, true));
    if (links.length) {
      const nav = document.createElement('div');
      nav.className = 'sf-links';
      links.forEach(function (a) { nav.appendChild(a); });
      inner.appendChild(nav);
    }
    footer.appendChild(inner);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('footer.site-footer').forEach(render);
  });
})();

/* FormLens "Model" panel — DOM + storage glue around ModelPicker.
 * Depends on: ModelPicker (src/modelPicker.js), and from index.html: getApiKey(), toast().
 * Exposes window.FormLensModel = { getModel, getProviderPrefs, isSaved }.
 * Fires 'formlens:model-saved' on document when the user saves a model.
 */
(function () {
  'use strict';
  const MP = window.ModelPicker;
  const SK_MODEL = 'formlens_model_v1';
  const SK_CAT = 'formlens_catalogue_v1';           // sessionStorage cache
  const DEFAULT_MODEL = 'z-ai/glm-5.2';
  const DEFAULT_ANSWERS = { forms: 'handwritten', identifiable: true, priority: 'balanced', pages: 1000 };

  let catalogue = null;
  let answers = Object.assign({}, DEFAULT_ANSWERS);
  let selectedId = null;   // radio selection, not yet saved
  let showAll = false;

  /* ── storage (wrapped: storage can throw in private modes) ── */
  function load() {
    try { return JSON.parse(localStorage.getItem(SK_MODEL)) || {}; } catch (e) { return {}; }
  }
  function save(state) {
    try { localStorage.setItem(SK_MODEL, JSON.stringify(state)); } catch (e) { /* ignore */ }
  }
  function getModel() { return load().id || DEFAULT_MODEL; }
  function isSaved() { return !!load().id; }
  /** 'none' | 'unknown' | 'ok' | 'text-only' | 'missing' for the saved model. */
  function savedStatus() { const id = load().id; return id ? MP.imageStatus(id, catalogue) : 'none'; }
  /** Status of the model extraction will actually use (saved, or the default). */
  function effectiveStatus() { return MP.imageStatus(getModel(), catalogue); }
  function formsAnswer() { return (load().answers || answers).forms; }
  function getProviderPrefs() { return MP.providerPrefs(load().answers || DEFAULT_ANSWERS); }

  /* ── catalogue ── */
  async function fetchCatalogue() {
    if (catalogue) return catalogue;
    try {
      const cached = sessionStorage.getItem(SK_CAT);
      if (cached) { catalogue = JSON.parse(cached); return catalogue; }
    } catch (e) { /* ignore */ }
    const headers = {};
    const key = typeof getApiKey === 'function' ? getApiKey() : '';
    if (key) headers.Authorization = 'Bearer ' + key;
    const r = await fetch('https://openrouter.ai/api/v1/models', { headers: headers });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    catalogue = d.data || [];
    try { sessionStorage.setItem(SK_CAT, JSON.stringify(catalogue)); } catch (e) { /* quota: fine */ }
    return catalogue;
  }

  /* ── helpers ── */
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  /* ── rendering ── */
  /* Header = the SAVED model (what extraction will use). */
  function renderHeader() {
    renderHeaderInner();
    if (window.FormLensSteps) FormLensSteps.refresh();
  }
  function renderHeaderInner() {
    const saved = load().id;
    const dot = $('mp-dot'), status = $('mp-status');
    $('mp-current').textContent = saved || 'not chosen';
    if (!saved) {
      dot.className = 'apikey-status-dot';
      status.textContent = 'Choose a model to continue';
      return;
    }
    const st = MP.imageStatus(saved, catalogue);
    if (st === 'missing') {
      dot.className = 'apikey-status-dot warn';
      status.textContent = 'Saved model not found on OpenRouter \u2014 choose another';
    } else if (st === 'text-only') {
      dot.className = 'apikey-status-dot ' + (answers.forms === 'typed' ? 'warn' : 'err');
      status.textContent = answers.forms === 'typed'
        ? 'Text-only model \u00b7 fine for digital PDFs, not scans'
        : 'Saved model can\u2019t read images';
    } else {
      dot.className = 'apikey-status-dot ok';
      status.textContent = 'Saved \u00b7 used for all extraction';
    }
  }

  /* Warning box + Use button = the HIGHLIGHTED model (what the user is looking at). */
  function renderSelection() {
    const warn = $('mp-warn'), use = $('mp-use');
    const st = selectedId ? MP.imageStatus(selectedId, catalogue) : 'unknown';
    if (st === 'text-only') {
      $('mp-warn-txt').textContent = answers.forms === 'typed'
        ? selectedId + ' only reads text. It works for digitally created PDFs, but not for scanned pages.'
        : selectedId + ' can\u2019t read images, so scanned or handwritten forms will extract poorly. Pick a vision model below.';
      warn.style.display = 'flex';
    } else {
      warn.style.display = 'none';
    }
    const saved = load();
    const sameAnswers = JSON.stringify(saved.answers || {}) === JSON.stringify(answers);
    const isSavedChoice = !!selectedId && selectedId === saved.id && sameAnswers;
    use.textContent = isSavedChoice ? 'Saved \u2713' : 'Use this model';
    use.className = 'btn btn-sm ' + (isSavedChoice ? 'btn-o' : 'btn-p');
    use.disabled = !selectedId || isSavedChoice;
  }

  function renderOptions() {
    document.querySelectorAll('.mp-opt').forEach(function (b) {
      const k = b.dataset.k;
      let v = b.dataset.v;
      if (k === 'identifiable') v = v === 'yes';
      b.classList.toggle('on', answers[k] === v);
    });
    const pages = $('mp-pages');
    if (document.activeElement !== pages) pages.value = Number(answers.pages).toLocaleString('en-US');
    $('mp-privacy').style.display = answers.identifiable ? 'flex' : 'none';
  }

  function recRow(item) {
    const row = el('div', 'mp-rec' + (item.id === selectedId ? ' on' : ''));
    row.setAttribute('role', 'radio');
    row.setAttribute('aria-checked', item.id === selectedId ? 'true' : 'false');
    row.tabIndex = 0;
    row.appendChild(el('div', 'mp-radio'));
    const txt = el('div', 'mp-txt');
    const idLine = el('div', 'mp-id', item.id);
    if (item.tested) idLine.appendChild(el('span', 'mp-tag', 'Tested on CRFs'));
    txt.appendChild(idLine);
    txt.appendChild(el('div', 'mp-why', item.reason));
    if (item.warning) txt.appendChild(el('div', 'mp-warnline', item.warning));
    row.appendChild(txt);
    const cost = el('div', 'mp-cost', MP.formatCost(item.estMonthlyCost) + ' / mo');
    cost.appendChild(el('small', null, 'est. at ' + Number(answers.pages).toLocaleString('en-US') + ' pages'));
    row.appendChild(cost);
    function pick() { selectedId = item.id; renderRecs(); }
    row.addEventListener('click', pick);
    row.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });
    return row;
  }

  function renderRecs() {
    const box = $('mp-recs');
    box.innerHTML = '';
    if (!catalogue) { box.appendChild(el('div', 'mp-why', 'Loading models…')); return; }
    let items;
    if (showAll) {
      items = MP.allVision(catalogue, answers).map(function (m) {
        return { id: m.id, reason: m.name || m.id, tested: false, estMonthlyCost: MP.estimateCost(m, answers.pages), warning: null };
      });
    } else {
      items = MP.recommend(answers, catalogue);
    }
    if (!items.length) { box.appendChild(el('div', 'mp-why', 'No matching vision models found.')); return; }
    if (!selectedId || !items.some(function (i) { return i.id === selectedId; })) selectedId = items[0].id;
    box.appendChild(el('div', 'slabel', showAll ? 'All vision models (' + items.length + ')' : 'Recommended'));
    const list = el('div', 'mp-list' + (showAll ? ' all' : ''));
    list.setAttribute('role', 'radiogroup');
    items.forEach(function (i) { list.appendChild(recRow(i)); });
    box.appendChild(list);
    $('mp-toggle-all').textContent = showAll ? '← Back to recommendations' : 'Show all vision models →';
    renderSelection();
  }

  function renderAll() { renderHeader(); renderOptions(); renderRecs(); }

  /* ── actions ── */
  function togglePanel(force) {
    const body = $('mp-body'), chev = $('mp-chevron');
    const open = force === undefined ? !body.classList.contains('open') : force;
    body.classList.toggle('open', open);
    chev.classList.toggle('open', open);
    if (open) ensureCatalogue();
  }

  async function ensureCatalogue() {
    if (catalogue) return;
    renderRecs();
    try { await fetchCatalogue(); }
    catch (e) {
      $('mp-recs').innerHTML = '';
      $('mp-recs').appendChild(el('div', 'mp-why', 'Couldn’t load the model list (' + e.message + '). Check your connection and reopen this panel.'));
      return;
    }
    renderAll();
  }

  function useSelected() {
    if (!selectedId) return;
    save({ id: selectedId, answers: answers });
    renderHeader();
    renderSelection();
    document.dispatchEvent(new CustomEvent('formlens:model-saved'));
    if (typeof toast === 'function') toast('Model set to ' + selectedId, 'ok');
    togglePanel(false);
  }

  function init() {
    if (!$('mp-panel')) return;
    const saved = load();
    if (saved.answers) answers = Object.assign({}, DEFAULT_ANSWERS, saved.answers);
    answers = { forms: answers.forms, identifiable: answers.identifiable, priority: answers.priority, pages: answers.pages };
    selectedId = saved.id || null;

    $('mp-head').addEventListener('click', function () { togglePanel(); });
    document.querySelectorAll('.mp-opt').forEach(function (b) {
      b.addEventListener('click', function () {
        const k = b.dataset.k;
        answers[k] = k === 'identifiable' ? b.dataset.v === 'yes' : b.dataset.v;
        showAll = false;
        selectedId = null;   // new answers -> preselect the new top recommendation
        renderOptions(); renderRecs(); renderHeader();
      });
    });
    $('mp-pages').addEventListener('input', function (e) {
      const n = parseInt(String(e.target.value).replace(/[^0-9]/g, ''), 10);
      answers.pages = Number.isFinite(n) ? Math.min(n, 10000000) : 0;
      renderRecs();
    });
    $('mp-pages').addEventListener('blur', renderOptions);
    $('mp-toggle-all').addEventListener('click', function () { showAll = !showAll; renderRecs(); });
    $('mp-use').addEventListener('click', useSelected);

    renderOptions();
    renderHeader();
    // Load the catalogue quietly so the image-capability warning can show
    // even while the panel is closed.
    fetchCatalogue().then(renderAll).catch(function () { /* shown when opened */ });
  }

  window.FormLensModel = { getModel: getModel, getProviderPrefs: getProviderPrefs, isSaved: isSaved, savedStatus: savedStatus,
    effectiveStatus: effectiveStatus, formsAnswer: formsAnswer };
  document.addEventListener('DOMContentLoaded', init);
})();

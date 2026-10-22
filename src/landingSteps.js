/* FormLens landing: two steps.
 *   Step 1 "Setup": API key + model. Next is enabled once both are saved.
 *   Step 2 "Start": discover a schema or load a saved profile.
 * Depends on (from index.html): getApiKey(), maskKey(); FormLensModel (src/modelPanel.js).
 * Exposes window.FormLensSteps = { show, refresh, isReady }.
 */
(function () {
  'use strict';
  let current = 1;

  function $(id) { return document.getElementById(id); }

  /* Only the API key is required. Model problems are warnings, not blocks. */
  function isReady() {
    return !!(typeof getApiKey === 'function' && getApiKey());
  }

  /* Returns { text, warn } describing the model extraction will use. */
  function modelNote() {
    const M = window.FormLensModel;
    const id = M.getModel();
    const st = M.effectiveStatus();
    const who = M.isSaved() ? id : 'No model chosen. The default, ' + id + ',';
    if (st === 'missing') return { text: '\u26a0 ' + who + ' isn\u2019t on OpenRouter, so extraction will probably fail.', warn: true };
    if (st === 'text-only') {
      return M.formsAnswer() === 'typed'
        ? { text: '\u26a0 ' + who + ' only reads text: fine for digital PDFs, not scans.', warn: true }
        : { text: '\u26a0 ' + who + ' can\u2019t read images, so scanned or handwritten forms will extract poorly.', warn: true };
    }
    if (!M.isSaved()) return { text: '\u26a0 No model chosen, so the default ' + id + ' will be used.', warn: true };
    return { text: 'Setup saved on this browser.', warn: false };
  }

  function refresh() {
    if (!$('land-step-1')) return;
    const ready = isReady();
    $('ls-next').disabled = !ready;
    const hint = $('ls-hint');
    const key = ready ? getApiKey() : '';
    let note = { text: 'Add your OpenRouter key to continue.', warn: false };
    if (ready) note = modelNote();
    hint.textContent = note.text;
    hint.classList.toggle('warn', note.warn);

    $('ls-step2').classList.toggle('done', false);
    $('ls-step1').classList.toggle('active', current === 1);
    $('ls-step1').classList.toggle('done', current === 2);
    $('ls-step2').classList.toggle('active', current === 2);
    $('ls-step2').classList.toggle('reachable', current === 1 && ready);

    if (ready) {
      $('ls-sum-key').textContent = typeof maskKey === 'function' ? maskKey(key) : '';
      $('ls-sum-model').textContent = FormLensModel.getModel();
      const st = FormLensModel.effectiveStatus();
      const flag = $('ls-sum-flag');
      flag.textContent = st === 'missing' ? 'not on OpenRouter'
        : st === 'text-only' ? (FormLensModel.formsAnswer() === 'typed' ? 'text only' : 'can\u2019t read images') : '';
      flag.style.display = flag.textContent ? '' : 'none';
    }
  }

  function show(step) {
    if (step === 2 && !isReady()) step = 1;
    current = step;
    $('land-step-1').style.display = step === 1 ? '' : 'none';
    $('land-step-2').style.display = step === 2 ? '' : 'none';
    const copy = step === 1
      ? ['Set up FormLens', 'Connect your OpenRouter key and choose a model. You only do this once per browser.']
      : ['How do you want to start?', 'Discover the schema of a new form, or load a profile you saved before.'];
    if ($('land-title')) $('land-title').textContent = copy[0];
    if ($('land-sub')) $('land-sub').textContent = copy[1];
    refresh();
    const scroller = $('screen-landing');
    if (scroller) scroller.scrollTop = 0;
  }

  function init() {
    if (!$('land-step-1')) return;
    $('ls-next').addEventListener('click', function () { show(2); });
    $('ls-back').addEventListener('click', function () { show(1); });
    $('ls-step1').addEventListener('click', function () { if (current === 2) show(1); });
    $('ls-step2').addEventListener('click', function () { if (current === 1 && isReady()) show(2); });
    document.addEventListener('formlens:model-saved', refresh);
    show(1);
  }

  window.FormLensSteps = { show: show, refresh: refresh, isReady: isReady };
  document.addEventListener('DOMContentLoaded', init);
})();

/* FormLens model picker — pure logic, no DOM, no network.
 *
 * Loaded in the browser as a plain <script> (exposes window.ModelPicker)
 * and in Node tests via require() (module.exports). Everything here takes
 * the OpenRouter catalogue as an argument, so it is testable offline.
 *
 * Catalogue entries follow GET https://openrouter.ai/api/v1/models:
 *   { id, name, architecture:{input_modalities:[...], output_modalities:[...]},
 *     pricing:{prompt:"0.000002", completion:"0.00001", ...} }   (USD per token, strings)
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ModelPicker = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /* Candidate shortlist. `tested` must stay false until the model has been
     benchmarked on real CRFs — only tested models get the "Tested on CRFs"
     tag. Entries missing from the live catalogue are ignored automatically. */
  const DEFAULT_SHORTLIST = [
    { id: 'anthropic/claude-sonnet-5.5', reason: 'Strong on handwriting and dense forms', tested: false },
    { id: 'google/gemini-4-argon', reason: 'Reads PDFs natively; strong on long documents', tested: false },
    { id: 'anthropic/claude-haiku-5.5', reason: 'Fast and low-cost; best on typed forms', tested: false },
  ];

  /* Rough token budget per form page. Deliberately conservative; tune once
     real usage numbers are available from OpenRouter's activity page. */
  const TOKENS_PER_PAGE = { input: 2500, output: 600 };

  const MAX_RECS = 3;

  function num(v) {
    const n = typeof v === 'number' ? v : parseFloat(v);
    return Number.isFinite(n) ? n : NaN;
  }

  /** True if the model can look at images (needed for scanned/handwritten forms). */
  function canSeeImages(model) {
    const arch = (model && model.architecture) || {};
    const inp = arch.input_modalities || [];
    const out = arch.output_modalities || ['text'];
    return inp.indexOf('image') !== -1 && out.indexOf('text') !== -1;
  }

  /**
   * Can this model handle the user's forms?
   *   'ok'        model accepts images
   *   'text-only' model only reads text (OpenRouter extracts the PDF text layer:
   *               fine for digital PDFs, fails on scans and handwriting)
   *   'missing'   model id not in the catalogue (renamed or retired)
   *   'unknown'   catalogue not loaded yet
   */
  function imageStatus(modelId, catalogue) {
    if (!catalogue) return 'unknown';
    const m = catalogue.find(function (x) { return x && x.id === modelId; });
    if (!m) return 'missing';
    return canSeeImages(m) ? 'ok' : 'text-only';
  }

  /** True if prices are known and non-negative (excludes routers with variable pricing). */
  function hasFixedPrice(model) {
    const p = (model && model.pricing) || {};
    return num(p.prompt) >= 0 && num(p.completion) >= 0;
  }

  function isFree(model) {
    const p = model.pricing || {};
    return /:free$/.test(model.id) || (num(p.prompt) === 0 && num(p.completion) === 0);
  }

  /** Estimated USD cost for `pages` pages, or null if pricing is unknown. */
  function estimateCost(model, pages, tokens) {
    const t = tokens || TOKENS_PER_PAGE;
    if (!hasFixedPrice(model)) return null;
    const perPage = t.input * num(model.pricing.prompt) + t.output * num(model.pricing.completion);
    return perPage * Math.max(0, num(pages) || 0);
  }

  /** Vision-capable models suitable for interactive extraction. */
  function eligibleModels(catalogue, answers) {
    const a = answers || {};
    return (catalogue || []).filter(function (m) {
      if (!m || !m.id || /:batch$/.test(m.id)) return false; // batch variants are async-only
      if (!canSeeImages(m) || !hasFixedPrice(m)) return false;
      if (a.identifiable && isFree(m)) return false;         // free endpoints commonly log prompts
      return true;
    });
  }

  function byCost(pages) {
    return function (x, y) { return estimateCost(x, pages) - estimateCost(y, pages); };
  }

  /**
   * Recommend up to 3 models.
   * answers: { forms: 'handwritten'|'typed'|'mixed', identifiable: bool,
   *            priority: 'accuracy'|'balanced'|'cost', pages: number }
   * Returns [{ id, name, reason, tested, estMonthlyCost, warning }]
   */
  function recommend(answers, catalogue, shortlist) {
    const a = Object.assign({ forms: 'handwritten', identifiable: true, priority: 'balanced', pages: 1000 }, answers);
    const list = shortlist || DEFAULT_SHORTLIST;
    const pool = eligibleModels(catalogue, a);
    const byId = {};
    pool.forEach(function (m) { byId[m.id] = m; });

    const short = list.filter(function (s) { return byId[s.id]; })
      .map(function (s) { return { model: byId[s.id], meta: s }; });
    const others = pool.filter(function (m) { return !list.some(function (s) { return s.id === m.id; }); })
      .sort(byCost(a.pages))
      .map(function (m) { return { model: m, meta: null }; });

    let ordered;
    if (a.priority === 'cost') {
      ordered = short.concat(others).sort(function (x, y) { return byCost(a.pages)(x.model, y.model); });
    } else if (a.priority === 'accuracy') {
      ordered = short.concat(others.slice().reverse()); // price as a weak proxy after the shortlist
    } else {
      ordered = short.concat(others);
    }

    const handwriting = a.forms !== 'typed';
    return ordered.slice(0, MAX_RECS).map(function (c) {
      const tested = !!(c.meta && c.meta.tested);
      let reason = c.meta ? c.meta.reason : (a.priority === 'accuracy' ? 'Higher-end vision model' : 'Low-cost vision model');
      let warning = null;
      if (handwriting && !tested) warning = 'Not yet tested on handwritten CRFs';
      return {
        id: c.model.id,
        name: c.model.name || c.model.id,
        reason: reason,
        tested: tested,
        estMonthlyCost: estimateCost(c.model, a.pages),
        warning: warning,
      };
    });
  }

  /** Every eligible model, cheapest first — for "Show all vision models". */
  function allVision(catalogue, answers) {
    const pages = (answers && answers.pages) || 1000;
    return eligibleModels(catalogue, answers).sort(byCost(pages));
  }

  /** OpenRouter `provider` routing block for a request, or undefined. */
  function providerPrefs(answers) {
    if (answers && answers.identifiable) return { zdr: true, data_collection: 'deny' };
    return undefined;
  }

  function formatCost(usd) {
    if (usd === null || !Number.isFinite(usd)) return '—';
    if (usd < 1) return '<$1';
    if (usd < 100) return '~$' + Math.round(usd);
    return '~$' + Math.round(usd).toLocaleString('en-US');
  }

  return {
    DEFAULT_SHORTLIST: DEFAULT_SHORTLIST,
    TOKENS_PER_PAGE: TOKENS_PER_PAGE,
    canSeeImages: canSeeImages,
    imageStatus: imageStatus,
    estimateCost: estimateCost,
    eligibleModels: eligibleModels,
    recommend: recommend,
    allVision: allVision,
    providerPrefs: providerPrefs,
    formatCost: formatCost,
  };
});

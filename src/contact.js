/* FormLens contact settings — shared by every page (index.html and app.html).
 *
 *   formEndpoint : a form-service URL that emails you each pilot request
 *                  (e.g. a Formspree or Basin endpoint). Leave '' to skip.
 *   whatsapp     : your number in international format, digits only
 *                  (e.g. '2207xxxxxx'). Used for WhatsApp links, and as the
 *                  pilot-form fallback when no formEndpoint is set.
 *   email        : your contact email (footer link, last-resort fallback).
 *
 * Links for anything left blank are hidden automatically.
 */
window.FORMLENS_CONTACT = {
  formEndpoint: '',
  whatsapp: '+220877441595',
  email: 'info@amlabs-africa.com'
};

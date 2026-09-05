const CHROME_FAMILY = /Chrom(e|ium)|CriOS|Edg|OPR|Brave/i;
const FIREFOX = /Firefox|FxiOS/i;

export function detectBrowser(nav = typeof navigator === 'undefined' ? {} : navigator) {
  const ua = nav.userAgent || '';
  const vendor = nav.vendor || '';
  const platform = nav.platform || '';
  const touchPoints = nav.maxTouchPoints || 0;

  const ios = /iP(hone|od|ad)/.test(ua) || (platform === 'MacIntel' && touchPoints > 1);
  const macos = /Mac/.test(platform || ua) && !ios;
  const windows = /Win/.test(platform || ua);
  const android = /Android/i.test(ua);

  const safari = /Safari/i.test(ua)
    && /Apple Computer/i.test(vendor)
    && !CHROME_FAMILY.test(ua)
    && !FIREFOX.test(ua)
    && !android;

  let browser = 'other';
  if (safari) browser = 'safari';
  else if (FIREFOX.test(ua)) browser = 'firefox';
  else if (/Edg\//.test(ua)) browser = 'edge';
  else if (CHROME_FAMILY.test(ua)) browser = 'chrome';

  const mobile = ios || android || /Mobile/i.test(ua);
  let os = 'other';
  if (ios) os = 'ios';
  else if (macos) os = 'macos';
  else if (windows) os = 'windows';
  else if (android) os = 'android';
  else if (/Linux/.test(ua)) os = 'linux';

  return { browser, os, mobile, safari };
}

export function applyBrowserProfile(target = typeof document === 'undefined' ? null : document.documentElement) {
  if (!target) return null;
  const profile = detectBrowser();
  target.dataset.browser = profile.browser;
  target.dataset.os = profile.os;
  if (profile.mobile) target.dataset.mobile = 'true';
  else delete target.dataset.mobile;
  return profile;
}

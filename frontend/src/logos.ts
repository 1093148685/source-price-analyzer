// Product logos as inline SVG
const LOGOS: Record<string, string> = {
  chatgpt: '<svg width="48" height="48" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#10A37F"/><path d="M42.15 28.78c-.88-3.6-3.85-6.6-7.47-7.47-2.3-.55-4.68-.22-6.75.9-2.05 1.12-3.71 2.92-4.65 5.15-.4.88-.67 1.82-.8 2.78l-.02.17c0 .03-.02.05-.05.05h-3.52c-.08 0-.15.05-.17.12-.3 1.23-.3 2.52 0 3.75.02.07.1.12.17.12h3.53c.02 0 .04.02.04.05l.02.17c.13.95.4 1.88.78 2.77.94 2.23 2.6 4.03 4.65 5.15 2.08 1.12 4.46 1.45 6.76.9 3.62-.88 6.6-3.87 7.48-7.47.47-1.93.35-3.97-.33-5.8-.68-1.84-1.92-3.38-3.53-4.35 1.61-.97 2.85-2.51 3.53-4.35.68-1.83.8-3.87.34-5.8zM32 37.63c-2.28 0-4.13-1.85-4.13-4.13S29.72 29.38 32 29.38s4.13 1.85 4.13 4.13-1.85 4.12-4.13 4.12z" fill="#fff"/></svg>',
  claude: '<svg width="48" height="48" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#D97706"/><path d="M20 44V24l12 10 12-10v20" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  grok: '<svg width="48" height="48" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#111"/><path d="M18 18h6l6 10 6-10h6l-8 14 8 14h-6l-6-10-6 10h-6l8-14-8-14z" fill="#fff"/></svg>',
  netflix: '<svg width="48" height="48" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#E50914"/><path d="M22 18h4.5L36 46h-4.5L22 18zM38 18h4.5v28H38zM26 18h4.5v28H26z" fill="#fff"/></svg>',
  'cloud-drive': '<svg width="48" height="48" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#3B82F6"/><path d="M38 26c3.87 0 7 3.13 7 7 0 3.4-2.43 6.2-5.65 6.9l-.08.01H23.73l-.08-.01C20.43 39.2 18 36.4 18 33c0-3.87 3.13-7 7-7 1.1 0 2.15.27 3.08.73.64-3.63 3.8-6.73 7.42-6.73 3 0 5.6 1.57 6.83 3.86.7-.54 1.6-.86 2.57-.86z" fill="#fff"/></svg>',
  apple: '<svg width="48" height="48" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#555"/><path d="M39.5 18c.8-.9 1.3-2.2 1.2-3.5-1.1.1-2.5.7-3.3 1.7-.7.85-1.3 2.1-1.2 3.4 1.3.1 2.6-.6 3.3-1.6zM43 36.5c0 1.5-.3 3-1 4.2-.7 1.2-1.5 2.4-2.7 3.4-1.6 1.3-3.1 2.2-5 2.2-1.4 0-2.7-.4-3.8-1-.9-.5-1.8-.8-2.6-.8-.7 0-1.6.3-2.5.8-1 .6-2.2 1-3.6 1-1.9 0-3.4-.9-5-2.2-1.6-1.4-2.8-3-3.5-4.8-.8-2-1.2-4.2-1.2-6.3 0-2.6.6-4.9 1.8-6.7s2.8-3 4.8-3.7c.9-.3 2-.5 3.1-.5 1.2 0 2.4.3 3.6.8 1 .4 1.9.8 2.8.8.8 0 1.7-.4 2.8-.9 1.3-.6 2.6-1 3.8-1 1.1 0 2.2.2 3.2.6 2 .7 3.5 1.9 4.7 3.7 1.2 1.8 1.8 3.9 1.8 6.4z" fill="#fff"/></svg>',
  other: '<svg width="48" height="48" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#6B7280"/><circle cx="32" cy="32" r="12" stroke="#fff" stroke-width="3" fill="none"/><path d="M32 20v6m0 12v6M20 32h6m12 0h6" stroke="#fff" stroke-width="3" stroke-linecap="round"/></svg>'
};

export function getLogo(slug: string): string {
  return LOGOS[slug] || LOGOS.other;
}

export function getBigLogo(slug: string): string {
  const small = getLogo(slug);
  return small.replace(/width="48"/g, 'width="64"').replace(/height="48"/g, 'height="64"');
}

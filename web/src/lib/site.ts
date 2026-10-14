// Set the public production origin at build time. Do not infer it from preview
// hosts: every deployment should point search engines to the same public site.
export const siteUrl = new URL(
  process.env.NEXT_PUBLIC_SITE_URL || 'https://www.njitschedulepro.com',
).origin;

export function canonicalUrl(path: string) {
  return new URL(path, siteUrl).toString();
}

export const socialImage = {
  url: canonicalUrl('/opengraph-image'),
  width: 1200,
  height: 630,
  alt: 'NJIT Schedule Pro course schedule builder',
};

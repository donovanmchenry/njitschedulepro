const normalizeBaseUrl = (baseUrl: string) => baseUrl.replace(/\/$/, '');

const baseUrl =
  typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_BASE_URL
    ? normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL)
    : undefined;

/**
 * Builds an absolute API URL when NEXT_PUBLIC_API_BASE_URL is provided, or
 * falls back to the Next.js API proxy path for local development.
 */
export const apiUrl = (path: string) => {
  const cleanedPath = path.startsWith('/') ? path : `/${path}`;
  if (baseUrl) {
    return `${baseUrl}${cleanedPath}`;
  }
  return `/api${cleanedPath}`;
};

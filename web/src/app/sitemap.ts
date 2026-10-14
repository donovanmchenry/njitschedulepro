import type { MetadataRoute } from 'next';
import { guides } from '@/lib/guides';
import { canonicalUrl } from '@/lib/site';

export default function sitemap(): MetadataRoute.Sitemap {
  return ['/', ...guides.map(({ slug }) => `/guides/${slug}`)].map((path) => ({
    url: canonicalUrl(path),
  }));
}

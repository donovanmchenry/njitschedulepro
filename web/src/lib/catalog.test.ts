import { afterEach, expect, it, vi } from 'vitest';
import { loadCatalogIndex } from './catalog';

const catalog = (term: string) => ({ term, version: term, courses: [], total: 0 });
const response = (term: string) => ({ ok: true, json: async () => catalog(term) }) as Response;

afterEach(() => vi.unstubAllGlobals());

it('falls back to the Spring API when a cached static catalog belongs to Winter', async () => {
  const fetch = vi.fn().mockResolvedValueOnce(response('202695')).mockResolvedValueOnce(response('202710'));
  vi.stubGlobal('fetch', fetch);
  expect((await loadCatalogIndex()).term).toBe('202710');
  expect(fetch).toHaveBeenNthCalledWith(1, '/catalog/index.json?term=202710', { cache: 'no-cache' });
  expect(fetch).toHaveBeenCalledTimes(2);
});

it('does not display another semester when both sources are stale', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response('202690')));
  await expect(loadCatalogIndex()).rejects.toThrow('active semester');
});

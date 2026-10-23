import { CatalogIndex, SubjectCatalog } from '@/types';
import { apiUrl } from './api';

export const ACTIVE_TERM = { code: '202710', label: 'Spring 2027' } as const;

function requireActiveTerm(data: CatalogIndex): CatalogIndex {
  if (data.term !== ACTIVE_TERM.code) throw new Error('The active semester catalog is not available yet');
  return data;
}

let catalogVersion = '';
const subjectRequests = new Map<string, Promise<SubjectCatalog>>();

async function requireJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export async function loadCatalogIndex(): Promise<CatalogIndex> {
  try {
    const data = requireActiveTerm(await requireJson<CatalogIndex>(
      await fetch(`/catalog/index.json?term=${ACTIVE_TERM.code}`, { cache: 'no-cache' })
    ));
    catalogVersion = data.version;
    return data;
  } catch {
    const data = requireActiveTerm(await requireJson<CatalogIndex>(await fetch(apiUrl('/catalog/courses'))));
    catalogVersion = data.version;
    return data;
  }
}

export function loadSubjectCatalog(subject: string): Promise<SubjectCatalog> {
  const normalizedSubject = subject.trim().toUpperCase();
  const existing = subjectRequests.get(normalizedSubject);
  if (existing) return existing;

  const request = (async () => {
    try {
      const versionQuery = catalogVersion ? `?v=${catalogVersion}` : '';
      return await requireJson<SubjectCatalog>(
        await fetch(`/catalog/subjects/${encodeURIComponent(normalizedSubject)}.json${versionQuery}`, {
          cache: 'force-cache',
        })
      );
    } catch {
      return requireJson<SubjectCatalog>(
        await fetch(apiUrl(`/catalog/subjects/${encodeURIComponent(normalizedSubject)}`))
      );
    }
  })();

  subjectRequests.set(normalizedSubject, request);
  request.catch(() => subjectRequests.delete(normalizedSubject));
  return request;
}

import type { Metadata } from 'next';
import ScheduleHome from '@/components/ScheduleHome';
import { canonicalUrl } from '@/lib/site';

export const metadata: Metadata = {
  verification: { google: 'Jr9ymrZXi8IGIBXU9oDGzbhW8UzOtn-w0WnqrEf7DKM' },
  alternates: { canonical: canonicalUrl('/') },
  openGraph: { siteName: 'NJIT Schedule Pro', type: 'website', locale: 'en_US', url: canonicalUrl('/') },
};

const application = {
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: 'NJIT Schedule Pro',
  url: canonicalUrl('/'),
  applicationCategory: 'EducationalApplication',
  operatingSystem: 'Web browser',
  description: 'An independent NJIT course schedule builder that generates conflict-free schedules using selected courses, unavailable times, and filters.',
  creator: { '@type': 'Person', name: 'Donovan McHenry' },
  featureList: ['Conflict-free schedule generation', 'Unavailable time blocks', 'Course section filters', 'Schedule bookmarks', 'ICS and CSV export'],
};

const structuredData = {
  '@context': 'https://schema.org',
  '@graph': [
    application,
    { '@type': 'WebSite', name: 'NJIT Schedule Pro', alternateName: 'NJIT SchedulePro', url: canonicalUrl('/') },
  ],
};

export default function Home() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData).replace(/</g, '\\u003c') }} />
      <ScheduleHome />
    </>
  );
}

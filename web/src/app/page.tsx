import Link from 'next/link';
import type { Metadata } from 'next';
import ScheduleHome from '@/components/ScheduleHome';
import { guides, schedulingFaqs } from '@/lib/guides';
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
      <section aria-labelledby="about-builder" className="border-t border-gray-200 bg-white px-6 py-12 text-gray-900 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-100">
        <div className="mx-auto max-w-4xl space-y-8">
          <div>
            <h1 id="about-builder" className="text-2xl font-bold">NJIT Schedule Builder &amp; Course Planner</h1>
            <p className="mt-3 leading-relaxed">NJIT Schedule Pro helps New Jersey Institute of Technology students generate conflict-free class schedules. Choose courses, block work or commuting hours, compare section combinations, and export your plan to your calendar.</p>
          </div>
          <nav id="planning-guides" aria-label="Schedule planning guides">
            <h2 className="text-xl font-semibold">NJIT schedule planning guides</h2>
            <ul className="mt-3 space-y-3">
              {guides.map((guide) => <li key={guide.slug}><Link className="text-blue-700 underline underline-offset-4 dark:text-blue-300" href={`/guides/${guide.slug}`}>{guide.title}</Link></li>)}
            </ul>
          </nav>
          <div>
            <h2 className="text-xl font-semibold">Frequently asked questions</h2>
            <dl className="mt-4 space-y-5">
              {schedulingFaqs.map(([question, answer]) => <div key={question}><dt className="font-semibold">{question}</dt><dd className="mt-1 leading-relaxed">{answer}</dd></div>)}
            </dl>
          </div>
          <p className="text-sm">Confirm section availability and registration details with the <a className="underline" href="https://www.njit.edu/registrar/schedules">NJIT Office of the Registrar</a>.</p>
        </div>
      </section>
    </>
  );
}

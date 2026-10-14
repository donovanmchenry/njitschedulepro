import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { guides } from '@/lib/guides';
import { canonicalUrl, socialImage } from '@/lib/site';

type Props = { params: Promise<{ slug: string }> };
export const dynamicParams = false;

export function generateStaticParams() {
  return guides.map(({ slug }) => ({ slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const guide = guides.find((item) => item.slug === slug);
  if (!guide) return {};
  return {
    title: `${guide.title} | NJIT Schedule Pro`,
    description: guide.description,
    alternates: { canonical: canonicalUrl(`/guides/${slug}`) },
    openGraph: { siteName: 'NJIT Schedule Pro', type: 'website', locale: 'en_US', title: guide.title, description: guide.description, url: canonicalUrl(`/guides/${slug}`), images: [socialImage] },
  };
}

export default async function GuidePage({ params }: Props) {
  const { slug } = await params;
  const guide = guides.find((item) => item.slug === slug);
  if (!guide) notFound();

  const breadcrumbs = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'NJIT Schedule Pro', item: canonicalUrl('/') },
      { '@type': 'ListItem', position: 2, name: guide.title, item: canonicalUrl(`/guides/${slug}`) },
    ],
  };

  return (
    <main className="min-h-screen bg-white px-6 py-12 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbs).replace(/</g, '\\u003c') }} />
      <article className="mx-auto max-w-3xl space-y-8">
        <Link href="/" className="text-blue-700 underline dark:text-blue-300">NJIT Schedule Pro — open the schedule builder</Link>
        <header><h1 className="text-3xl font-bold">{guide.title}</h1><p className="mt-4 text-lg leading-relaxed">{guide.intro}</p></header>
        <ol className="list-decimal space-y-6 pl-6">
          {guide.steps.map(([title, text]) => <li key={title}><h2 className="text-xl font-semibold">{title}</h2><p className="mt-2 leading-relaxed">{text}</p></li>)}
        </ol>
        {slug === 'export-njit-schedule-to-google-calendar' && <p>See <a className="underline" href="https://support.google.com/calendar/answer/37118">Google Calendar’s official import instructions</a> for details.</p>}
        <p className="rounded-lg bg-gray-100 p-4 text-sm dark:bg-gray-900">NJIT Schedule Pro is an independent planning tool maintained by Donovan McHenry. It does not register you for classes. Confirm course details with the <a className="underline" href="https://www.njit.edu/registrar/schedules">NJIT registrar</a>.</p>
        <nav aria-label="Related guides"><h2 className="text-xl font-semibold">More scheduling help</h2><ul className="mt-3 space-y-3">{guides.filter((item) => item.slug !== slug).map((item) => <li key={item.slug}><Link className="text-blue-700 underline dark:text-blue-300" href={`/guides/${item.slug}`}>{item.title}</Link></li>)}</ul></nav>
      </article>
    </main>
  );
}

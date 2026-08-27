'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { ScheduleBuilder } from '@/components/ScheduleBuilder';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Notice } from '@/components/Notice';
import { useAppStore } from '@/lib/store';
import { apiUrl } from '@/lib/api';
import { Loader2 } from 'lucide-react';

export default function Home() {
  const { setCourses, setSchedules } = useAppStore();
  const [catalogState, setCatalogState] = useState<'loading' | 'ready' | 'error'>('loading');

  useEffect(() => {
    const loadCourses = async () => {
      setCatalogState('loading');
      try {
        const response = await fetch(apiUrl('/catalog/courses'));
        if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
        const data = await response.json();
        setCourses(data.courses || []);
        setCatalogState('ready');
      } catch (error) {
        console.error('Failed to load courses:', error);
        setCatalogState('error');
      }
    };

    loadCourses();
  }, [setCourses]);

  // Load a shared schedule if ?share= is present in the URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const shareId = params.get('share');
    if (!shareId) return;

    fetch(apiUrl(`/share/${shareId}`))
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          setSchedules([data]);
          // Remove the param from the address bar without reloading
          const url = new URL(window.location.href);
          url.searchParams.delete('share');
          window.history.replaceState({}, '', url.toString());
        }
      })
      .catch(() => {});
  }, [setSchedules]);

  return (
    <main className="min-h-screen overflow-x-hidden bg-[#f4f6fb] text-gray-950 dark:bg-gray-950 dark:text-white lg:flex lg:h-screen lg:flex-col lg:overflow-hidden">
      <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-gray-200 bg-white pl-5 pr-3 dark:border-gray-700 dark:bg-gray-900">
          <div className="flex min-w-0 items-center">
            <Image
              src="/scheduleprologo.png"
              alt="NJIT Schedule Pro"
              width={612}
              height={408}
              className="h-10 w-auto shrink-0"
              priority
            />
            <h1 className="sr-only">NJIT Schedule Pro</h1>
          </div>
          <ThemeToggle />
      </header>

      {catalogState !== 'ready' && (
          <Notice
            tone={catalogState === 'error' ? 'error' : 'info'}
            icon={catalogState === 'loading' ? Loader2 : undefined}
            iconClassName={catalogState === 'loading' ? 'animate-spin' : ''}
            className="shrink-0 rounded-none border-x-0 border-t-0 pl-5 text-sm"
          >
            <p>
              {catalogState === 'loading'
                ? 'Loading the latest NJIT course catalog…'
                : 'The course catalog could not be loaded. Check the API configuration and try again.'}
            </p>
          </Notice>
      )}
      <div className="lg:min-h-0 lg:flex-1">
        <ScheduleBuilder />
      </div>
    </main>
  );
}

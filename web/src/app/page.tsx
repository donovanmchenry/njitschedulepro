'use client';

import { useEffect } from 'react';
import Image from 'next/image';
import { ScheduleBuilder } from '@/components/ScheduleBuilder';
import { useAppStore } from '@/lib/store';
import { apiUrl } from '@/lib/api';

export default function Home() {
  const { setCourses, setIsLoading } = useAppStore();

  useEffect(() => {
    // Load courses from API on mount
    const loadCourses = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(apiUrl('/catalog/courses'));
        const data = await response.json();
        setCourses(data.courses || []);
      } catch (error) {
        console.error('Failed to load courses:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadCourses();
  }, [setCourses, setIsLoading]);

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8 text-center">
          <div className="flex justify-center">
            <Image
              src="/scheduleprologo.png"
              alt="NJIT Schedule Pro logo"
              width={612}
              height={408}
              className="h-32 w-auto"
              priority
            />
          </div>
          <p className="sr-only">
            NJIT Schedule Pro - Generate your perfect course schedule with smart
            constraint solving
          </p>
        </header>
        <ScheduleBuilder />
      </div>
    </main>
  );
}

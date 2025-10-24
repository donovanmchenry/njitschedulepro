'use client';

import { useEffect } from 'react';
import { ScheduleBuilder } from '@/components/ScheduleBuilder';
import { useAppStore } from '@/lib/store';

export default function Home() {
  const { setCourses, setIsLoading } = useAppStore();

  useEffect(() => {
    // Load courses from API on mount
    const loadCourses = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('/api/catalog/courses');
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
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            NJIT Schedule Pro
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            Generate your perfect course schedule with smart constraint solving
          </p>
        </header>
        <ScheduleBuilder />
      </div>
    </main>
  );
}

'use client';

import { useEffect } from 'react';
import Image from 'next/image';
import { ScheduleBuilder } from '@/components/ScheduleBuilder';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useAppStore } from '@/lib/store';
import { apiUrl } from '@/lib/api';

export default function Home() {
  const { setCourses, setIsLoading, isLoading } = useAppStore();

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
        <div className="absolute right-4 top-4">
          <ThemeToggle />
        </div>
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
        <div
          className={`mb-6 mx-auto max-w-2xl transition-all duration-500 ease-in-out ${
            isLoading ? 'opacity-100 max-h-24' : 'opacity-0 max-h-0 overflow-hidden'
          }`}
        >
          <div className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-700 rounded-lg p-4 flex items-center gap-3">
            <svg
              className="animate-spin h-5 w-5 text-yellow-600 dark:text-yellow-400"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            <div>
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                Warming up the schedule engine… this may take a few seconds
              </p>
            </div>
          </div>
        </div>
        <ScheduleBuilder />
      </div>
    </main>
  );
}

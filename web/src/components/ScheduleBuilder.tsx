'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { CourseSelector } from './CourseSelector';
import { AvailabilityEditor } from './AvailabilityEditor';
import { FiltersPanel } from './FiltersPanel';
import { ScheduleView } from './ScheduleView';
import { ScheduleList } from './ScheduleList';
import { SolveRequest } from '@/types';

export function ScheduleBuilder() {
  const {
    selectedCourseKeys,
    unavailableBlocks,
    filters,
    minCredits,
    maxCredits,
    schedules,
    setSchedules,
    isLoading,
    setIsLoading,
  } = useAppStore();

  const [error, setError] = useState<string | null>(null);

  const handleGenerateSchedules = async () => {
    if (selectedCourseKeys.length === 0) {
      setError('Please select at least one course');
      return;
    }

    setIsLoading(true);
    setError(null);

    const request: SolveRequest = {
      required_course_keys: selectedCourseKeys,
      unavailable: unavailableBlocks,
      filters,
      min_credits: minCredits,
      max_credits: maxCredits,
      max_results: 500,
    };

    try {
      const response = await fetch('/api/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate schedules');
      }

      const data = await response.json();
      setSchedules(data.schedules || []);

      if (data.schedules.length === 0) {
        setError(
          'No valid schedules found. Try adjusting your constraints or availability blocks.'
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left panel - Builder */}
      <div className="lg:col-span-1 space-y-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
            Build Your Schedule
          </h2>

          <div className="space-y-6">
            {/* Course Selection */}
            <section>
              <h3 className="text-lg font-semibold mb-2 text-gray-700 dark:text-gray-200">
                Select Courses
              </h3>
              <CourseSelector />
            </section>

            {/* Availability */}
            <section>
              <h3 className="text-lg font-semibold mb-2 text-gray-700 dark:text-gray-200">
                Availability Constraints
              </h3>
              <AvailabilityEditor />
            </section>

            {/* Filters */}
            <section>
              <h3 className="text-lg font-semibold mb-2 text-gray-700 dark:text-gray-200">
                Filters & Preferences
              </h3>
              <FiltersPanel />
            </section>

            {/* Generate Button */}
            <button
              onClick={handleGenerateSchedules}
              disabled={isLoading || selectedCourseKeys.length === 0}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              {isLoading ? 'Generating...' : 'Generate Schedules'}
            </button>

            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right panels - Results */}
      <div className="lg:col-span-2 space-y-4">
        {schedules.length > 0 ? (
          <>
            <ScheduleView />
            <ScheduleList />
          </>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
            <div className="text-gray-400 dark:text-gray-500">
              <svg
                className="mx-auto h-24 w-24 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <p className="text-xl font-semibold mb-2">No Schedules Yet</p>
              <p className="text-sm">
                Select your courses and constraints, then generate schedules to see them here.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { CourseSelector } from './CourseSelector';
import { AvailabilityEditor } from './AvailabilityEditor';
import { FiltersPanel } from './FiltersPanel';
import { ScheduleView } from './ScheduleView';
import { ScheduleList } from './ScheduleList';
import { BookmarkedSchedules } from './BookmarkedSchedules';
import { AIScheduleInput } from './AIScheduleInput';
import { SolveRequest, Schedule } from '@/types';
import { useAppStore } from '@/lib/store';
import { apiUrl } from '@/lib/api';
import { Calendar, Bookmark } from 'lucide-react';

type Tab = 'generated' | 'bookmarks';

export function ScheduleBuilder() {
  const {
    selectedCourseKeys,
    requiredCRNs,
    preferredProfessors,
    unavailableBlocks,
    filters,
    schedules,
    setSchedules,
    isLoading,
    setIsLoading,
    bookmarkedSchedules,
    addCourse,
    addUnavailableBlock,
  } = useAppStore();

  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('generated');
  const [selectedBookmark, setSelectedBookmark] = useState<{
    schedule: Schedule;
    index: number;
  } | null>(null);
  const [aiSuccess, setAiSuccess] = useState<string | null>(null);

  const handleAIParsed = (constraints: any) => {
    // Add courses
    if (constraints.courses && Array.isArray(constraints.courses)) {
      constraints.courses.forEach((courseKey: string) => {
        if (!selectedCourseKeys.includes(courseKey)) {
          addCourse(courseKey);
        }
      });
    }

    // Add unavailable blocks
    if (constraints.unavailable_blocks && Array.isArray(constraints.unavailable_blocks)) {
      constraints.unavailable_blocks.forEach((block: any) => {
        addUnavailableBlock({
          day: block.day,
          start_min: block.start_min,
          end_min: block.end_min,
        });
      });
    }

    // Show success message
    const summary = [];
    if (constraints.courses?.length) {
      summary.push(`${constraints.courses.length} course(s)`);
    }
    if (constraints.unavailable_blocks?.length) {
      summary.push(`${constraints.unavailable_blocks.length} time block(s)`);
    }

    setAiSuccess(`Added: ${summary.join(', ')}`);
    setTimeout(() => setAiSuccess(null), 5000);
  };

  const handleGenerateSchedules = async () => {
    if (selectedCourseKeys.length === 0 && requiredCRNs.length === 0) {
      setError('Please select at least one course or CRN');
      return;
    }

    setIsLoading(true);
    setError(null);

    const request: SolveRequest = {
      required_course_keys: selectedCourseKeys,
      required_crns: requiredCRNs,
      preferred_professors: preferredProfessors,
      unavailable: unavailableBlocks,
      filters,
      max_results: 500,
    };

    try {
      const response = await fetch(apiUrl('/solve'), {
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
            {/* AI Input */}
            <section>
              <AIScheduleInput onConstraintsParsed={handleAIParsed} />
            </section>

            {/* Success Message */}
            {aiSuccess && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 px-4 py-3 rounded">
                {aiSuccess}
              </div>
            )}

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                  Or manually configure
                </span>
              </div>
            </div>

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
              className="w-full bg-njit-red hover:bg-red-700 disabled:bg-njit-gray text-white font-semibold py-3 px-4 rounded-lg transition-colors shadow-md"
            >
              {isLoading ? 'Generating...' : 'Generate Schedules'}
            </button>

            {error && (
              <div className="bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded">
                {error}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right panels - Results */}
      <div className="lg:col-span-2 space-y-4">
        {/* Tab Navigation */}
        <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setActiveTab('generated')}
            className={`flex items-center gap-2 px-4 py-3 font-semibold transition-colors border-b-2 ${
              activeTab === 'generated'
                ? 'border-njit-red text-njit-red dark:text-red-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            <Calendar size={18} />
            Generated Schedules
            {schedules.length > 0 && (
              <span className="ml-1 px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded-full text-xs">
                {schedules.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('bookmarks')}
            className={`flex items-center gap-2 px-4 py-3 font-semibold transition-colors border-b-2 ${
              activeTab === 'bookmarks'
                ? 'border-njit-red text-njit-red dark:text-red-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            <Bookmark size={18} />
            Bookmarks
            {bookmarkedSchedules.length > 0 && (
              <span className="ml-1 px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded-full text-xs">
                {bookmarkedSchedules.length}
              </span>
            )}
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'generated' ? (
          schedules.length > 0 ? (
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
          )
        ) : (
          <>
            {selectedBookmark && <ScheduleView schedule={selectedBookmark.schedule} />}
            <BookmarkedSchedules
              onSelectBookmark={(schedule, index) =>
                setSelectedBookmark({ schedule, index })
              }
              selectedBookmarkIndex={selectedBookmark?.index}
            />
          </>
        )}
      </div>
    </div>
  );
}

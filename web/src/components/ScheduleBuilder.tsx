'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { CourseSelector } from './CourseSelector';
import { AvailabilityEditor } from './AvailabilityEditor';
import { FiltersPanel } from './FiltersPanel';
import { AIScheduleInput } from './AIScheduleInput';
import { EmptyState } from './EmptyState';
import { Notice } from './Notice';
import { ParsedScheduleConstraints, SolveRequest, Schedule } from '@/types';
import { useAppStore } from '@/lib/store';
import { apiUrl } from '@/lib/api';
import { primaryButtonClass } from '@/lib/uiStyles';
import { Calendar, Bookmark } from 'lucide-react';

const ScheduleView = dynamic(() =>
  import('./ScheduleView').then((module) => module.ScheduleView)
);
const ScheduleList = dynamic(() =>
  import('./ScheduleList').then((module) => module.ScheduleList)
);
const BookmarkedSchedules = dynamic(() =>
  import('./BookmarkedSchedules').then((module) => module.BookmarkedSchedules)
);

type Tab = 'generated' | 'bookmarks';

function BuilderStep({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-gray-200 pt-3 first:border-0 first:pt-0 dark:border-gray-700">
      <h3 className="mb-2 text-sm font-bold text-gray-900 dark:text-white">{title}</h3>
      {children}
    </section>
  );
}

export function ScheduleBuilder() {
  const {
    courses,
    selectedCourseKeys,
    courseChoiceGroups,
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
    addCourseChoiceGroup,
    addUnavailableBlock,
    updateFilters,
    minCredits,
    maxCredits,
    setMinCredits,
    setMaxCredits,
  } = useAppStore();

  const [error, setError] = useState<string | null>(null);
  const [noResultsHints, setNoResultsHints] = useState<string[] | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('generated');
  const [selectedBookmark, setSelectedBookmark] = useState<{
    schedule: Schedule;
    index: number;
  } | null>(null);
  const [aiSuccess, setAiSuccess] = useState<string | null>(null);

  const handleAIParsed = (constraints: ParsedScheduleConstraints) => {
    const catalogKeys = new Set(courses.map((course) => course.course_key));
    const existingKeys = new Set(selectedCourseKeys);
    const validCourses = constraints.courses.filter((courseKey) => catalogKeys.has(courseKey));
    const missingCourses = constraints.courses.filter((courseKey) => !catalogKeys.has(courseKey));

    validCourses.forEach((courseKey) => {
      if (!existingKeys.has(courseKey)) addCourse(courseKey);
    });

    constraints.course_groups.forEach((group) => addCourseChoiceGroup(group));

    constraints.unavailable_blocks.forEach((block) => {
      const exists = unavailableBlocks.some(
        (current) =>
          current.day === block.day &&
          current.start_min === block.start_min &&
          current.end_min === block.end_min
      );
      if (!exists) addUnavailableBlock(block);
    });

    setMinCredits(constraints.min_credits ?? undefined);
    setMaxCredits(constraints.max_credits ?? undefined);

    if (constraints.time_preference && constraints.time_preference_strength === 'preferred') {
      updateFilters({ preferred_time: constraints.time_preference });
    } else if (constraints.time_preference === 'morning') {
      updateFilters({ earliest_start: undefined, latest_end: 12 * 60, preferred_time: undefined });
    } else if (constraints.time_preference === 'afternoon') {
      updateFilters({ earliest_start: 12 * 60, latest_end: 17 * 60, preferred_time: undefined });
    } else if (constraints.time_preference === 'evening') {
      updateFilters({ earliest_start: 17 * 60, latest_end: undefined, preferred_time: undefined });
    }

    if (constraints.delivery_preference) {
      if (constraints.delivery_preference_strength === 'preferred') {
        updateFilters({ preferred_delivery: [constraints.delivery_preference] });
      } else {
        updateFilters({
          delivery: [constraints.delivery_preference],
          preferred_delivery: undefined,
        });
      }
    }

    const summary = [
      validCourses.length ? `${validCourses.length} course${validCourses.length === 1 ? '' : 's'}` : '',
      constraints.course_groups.length
        ? `${constraints.course_groups.length} course requirement${constraints.course_groups.length === 1 ? '' : 's'}`
        : '',
      constraints.unavailable_blocks.length
        ? `${constraints.unavailable_blocks.length} time${constraints.unavailable_blocks.length === 1 ? '' : 's'} to avoid`
        : '',
      missingCourses.length ? `${missingCourses.join(', ')} not found` : '',
    ].filter(Boolean);

    setAiSuccess(summary.length ? `Added ${summary.join(' · ')}` : 'Nothing new was found.');
    setTimeout(() => setAiSuccess(null), 5000);
  };

  const handleGenerateSchedules = async () => {
    if (selectedCourseKeys.length === 0 && courseChoiceGroups.length === 0 && requiredCRNs.length === 0) {
      setError('Please select at least one course, requirement, or CRN');
      return;
    }

    if (minCredits != null && maxCredits != null && minCredits > maxCredits) {
      setError('Minimum credits cannot be greater than maximum credits');
      return;
    }

    setIsLoading(true);
    setError(null);
    setNoResultsHints(null);

    const request: SolveRequest = {
      required_course_keys: selectedCourseKeys,
      course_choice_groups: courseChoiceGroups,
      required_crns: requiredCRNs,
      preferred_professors: preferredProfessors,
      min_credits: minCredits,
      max_credits: maxCredits,
      unavailable: unavailableBlocks,
      filters,
      max_results: 50,
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
        const hints: string[] = [];
        if (filters.status?.length === 1 && filters.status[0] === 'Open')
          hints.push('Only "Open" sections are included — try enabling Waitlist in Filters.');
        if (requiredCRNs.length > 0)
          hints.push(`You have ${requiredCRNs.length} pinned section(s) — remove CRN pins to allow more flexibility.`);
        if (courseChoiceGroups.length > 0)
          hints.push('One of your course requirements may not have enough sections matching the current filters.');
        if (unavailableBlocks.length > 3)
          hints.push('You have many availability restrictions — try removing some to open more time slots.');
        hints.push('Remove a few limits and try again.');
        setNoResultsHints(hints);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const selectedCourseCount = new Set([
    ...selectedCourseKeys,
    ...requiredCRNs
      .map((crn) =>
        courses.find((course) => course.sections?.some((section) => section.crn === crn))
          ?.course_key
      )
      .filter((courseKey): courseKey is string => Boolean(courseKey)),
  ]).size + courseChoiceGroups.reduce((total, group) => total + group.choose, 0);

  return (
    <div className="grid grid-cols-1 overflow-hidden bg-white lg:h-full lg:grid-cols-[380px_minmax(0,1fr)] dark:bg-gray-800 xl:grid-cols-[420px_minmax(0,1fr)]">
      <div className="flex min-h-0 flex-col border-b border-gray-200 lg:h-full lg:border-b-0 lg:border-r dark:border-gray-700">
        <div className="workspace-scrollbar workspace-scrollbar-left flex-1 py-3 pl-5 pr-3 lg:overflow-y-auto">
          <h2 className="mb-3 text-lg font-bold text-gray-900 dark:text-white">
            Schedule setup
          </h2>

          <div className="space-y-3">
            <AIScheduleInput onConstraintsParsed={handleAIParsed} />

            {aiSuccess && (
              <Notice tone="success">{aiSuccess}</Notice>
            )}

            <BuilderStep title="Courses">
              <CourseSelector />
            </BuilderStep>

            <BuilderStep title="Times to avoid">
              <AvailabilityEditor />
            </BuilderStep>

            <BuilderStep title="Options">
              <FiltersPanel />
            </BuilderStep>

            {error && (
              <Notice tone="error">{error}</Notice>
            )}

            {noResultsHints && schedules.length === 0 && (
              <Notice tone="warning">
                <p className="mb-1 font-semibold">No schedules found</p>
                <ul className="space-y-1 text-xs">
                  {noResultsHints.map((hint, i) => (
                    <li key={i}>• {hint}</li>
                  ))}
                </ul>
              </Notice>
            )}
          </div>
        </div>
        <div className="shrink-0 border-t border-gray-200 bg-white py-2 pl-5 pr-3 dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-1.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
            <span>{selectedCourseCount} {selectedCourseCount === 1 ? 'course' : 'courses'}</span>
            <span>
              {unavailableBlocks.length} {unavailableBlocks.length === 1 ? 'time' : 'times'} to avoid
            </span>
          </div>
          <button
            onClick={handleGenerateSchedules}
            disabled={
              isLoading ||
              (selectedCourseKeys.length === 0 &&
                courseChoiceGroups.length === 0 &&
                requiredCRNs.length === 0)
            }
            className={`w-full px-4 py-2.5 text-sm font-bold ${primaryButtonClass}`}
          >
            {isLoading ? 'Finding schedules…' : 'Show schedules'}
          </button>
        </div>
      </div>

      <div className="min-w-0 bg-gray-50 lg:flex lg:h-full lg:min-h-0 lg:flex-col dark:bg-gray-900/40">
        <div className="flex shrink-0 gap-1 border-b border-gray-200 bg-white px-2 dark:border-gray-700 dark:bg-gray-800">
          <button
            onClick={() => setActiveTab('generated')}
            className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-semibold transition-colors touch-manipulation ${
              activeTab === 'generated'
                ? 'border-njit-red text-njit-red dark:text-red-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            <Calendar size={16} />
            Schedules
            {schedules.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded-full text-xs">
                {schedules.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('bookmarks')}
            className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-semibold transition-colors touch-manipulation ${
              activeTab === 'bookmarks'
                ? 'border-njit-red text-njit-red dark:text-red-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            <Bookmark size={16} />
            Saved
            {bookmarkedSchedules.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded-full text-xs">
                {bookmarkedSchedules.length}
              </span>
            )}
          </button>
        </div>

        <div className="workspace-scrollbar min-h-0 flex-1 space-y-2 overflow-y-auto p-2">
          {activeTab === 'generated' ? (
            schedules.length > 0 ? (
              <>
                <ScheduleView />
                <ScheduleList />
              </>
            ) : (
              <EmptyState
                icon={Calendar}
                title="No schedules yet"
                description="Add at least one course, then choose Show schedules."
              />
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
    </div>
  );
}

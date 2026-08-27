'use client';

import { useEffect, useMemo, useState } from 'react';
import { CalendarDays, Clock3, UsersRound } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import {
  classDays,
  earliestStart,
  formatGap,
  instructorNames,
  latestEnd,
  totalGapMinutes,
} from '@/lib/scheduleMetrics';
import { minutesToTime } from '@/types';
import { fieldControlClass, panelClass } from '@/lib/uiStyles';
import { getClosedOfferings } from '@/lib/sectionAvailability';
import { SectionStatusBadge } from './SectionStatusBadge';

type SortMode = 'score' | 'earliest' | 'latest' | 'gaps' | 'days';

export function ScheduleList() {
  const { schedules, selectedScheduleIndex, setSelectedScheduleIndex } = useAppStore();
  const [sortMode, setSortMode] = useState<SortMode>('score');
  const [visibleCount, setVisibleCount] = useState(20);

  useEffect(() => setVisibleCount(20), [schedules, sortMode]);

  const sortedSchedules = useMemo(() => {
    const items = schedules.map((schedule, originalIndex) => ({
      schedule,
      originalIndex,
      days: classDays(schedule),
      professors: instructorNames(schedule),
      start: earliestStart(schedule),
      end: latestEnd(schedule),
      gaps: totalGapMinutes(schedule),
      closedCount: getClosedOfferings(schedule).length,
    }));
    return items.sort((left, right) => {
      if (sortMode === 'earliest') return left.start - right.start;
      if (sortMode === 'latest') return right.start - left.start;
      if (sortMode === 'gaps') return left.gaps - right.gaps;
      if (sortMode === 'days') return left.days.length - right.days.length;
      return left.schedule.score - right.schedule.score;
    });
  }, [schedules, sortMode]);

  if (schedules.length === 0) return null;

  return (
    <div className={`${panelClass} p-3`}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <h3 className="text-sm font-bold text-gray-900 dark:text-white">Other schedules</h3>
        <select
          value={sortMode}
          onChange={(event) => setSortMode(event.target.value as SortMode)}
          aria-label="Sort schedules"
          className={`max-w-[155px] px-2 py-1.5 text-xs sm:max-w-none ${fieldControlClass}`}
        >
          <option value="score">Recommended</option>
          <option value="earliest">Starts earliest</option>
          <option value="latest">Starts latest</option>
          <option value="gaps">Shortest breaks</option>
          <option value="days">Fewest days</option>
        </select>
      </div>

      <div className="grid max-h-[32rem] grid-cols-1 gap-2 overflow-y-auto pr-1 xl:grid-cols-2">
        {sortedSchedules.slice(0, visibleCount).map((item) => {
          const { schedule, originalIndex, days, professors, start, end, gaps, closedCount } = item;
          const selected = originalIndex === selectedScheduleIndex;

          return (
            <button
              key={originalIndex}
              type="button"
              onClick={() => setSelectedScheduleIndex(originalIndex)}
              className={`rounded-md border p-2 text-left transition ${
                selected
                  ? 'border-gray-500 bg-gray-50 dark:border-gray-400 dark:bg-gray-700'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700'
              }`}
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-sm font-bold text-gray-900 dark:text-white">
                  Schedule {originalIndex + 1}
                </span>
                <span className="flex items-center gap-1">
                  {closedCount > 0 && <SectionStatusBadge status="Closed" compact />}
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                    {schedule.total_credits} credits
                  </span>
                </span>
              </div>

              <div className="space-y-1 text-xs text-gray-600 dark:text-gray-300">
                <div className="flex items-center gap-2">
                  <CalendarDays size={14} className="shrink-0 text-gray-400" />
                  <span>{days.length ? days.join(' · ') : 'No fixed class days'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock3 size={14} className="shrink-0 text-gray-400" />
                  <span>
                    {Number.isFinite(start) ? `${minutesToTime(start)} to ${minutesToTime(end)}` : 'No fixed meeting time'}
                    {' · '}{formatGap(gaps)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <UsersRound size={14} className="shrink-0 text-gray-400" />
                  <span className="truncate">{professors.length ? professors.join(', ') : 'Instructor TBA'}</span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
      {visibleCount < sortedSchedules.length && (
        <button
          type="button"
          onClick={() => setVisibleCount((count) => count + 20)}
          className="mt-2 w-full rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
        >
          Show {Math.min(20, sortedSchedules.length - visibleCount)} more
        </button>
      )}
    </div>
  );
}

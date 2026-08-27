'use client';

import { useState } from 'react';
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

  if (schedules.length === 0) return null;

  const sortedSchedules = [...schedules].sort((a, b) => {
    if (sortMode === 'earliest') return earliestStart(a) - earliestStart(b);
    if (sortMode === 'latest') return earliestStart(b) - earliestStart(a);
    if (sortMode === 'gaps') return totalGapMinutes(a) - totalGapMinutes(b);
    if (sortMode === 'days') return classDays(a).length - classDays(b).length;
    return a.score - b.score;
  });

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
        {sortedSchedules.map((schedule) => {
          const originalIndex = schedules.indexOf(schedule);
          const selected = originalIndex === selectedScheduleIndex;
          const days = classDays(schedule);
          const professors = instructorNames(schedule);
          const start = earliestStart(schedule);
          const end = latestEnd(schedule);
          const closedCount = getClosedOfferings(schedule).length;

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
                    {' · '}{formatGap(totalGapMinutes(schedule))}
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
    </div>
  );
}

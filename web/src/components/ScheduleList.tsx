'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { Schedule } from '@/types';

type SortMode = 'score' | 'earliest' | 'latest' | 'gaps' | 'days';

function totalGapMinutes(schedule: Schedule): number {
  let gaps = 0;
  const byDay: Record<string, number[]> = {};
  schedule.offerings.forEach((o) =>
    o.meetings.forEach((m) => {
      (byDay[m.day] ??= []).push(m.start_min, m.end_min);
    })
  );
  Object.values(byDay).forEach((times) => {
    const sorted = [...times].sort((a, b) => a - b);
    for (let i = 2; i < sorted.length; i += 2)
      gaps += Math.max(0, sorted[i] - sorted[i - 1]);
  });
  return gaps;
}

function earliestStart(schedule: Schedule): number {
  const starts = schedule.offerings.flatMap((o) => o.meetings.map((m) => m.start_min));
  return starts.length ? Math.min(...starts) : Infinity;
}

function latestStart(schedule: Schedule): number {
  const starts = schedule.offerings.flatMap((o) => o.meetings.map((m) => m.start_min));
  return starts.length ? Math.min(...starts) : 0;
}

function daysOnCampus(schedule: Schedule): number {
  const days = new Set(
    schedule.offerings
      .flatMap((o) => o.meetings.map((m) => m.day))
      .filter(Boolean)
  );
  return days.size;
}

export function ScheduleList() {
  const { schedules, selectedScheduleIndex, setSelectedScheduleIndex } = useAppStore();
  const [sortMode, setSortMode] = useState<SortMode>('score');

  if (schedules.length === 0) return null;

  const sortedSchedules = [...schedules].sort((a, b) => {
    if (sortMode === 'earliest') return earliestStart(a) - earliestStart(b);
    if (sortMode === 'latest') return latestStart(b) - latestStart(a);
    if (sortMode === 'gaps') return totalGapMinutes(a) - totalGapMinutes(b);
    if (sortMode === 'days') return daysOnCampus(a) - daysOnCampus(b);
    return a.score - b.score; // 'score' default
  });

  // Map sorted index back to original index for selection highlighting
  const originalIndex = (sortedIdx: number) =>
    schedules.indexOf(sortedSchedules[sortedIdx]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-800 dark:text-white">
          All Schedules ({schedules.length})
        </h3>
        <select
          value={sortMode}
          onChange={(e) => setSortMode(e.target.value as SortMode)}
          className="text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg px-2 py-1"
        >
          <option value="score">Best Score</option>
          <option value="earliest">Earliest Start</option>
          <option value="latest">Latest Start</option>
          <option value="gaps">Fewest Gaps</option>
          <option value="days">Fewest Days on Campus</option>
        </select>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {sortedSchedules.map((schedule, sortedIdx) => {
          const origIdx = originalIndex(sortedIdx);
          const isSelected = origIdx === selectedScheduleIndex;
          const courseList = schedule.offerings.map((o) => o.course_key).join(', ');

          return (
            <button
              key={origIdx}
              onClick={() => setSelectedScheduleIndex(origIdx)}
              className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                isSelected
                  ? 'border-njit-red bg-red-50 dark:bg-njit-navy/50'
                  : 'border-njit-gray dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-sm">Schedule {origIdx + 1}</span>
                <span className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">
                  {schedule.total_credits} cr
                </span>
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 truncate">
                {courseList}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { Schedule } from '@/types';
import { Trash2, Bookmark } from 'lucide-react';
import { EmptyState } from './EmptyState';
import { iconButtonClass, panelClass, secondaryButtonClass } from '@/lib/uiStyles';
import { getClosedOfferings } from '@/lib/sectionAvailability';
import { SectionStatusBadge } from './SectionStatusBadge';

interface BookmarkedSchedulesProps {
  onSelectBookmark: (schedule: Schedule, index: number) => void;
  selectedBookmarkIndex?: number;
}

export function BookmarkedSchedules({
  onSelectBookmark,
  selectedBookmarkIndex
}: BookmarkedSchedulesProps) {
  const { bookmarkedSchedules, removeBookmark } = useAppStore();
  const [pendingRemoval, setPendingRemoval] = useState<number | null>(null);

  if (bookmarkedSchedules.length === 0) {
    return (
      <EmptyState
        icon={Bookmark}
        title="No saved schedules"
        description="Generate a schedule, then select Save to keep it here."
      />
    );
  }

  return (
    <div className={`${panelClass} p-3`}>
      <h3 className="mb-2 text-sm font-bold text-gray-900 dark:text-white">
        Saved schedules ({bookmarkedSchedules.length})
      </h3>

      <div className="space-y-2">
        {bookmarkedSchedules.map((schedule, index) => {
          const isSelected = index === selectedBookmarkIndex;
          const courseList = schedule.offerings
            .map((o) => o.course_key)
            .join(', ');
          const closedCount = getClosedOfferings(schedule).length;

          return (
            <div
              key={index}
              className={`rounded-md border p-2 transition-colors ${
                isSelected
                  ? 'border-gray-500 bg-gray-50 dark:border-gray-400 dark:bg-gray-700'
                  : 'border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <button
                  onClick={() => onSelectBookmark(schedule, index)}
                  className="flex-1 text-left"
                >
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-sm font-semibold">
                      Saved schedule {index + 1}
                    </span>
                    <span className="flex items-center gap-1">
                      {closedCount > 0 && <SectionStatusBadge status="Closed" compact />}
                      <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                        {schedule.total_credits} credits
                      </span>
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 truncate">
                    {courseList}
                  </div>
                </button>
                {pendingRemoval === index ? (
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setPendingRemoval(null)}
                      className={`px-2 py-1 text-xs ${secondaryButtonClass}`}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        removeBookmark(index);
                        setPendingRemoval(null);
                      }}
                      className="rounded-md border border-red-300 px-2 py-1 text-xs font-medium text-red-700 transition-colors hover:bg-red-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950/40"
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setPendingRemoval(index)}
                    className={iconButtonClass}
                    title="Remove saved schedule"
                    aria-label={`Remove saved schedule ${index + 1}`}
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

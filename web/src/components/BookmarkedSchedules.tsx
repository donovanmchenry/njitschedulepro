'use client';

import { useAppStore } from '@/lib/store';
import { Schedule } from '@/types';
import { Trash2, Calendar } from 'lucide-react';

interface BookmarkedSchedulesProps {
  onSelectBookmark: (schedule: Schedule, index: number) => void;
  selectedBookmarkIndex?: number;
}

export function BookmarkedSchedules({
  onSelectBookmark,
  selectedBookmarkIndex
}: BookmarkedSchedulesProps) {
  const { bookmarkedSchedules, removeBookmark } = useAppStore();

  if (bookmarkedSchedules.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
        <div className="text-gray-400 dark:text-gray-500">
          <Calendar className="mx-auto h-16 w-16 mb-4" />
          <p className="text-lg font-semibold mb-2">No Bookmarked Schedules</p>
          <p className="text-sm">
            Generate schedules and click the bookmark button to save them here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h3 className="text-lg font-bold mb-4 text-gray-800 dark:text-white">
        Saved Schedules ({bookmarkedSchedules.length})
      </h3>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {bookmarkedSchedules.map((schedule, index) => {
          const isSelected = index === selectedBookmarkIndex;
          const courseList = schedule.offerings
            .map((o) => o.course_key)
            .join(', ');

          return (
            <div
              key={index}
              className={`p-3 rounded-lg border-2 transition-colors ${
                isSelected
                  ? 'border-njit-red bg-red-50 dark:bg-njit-navy/50'
                  : 'border-njit-gray dark:border-gray-700'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <button
                  onClick={() => onSelectBookmark(schedule, index)}
                  className="flex-1 text-left"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-sm">
                      Saved Schedule {index + 1}
                    </span>
                    <span className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">
                      {schedule.total_credits} cr
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 truncate">
                    {courseList}
                  </div>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Remove this bookmarked schedule?')) {
                      removeBookmark(index);
                    }
                  }}
                  className="flex-shrink-0 p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                  title="Remove bookmark"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

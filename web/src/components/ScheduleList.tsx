'use client';

import { useAppStore } from '@/lib/store';

export function ScheduleList() {
  const { schedules, selectedScheduleIndex, setSelectedScheduleIndex } = useAppStore();

  if (schedules.length === 0) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h3 className="text-lg font-bold mb-4 text-gray-800 dark:text-white">
        All Schedules ({schedules.length})
      </h3>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {schedules.map((schedule, index) => {
          const isSelected = index === selectedScheduleIndex;
          const courseList = schedule.offerings
            .map((o) => o.course_key)
            .join(', ');

          return (
            <button
              key={index}
              onClick={() => setSelectedScheduleIndex(index)}
              className={`w-full text-left p-3 rounded-lg border-2 transition-colors ${
                isSelected
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900'
                  : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-sm">Schedule {index + 1}</span>
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

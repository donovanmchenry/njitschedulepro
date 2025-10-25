'use client';

import { useAppStore } from '@/lib/store';
import { DAYS, DAY_NAMES, minutesToTime } from '@/types';
import { Download, BookmarkPlus } from 'lucide-react';
import { apiUrl } from '@/lib/api';

const COLORS = [
  'bg-blue-200 border-blue-400 text-blue-900',
  'bg-green-200 border-green-400 text-green-900',
  'bg-purple-200 border-purple-400 text-purple-900',
  'bg-yellow-200 border-yellow-400 text-yellow-900',
  'bg-pink-200 border-pink-400 text-pink-900',
  'bg-indigo-200 border-indigo-400 text-indigo-900',
  'bg-red-200 border-red-400 text-red-900',
  'bg-teal-200 border-teal-400 text-teal-900',
];

export function ScheduleView() {
  const { schedules, selectedScheduleIndex, addBookmark } = useAppStore();
  const schedule = schedules[selectedScheduleIndex];

  if (!schedule) return null;

  // Create color map for courses
  const courseColorMap = new Map<string, string>();
  let colorIndex = 0;
  schedule.offerings.forEach((offering) => {
    if (!courseColorMap.has(offering.course_key)) {
      courseColorMap.set(offering.course_key, COLORS[colorIndex % COLORS.length]);
      colorIndex++;
    }
  });

  // Find earliest and latest times across all meetings
  let earliestTime = 8 * 60; // 8 AM
  let latestTime = 18 * 60; // 6 PM

  schedule.offerings.forEach((offering) => {
    offering.meetings.forEach((meeting) => {
      earliestTime = Math.min(earliestTime, meeting.start_min);
      latestTime = Math.max(latestTime, meeting.end_min);
    });
  });

  // Round to hour boundaries
  earliestTime = Math.floor(earliestTime / 60) * 60;
  latestTime = Math.ceil(latestTime / 60) * 60;

  const timeSlots: number[] = [];
  for (let time = earliestTime; time <= latestTime; time += 60) {
    timeSlots.push(time);
  }

  const handleDownloadICS = async () => {
    try {
      const response = await fetch(apiUrl('/export/ics'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(schedule),
      });

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'njit_schedule.ics';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download ICS:', error);
    }
  };

  const handleDownloadCSV = async () => {
    try {
      const response = await fetch(apiUrl('/export/csv'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(schedule),
      });

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'njit_schedule.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download CSV:', error);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
            Schedule {selectedScheduleIndex + 1}
          </h2>
          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 mt-1">
            <span>{schedule.total_credits} credits</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => addBookmark(schedule)}
            className="flex items-center gap-2 px-3 py-2 bg-njit-navy/10 hover:bg-njit-navy/20 text-njit-navy dark:bg-njit-gray/20 dark:text-njit-gray rounded-lg text-sm transition-colors"
          >
            <BookmarkPlus size={16} />
            Bookmark
          </button>
          <button
            onClick={handleDownloadICS}
            className="flex items-center gap-2 px-3 py-2 bg-njit-red/10 hover:bg-njit-red/20 text-njit-red dark:bg-njit-red/30 dark:text-red-300 rounded-lg text-sm transition-colors"
          >
            <Download size={16} />
            ICS
          </button>
          <button
            onClick={handleDownloadCSV}
            className="flex items-center gap-2 px-3 py-2 bg-njit-gray/30 hover:bg-njit-gray/50 text-gray-700 dark:bg-gray-700 dark:text-njit-gray rounded-lg text-sm transition-colors"
          >
            <Download size={16} />
            CSV
          </button>
        </div>
      </div>

      {/* Calendar grid */}
      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          <div className="grid grid-cols-6 gap-2">
            {/* Time column header */}
            <div className="font-semibold text-sm text-gray-600 dark:text-gray-400 py-2">
              Time
            </div>
            {/* Day headers */}
            {DAYS.map((day) => (
              <div
                key={day}
                className="font-semibold text-sm text-center text-gray-600 dark:text-gray-400 py-2"
              >
                {DAY_NAMES[day]}
              </div>
            ))}

            {/* Time slots */}
            {timeSlots.map((time) => (
              <div key={time} className="contents">
                {/* Time label */}
                <div className="text-xs text-gray-500 py-1 pr-2 text-right">
                  {minutesToTime(time)}
                </div>

                {/* Day columns */}
                {DAYS.map((day) => {
                  // Find meetings for this day and time slot
                  const meetings = schedule.offerings.flatMap((offering) =>
                    offering.meetings
                      .filter(
                        (m) =>
                          m.day === day && m.start_min < time + 60 && m.end_min > time
                      )
                      .map((m) => ({ offering, meeting: m }))
                  );

                  return (
                    <div
                      key={day}
                      className="border border-gray-200 dark:border-gray-700 min-h-[60px] p-1 relative"
                    >
                      {meetings.map(({ offering, meeting }) => {
                        // Only render on the first slot
                        if (meeting.start_min >= time && meeting.start_min < time + 60) {
                          const duration = meeting.end_min - meeting.start_min;
                          const height = Math.max((duration / 60) * 60, 40);
                          const color = courseColorMap.get(offering.course_key);

                          return (
                            <div
                              key={offering.crn}
                              className={`${color} border-2 rounded p-2 mb-1 text-xs overflow-hidden`}
                              style={{ minHeight: `${height}px` }}
                              title={`${offering.course_key} - ${offering.title}\n${offering.instructor || 'TBA'}\n${meeting.location || 'TBA'}`}
                            >
                              <div className="font-bold">{offering.course_key}</div>
                              <div className="text-xs truncate">{offering.section}</div>
                              {offering.instructor && offering.instructor !== 'nan' && (
                                <div className="text-xs truncate font-medium">
                                  {offering.instructor}
                                </div>
                              )}
                              <div className="text-xs">
                                {minutesToTime(meeting.start_min)}-
                                {minutesToTime(meeting.end_min)}
                              </div>
                              {meeting.location && (
                                <div className="text-xs truncate">{meeting.location}</div>
                              )}
                            </div>
                          );
                        }
                        return null;
                      })}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}

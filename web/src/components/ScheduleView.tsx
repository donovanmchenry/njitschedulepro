'use client';

import { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { DAYS, DAY_NAMES, minutesToTime } from '@/types';
import { Download, Bookmark, BookmarkPlus, Share2, Check } from 'lucide-react';
import { apiUrl } from '@/lib/api';

interface RmpRating {
  avg_rating: number;
  num_ratings: number;
  url: string;
}

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

interface ScheduleViewProps {
  schedule?: import('@/types').Schedule;
}

export function ScheduleView({ schedule: propSchedule }: ScheduleViewProps = {}) {
  const { schedules, selectedScheduleIndex, addBookmark, removeBookmark, bookmarkedSchedules } = useAppStore();
  const schedule = propSchedule || schedules[selectedScheduleIndex];

  const [rmpRatings, setRmpRatings] = useState<Record<string, RmpRating | null>>({});
  const [prereqs, setPrereqs] = useState<Record<string, string | null>>({});
  const [shareCopied, setShareCopied] = useState(false);

  useEffect(() => {
    if (!schedule) return;
    const names = [...new Set(
      schedule.offerings.map((o) => o.instructor).filter((n): n is string => !!n && n !== 'nan')
    )];
    if (!names.length) return;
    fetch(apiUrl('/professors/ratings'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ names }),
    })
      .then((r) => (r.ok ? r.json() : {}))
      .then(setRmpRatings)
      .catch(() => {});
  }, [schedule]);

  // Fetch prerequisites for each unique course in the schedule
  useEffect(() => {
    if (!schedule) return;
    const courseKeys = [...new Set(schedule.offerings.map((o) => o.course_key))];
    courseKeys.forEach((key) => {
      fetch(apiUrl(`/catalog/prerequisites/${encodeURIComponent(key)}`))
        .then((r) => (r.ok ? r.json() : { prerequisites: null }))
        .then((data) => {
          setPrereqs((prev) => ({ ...prev, [key]: data.prerequisites ?? null }));
        })
        .catch(() => {});
    });
  }, [schedule]);

  const handleShare = async () => {
    if (!schedule) return;
    try {
      const resp = await fetch(apiUrl('/share'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(schedule),
      });
      if (!resp.ok) return;
      const { id } = await resp.json();
      const url = `${window.location.origin}${window.location.pathname}?share=${id}`;
      await navigator.clipboard.writeText(url);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2500);
    } catch {
      // clipboard not available – silently ignore
    }
  };

  if (!schedule) return null;

  const crns = schedule.offerings.map((o) => o.crn).sort().join(',');
  const bookmarkIndex = bookmarkedSchedules.findIndex(
    (b) => b.offerings.map((o) => o.crn).sort().join(',') === crns
  );
  const isBookmarked = bookmarkIndex !== -1;

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

  const isBookmarkedView = !!propSchedule;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
            {isBookmarkedView ? 'Saved Schedule' : `Schedule ${selectedScheduleIndex + 1}`}
          </h2>
          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 mt-1">
            <span>{schedule.total_credits} credits</span>
          </div>
        </div>
        <div className="flex gap-2">
          {!isBookmarkedView && (
            <button
              onClick={() => isBookmarked ? removeBookmark(bookmarkIndex) : addBookmark(schedule)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                isBookmarked
                  ? 'bg-njit-navy hover:bg-njit-navy/80 text-white dark:bg-blue-600 dark:hover:bg-blue-700'
                  : 'bg-njit-navy/10 hover:bg-njit-navy/20 text-njit-navy dark:bg-njit-gray/20 dark:text-njit-gray'
              }`}
            >
              {isBookmarked ? <Bookmark size={16} fill="currentColor" /> : <BookmarkPlus size={16} />}
              {isBookmarked ? 'Saved' : 'Bookmark'}
            </button>
          )}
          {!isBookmarkedView && (
            <button
              onClick={handleShare}
              className="flex items-center gap-2 px-3 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 rounded-lg text-sm transition-colors"
            >
              {shareCopied ? <Check size={16} /> : <Share2 size={16} />}
              {shareCopied ? 'Copied!' : 'Share'}
            </button>
          )}
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
            {timeSlots.map((time, timeIndex) => (
              <div key={time} className="contents">
                {/* Time label */}
                <div className="text-xs text-gray-500 py-1 pr-2 text-right">
                  {minutesToTime(time)}
                </div>

                {/* Day columns */}
                {DAYS.map((day) => {
                  return (
                    <div
                      key={day}
                      className="border border-gray-200 dark:border-gray-700 min-h-[60px] relative"
                      style={{ height: '60px' }}
                    >
                      {/* Only render courses in the first time slot (to avoid duplicates) */}
                      {timeIndex === 0 && schedule.offerings.flatMap((offering) =>
                        offering.meetings
                          .filter((m) => m.day === day)
                          .map((meeting) => {
                            const color = courseColorMap.get(offering.course_key);

                            // Calculate position relative to earliest time
                            const topOffset = (meeting.start_min - earliestTime);
                            const duration = meeting.end_min - meeting.start_min;
                            const height = Math.max(duration, 40); // minimum 40 minutes

                            return (
                              <div
                                key={offering.crn}
                                className={`${color} border-2 rounded p-2 text-xs overflow-hidden absolute left-1 right-1`}
                                style={{
                                  top: `${topOffset}px`,
                                  height: `${height}px`,
                                  zIndex: 10
                                }}
                                title={[
                                  `${offering.course_key} - ${offering.title}`,
                                  offering.instructor || 'TBA',
                                  meeting.location || 'TBA',
                                  prereqs[offering.course_key]
                                    ? `Prerequisites: ${prereqs[offering.course_key]}`
                                    : null,
                                ].filter(Boolean).join('\n')}
                              >
                                <div className="font-bold">{offering.course_key}</div>
                                <div className="text-xs truncate">{offering.section}</div>
                                {offering.instructor && offering.instructor !== 'nan' && (
                                  <div className="text-xs font-medium flex items-center gap-1 flex-wrap">
                                    <span className="truncate">{offering.instructor}</span>
                                    {rmpRatings[offering.instructor] && (
                                      <a
                                        href={rmpRatings[offering.instructor]!.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        onClick={(e) => e.stopPropagation()}
                                        className="font-semibold hover:underline shrink-0 opacity-80"
                                      >
                                        ★ {rmpRatings[offering.instructor]!.avg_rating.toFixed(1)}
                                      </a>
                                    )}
                                  </div>
                                )}
                                <div className="text-xs">
                                  {minutesToTime(meeting.start_min)}-
                                  {minutesToTime(meeting.end_min)}
                                </div>
                                {meeting.location && (
                                  <div className="text-xs truncate">{meeting.location}</div>
                                )}
                                {prereqs[offering.course_key] && (
                                  <div className="text-xs truncate opacity-75 italic">
                                    Prereq: {prereqs[offering.course_key]}
                                  </div>
                                )}
                              </div>
                            );
                          })
                      )}
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

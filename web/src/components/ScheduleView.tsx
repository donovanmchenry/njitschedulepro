'use client';

import { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { DAYS, DAY_NAMES, DayOfWeek, minutesToTime } from '@/types';
import { Download, Bookmark, BookmarkPlus, Share2, Check } from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { panelClass, secondaryButtonClass, selectedControlClass, unselectedControlClass } from '@/lib/uiStyles';
import { getClosedOfferings, isClosedStatus } from '@/lib/sectionAvailability';
import { Notice } from './Notice';
import { SectionStatusBadge } from './SectionStatusBadge';

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
  const [mobileDay, setMobileDay] = useState<DayOfWeek>('Mon');

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

  useEffect(() => {
    if (!schedule) return;
    const availableDays = DAYS.filter((day) =>
      schedule.offerings.some((offering) =>
        offering.meetings.some((meeting) => meeting.day === day)
      )
    );
    setMobileDay((current) =>
      availableDays.includes(current) ? current : (availableDays[0] || 'Mon')
    );
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

  const meetings = schedule.offerings.flatMap((offering) => offering.meetings);
  const desktopDays = DAYS.filter(
    (day) =>
      (day !== 'Sat' && day !== 'Sun') ||
      meetings.some((meeting) => meeting.day === day)
  );
  let earliestTime = meetings.length
    ? Math.min(...meetings.map((meeting) => meeting.start_min))
    : 8 * 60;
  let latestTime = meetings.length
    ? Math.max(...meetings.map((meeting) => meeting.end_min))
    : 18 * 60;

  // Round to hour boundaries
  earliestTime = Math.floor(earliestTime / 60) * 60;
  latestTime = Math.ceil(latestTime / 60) * 60;
  latestTime = Math.max(latestTime, earliestTime + 2 * 60);

  const timeSlots: number[] = [];
  for (let time = earliestTime; time <= latestTime; time += 60) {
    timeSlots.push(time);
  }

  const triggerDownload = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => window.URL.revokeObjectURL(url), 100);
  };

  const handleDownloadICS = async () => {
    try {
      const response = await fetch(apiUrl('/export/ics'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(schedule),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const blob = await response.blob();
      triggerDownload(blob, 'njit_schedule.ics');
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
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const blob = await response.blob();
      triggerDownload(blob, 'njit_schedule.csv');
    } catch (error) {
      console.error('Failed to download CSV:', error);
    }
  };

  const isBookmarkedView = !!propSchedule;
  const closedOfferings = getClosedOfferings(schedule);

  return (
    <div className={`${panelClass} p-3`}>
      {/* Header */}
      <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-800 dark:text-white">
            {isBookmarkedView ? 'Saved schedule' : `Schedule ${selectedScheduleIndex + 1}`}
          </h2>
          <div className="mt-0.5 flex items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
            <span>{schedule.total_credits} credits</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {!isBookmarkedView && (
            <button
              onClick={() => isBookmarked ? removeBookmark(bookmarkIndex) : addBookmark(schedule)}
              className={`gap-1.5 px-2 py-1.5 text-xs ${secondaryButtonClass}`}
            >
              {isBookmarked ? <Bookmark size={16} fill="currentColor" /> : <BookmarkPlus size={16} />}
              {isBookmarked ? 'Saved' : 'Save'}
            </button>
          )}
          {!isBookmarkedView && (
            <button
              onClick={handleShare}
              className={`gap-1.5 px-2 py-1.5 text-xs ${secondaryButtonClass}`}
            >
              {shareCopied ? <Check size={16} /> : <Share2 size={16} />}
              {shareCopied ? 'Copied!' : 'Share'}
            </button>
          )}
          <button
            onClick={handleDownloadICS}
            className={`gap-1.5 px-2 py-1.5 text-xs ${secondaryButtonClass}`}
          >
            <Download size={16} />
            Calendar
          </button>
          <button
            onClick={handleDownloadCSV}
            className={`gap-1.5 px-2 py-1.5 text-xs ${secondaryButtonClass}`}
          >
            <Download size={16} />
            Spreadsheet
          </button>
        </div>
      </div>

      {closedOfferings.length > 0 && (
        <Notice tone="error" className="mb-2 text-xs">
          <span className="font-semibold">Unavailable:</span>{' '}
          {closedOfferings.map((offering) => `${offering.course_key} §${offering.section}`).join(', ')}
          {closedOfferings.length === 1 ? ' is closed.' : ' are closed.'}
        </Notice>
      )}

      {/* Mobile: Day tabs + list view */}
      <div className="sm:hidden">
        {/* Day selector */}
        <div className="flex gap-1 mb-3">
          {DAYS.map((day) => {
            const hasClasses = schedule.offerings.some((o) => o.meetings.some((m) => m.day === day));
            if (!hasClasses) return null;
            return (
              <button
                key={day}
                onClick={() => setMobileDay(day)}
                className={`flex-1 rounded-md border py-2 text-sm font-semibold touch-manipulation transition-colors ${
                  mobileDay === day
                    ? selectedControlClass
                    : unselectedControlClass
                }`}
              >
                {({'Mon':'M','Tue':'T','Wed':'W','Thu':'R','Fri':'F','Sat':'S','Sun':'U'} as Record<string,string>)[day]}
              </button>
            );
          })}
        </div>
        {/* Classes for selected day */}
        <div className="space-y-2">
          {schedule.offerings
            .filter((o) => o.meetings.some((m) => m.day === mobileDay))
            .sort((a, b) => {
              const aMin = Math.min(...a.meetings.filter((m) => m.day === mobileDay).map((m) => m.start_min));
              const bMin = Math.min(...b.meetings.filter((m) => m.day === mobileDay).map((m) => m.start_min));
              return aMin - bMin;
            })
            .map((offering) => {
              const color = courseColorMap.get(offering.course_key) || COLORS[0];
              const dayMeetings = offering.meetings.filter((m) => m.day === mobileDay);
              return (
                <div
                  key={offering.crn}
                  className={`${color} rounded-lg border-2 p-3 ${
                    isClosedStatus(offering.status) ? 'ring-2 ring-inset ring-red-500' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <div className="text-sm font-bold">{offering.course_key}</div>
                      <SectionStatusBadge status={offering.status} compact />
                    </div>
                    <div className="text-xs font-mono shrink-0 text-right">
                      <div>§{offering.section}</div>
                      <div className="opacity-75">CRN {offering.crn}</div>
                    </div>
                  </div>
                  {offering.instructor && offering.instructor !== 'nan' && (
                    <div className="text-xs mt-1 flex items-center gap-1 flex-wrap">
                      <span>{offering.instructor}</span>
                      {rmpRatings[offering.instructor] && (
                        <a
                          href={rmpRatings[offering.instructor]!.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="font-semibold hover:underline opacity-80"
                        >
                          ★ {rmpRatings[offering.instructor]!.avg_rating.toFixed(1)}
                        </a>
                      )}
                    </div>
                  )}
                  {dayMeetings.map((m, i) => (
                    <div key={i} className="text-xs mt-1">
                      {minutesToTime(m.start_min)}–{minutesToTime(m.end_min)}
                      {m.location && <span className="ml-2 opacity-75">{m.location}</span>}
                    </div>
                  ))}
                </div>
              );
            })}
          {schedule.offerings.every((o) => !o.meetings.some((m) => m.day === mobileDay)) && (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic text-center py-4">
              No classes on {DAY_NAMES[mobileDay]}
            </p>
          )}
        </div>
      </div>

      {/* Desktop: Calendar grid */}
      <div className="workspace-scrollbar hidden overflow-x-auto sm:block">
        <div className="inline-block min-w-[640px] w-full">
          <div
            className="grid gap-1"
            style={{ gridTemplateColumns: `68px repeat(${desktopDays.length}, minmax(104px, 1fr))` }}
          >
            {/* Time column header */}
            <div className="font-semibold text-sm text-gray-600 dark:text-gray-400 py-2">
              Time
            </div>
            {/* Day headers */}
            {desktopDays.map((day) => (
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
                {desktopDays.map((day) => {
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
                                className={`${color} absolute left-0.5 right-0.5 overflow-hidden rounded border p-1.5 text-xs ${
                                  isClosedStatus(offering.status) ? 'ring-2 ring-inset ring-red-500' : ''
                                }`}
                                style={{
                                  top: `${topOffset}px`,
                                  height: `${height}px`,
                                  zIndex: 10
                                }}
                                title={[
                                  `${offering.course_key} - ${offering.title}`,
                                  isClosedStatus(offering.status) ? 'Closed - unavailable' : offering.status,
                                  offering.instructor || 'TBA',
                                  meeting.location || 'TBA',
                                  prereqs[offering.course_key]
                                    ? `Prerequisites: ${prereqs[offering.course_key]}`
                                    : null,
                                ].filter(Boolean).join('\n')}
                              >
                                <div className="flex items-center gap-1">
                                  <div className="font-bold">{offering.course_key}</div>
                                  <SectionStatusBadge status={offering.status} compact />
                                </div>
                                <div className="text-xs truncate">§{offering.section} · {offering.crn}</div>
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
                                {meeting.location && (
                                  <div className="text-xs truncate">{meeting.location}</div>
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

      {/* CRN Summary for registration */}
      <div className="mt-2 border-t border-gray-200 pt-2 dark:border-gray-700">
        <h3 className="mb-1 text-xs font-semibold text-gray-600 dark:text-gray-400">Registration CRNs</h3>
        <div className="flex flex-wrap gap-1">
          {schedule.offerings.map((o) => (
            <div
              key={o.crn}
              className={`${courseColorMap.get(o.course_key) || COLORS[0]} flex items-center gap-1.5 rounded border px-2 py-1 text-xs font-mono ${
                isClosedStatus(o.status) ? 'ring-1 ring-inset ring-red-500' : ''
              }`}
            >
              <span className="font-bold">{o.course_key}</span> · {o.crn}
              <SectionStatusBadge status={o.status} compact />
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

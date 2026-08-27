import { DAYS, Schedule } from '@/types';

export function earliestStart(schedule: Schedule): number {
  const starts = schedule.offerings.flatMap((offering) =>
    offering.meetings.map((meeting) => meeting.start_min)
  );
  return starts.length ? Math.min(...starts) : Infinity;
}

export function latestEnd(schedule: Schedule): number {
  const ends = schedule.offerings.flatMap((offering) =>
    offering.meetings.map((meeting) => meeting.end_min)
  );
  return ends.length ? Math.max(...ends) : 0;
}

export function totalGapMinutes(schedule: Schedule): number {
  const meetingsByDay: Record<string, Array<[number, number]>> = {};
  schedule.offerings.forEach((offering) => {
    offering.meetings.forEach((meeting) => {
      (meetingsByDay[meeting.day] ??= []).push([meeting.start_min, meeting.end_min]);
    });
  });

  return Object.values(meetingsByDay).reduce((total, meetings) => {
    const sorted = [...meetings].sort((a, b) => a[0] - b[0]);
    return total + sorted.slice(0, -1).reduce((dayTotal, meeting, index) => {
      return dayTotal + Math.max(0, sorted[index + 1][0] - meeting[1]);
    }, 0);
  }, 0);
}

export function classDays(schedule: Schedule): string[] {
  const activeDays = new Set(
    schedule.offerings.flatMap((offering) => offering.meetings.map((meeting) => meeting.day))
  );
  return DAYS.filter((day) => activeDays.has(day));
}

export function instructorNames(schedule: Schedule): string[] {
  return [...new Set(
    schedule.offerings
      .map((offering) => offering.instructor)
      .filter((name): name is string => Boolean(name && name !== 'nan' && name !== 'Staff TBA'))
  )];
}

export function formatGap(minutes: number): string {
  if (minutes === 0) return 'No gaps';
  if (minutes < 60) return `${minutes}m gaps`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours}h${remainder ? ` ${remainder}m` : ''} gaps`;
}

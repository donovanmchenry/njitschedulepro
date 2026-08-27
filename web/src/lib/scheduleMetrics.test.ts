import { describe, expect, it } from 'vitest';
import { formatAvailabilityRange, Schedule } from '@/types';
import {
  classDays,
  earliestStart,
  formatGap,
  latestEnd,
  totalGapMinutes,
} from './scheduleMetrics';

const schedule: Schedule = {
  total_credits: 6,
  score: 0,
  offerings: [
    {
      crn: '1',
      course_key: 'CS 114',
      section: '001',
      title: 'Computer Science II',
      meetings: [
        { day: 'Mon', start_min: 9 * 60, end_min: 10 * 60 },
        { day: 'Wed', start_min: 9 * 60, end_min: 10 * 60 },
      ],
      status: 'Open',
      delivery: 'In-Person',
      credits: 3,
    },
    {
      crn: '2',
      course_key: 'MATH 111',
      section: '002',
      title: 'Calculus I',
      meetings: [{ day: 'Mon', start_min: 11 * 60, end_min: 12 * 60 }],
      status: 'Open',
      delivery: 'In-Person',
      credits: 3,
    },
  ],
};

describe('schedule metrics', () => {
  it('summarizes time bounds and class days', () => {
    expect(earliestStart(schedule)).toBe(540);
    expect(latestEnd(schedule)).toBe(720);
    expect(classDays(schedule)).toEqual(['Mon', 'Wed']);
  });

  it('calculates gaps between same-day meetings', () => {
    expect(totalGapMinutes(schedule)).toBe(60);
    expect(formatGap(60)).toBe('1h gaps');
    expect(formatGap(0)).toBe('No gaps');
  });

  it('labels full-day and end-of-day availability clearly', () => {
    expect(formatAvailabilityRange(0, 1440)).toBe('All day');
    expect(formatAvailabilityRange(17 * 60, 1440)).toBe('5:00 PM – End of day');
  });
});

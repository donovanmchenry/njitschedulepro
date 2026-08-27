import { describe, expect, it } from 'vitest';
import { Offering, Schedule, Status } from '@/types';
import {
  getClosedOfferings,
  getSectionStatusLabel,
  isClosedStatus,
} from './sectionAvailability';

function offering(crn: string, status: Status): Offering {
  return {
    crn,
    course_key: 'CS 300',
    section: crn,
    title: 'Test course',
    meetings: [],
    status,
    delivery: 'In-Person',
    credits: 3,
  };
}

describe('section availability', () => {
  it('identifies closed offerings in a schedule', () => {
    const schedule: Schedule = {
      offerings: [offering('10001', 'Open'), offering('10002', 'Closed')],
      total_credits: 6,
      score: 0,
    };

    expect(getClosedOfferings(schedule).map((item) => item.crn)).toEqual(['10002']);
    expect(isClosedStatus('Closed')).toBe(true);
    expect(isClosedStatus('Waitlist')).toBe(false);
  });

  it('provides explicit non-open status labels', () => {
    expect(getSectionStatusLabel('Closed')).toBe('Closed · unavailable');
    expect(getSectionStatusLabel('Waitlist')).toBe('Waitlist');
    expect(getSectionStatusLabel('Open')).toBeNull();
  });
});

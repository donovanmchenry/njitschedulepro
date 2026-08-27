import { Offering, Schedule, Status } from '@/types';

export function isClosedStatus(status: Status | string): boolean {
  return status === 'Closed';
}

export function getClosedOfferings(schedule: Schedule): Offering[] {
  return schedule.offerings.filter((offering) => isClosedStatus(offering.status));
}

export function getSectionStatusLabel(status: Status | string): string | null {
  if (status === 'Closed') return 'Closed · unavailable';
  if (status === 'Waitlist') return 'Waitlist';
  return null;
}

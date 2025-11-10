/**
 * Type definitions matching the API models
 */

export type DayOfWeek = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';

export type Status = 'Open' | 'Closed' | 'Waitlist';

export type DeliveryMode = 'In-Person' | 'Online' | 'Hybrid' | 'Async';

export interface Meeting {
  day: DayOfWeek;
  start_min: number;
  end_min: number;
  location?: string | null;
}

export interface Offering {
  crn: string;
  course_key: string;
  section: string;
  title: string;
  term?: string | null;
  meetings: Meeting[];
  status: Status;
  capacity?: number | null;
  enrolled?: number | null;
  instructor?: string | null;
  delivery: DeliveryMode;
  credits?: number | null;
  info?: string | null;
  comments?: string | null;
}

export interface AvailabilityBlock {
  day: DayOfWeek;
  start_min: number;
  end_min: number;
}

export interface ScheduleFilters {
  status?: Status[];
  delivery?: DeliveryMode[];
  campus_include?: string[];
  campus_exclude?: string[];
  avoid_instructors?: string[];
  prefer_instructors?: string[];
  earliest_start?: number;
  latest_end?: number;
  max_gap_min?: number;
  include_honors?: boolean;
  include_non_honors?: boolean;
}

export interface SolveRequest {
  required_course_keys: string[];
  optional_course_keys?: string[];
  required_crns?: string[];
  preferred_professors?: Record<string, string[]>;
  min_credits?: number;
  max_credits?: number;
  unavailable: AvailabilityBlock[];
  filters?: ScheduleFilters;
  max_results?: number;
}

export interface Schedule {
  offerings: Offering[];
  total_credits: number;
  score: number;
}

export interface Course {
  course_key: string;
  title: string;
  sections: {
    crn: string;
    section: string;
    status: string;
    delivery: string;
    instructor: string | null;
    credits: number | null;
  }[];
}

// Helper functions
export function minutesToTime(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;
  return `${displayHours}:${mins.toString().padStart(2, '0')} ${period}`;
}

export function timeToMinutes(timeStr: string): number {
  const match = timeStr.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (!match) return 0;

  let hours = parseInt(match[1]);
  const minutes = parseInt(match[2]);
  const period = match[3].toUpperCase();

  if (period === 'PM' && hours !== 12) hours += 12;
  if (period === 'AM' && hours === 12) hours = 0;

  return hours * 60 + minutes;
}

export const DAYS: DayOfWeek[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

export const DAY_NAMES: Record<DayOfWeek, string> = {
  Mon: 'Monday',
  Tue: 'Tuesday',
  Wed: 'Wednesday',
  Thu: 'Thursday',
  Fri: 'Friday',
  Sat: 'Saturday',
  Sun: 'Sunday',
};

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
  preferred_delivery?: DeliveryMode[];
  campus_include?: string[];
  campus_exclude?: string[];
  avoid_instructors?: string[];
  prefer_instructors?: string[];
  earliest_start?: number;
  latest_end?: number;
  preferred_time?: TimePreference;
  max_gap_min?: number;
  include_honors?: boolean;
  include_non_honors?: boolean;
}

export interface SolveRequest {
  required_course_keys: string[];
  course_choice_groups?: CourseChoiceGroup[];
  optional_course_keys?: string[];
  required_crns?: string[];
  preferred_professors?: Record<string, string[]>;
  min_credits?: number;
  max_credits?: number;
  unavailable: AvailabilityBlock[];
  filters?: ScheduleFilters;
  max_results?: number;
}

export type TimePreference = 'morning' | 'afternoon' | 'evening';
export type ConstraintStrength = 'required' | 'preferred';

export interface CourseChoiceGroup {
  id: string;
  label: string;
  eligible_course_keys: string[];
  choose: number;
  total_course_count: number;
  open_course_count: number;
  departments?: string[];
  minimum_level?: number | null;
  requirement_id?: string | null;
  source_text?: string | null;
}

export interface IntentIssue {
  code: string;
  severity: 'warning' | 'blocking';
  message: string;
  source_text?: string | null;
}

export interface ParsedScheduleConstraints {
  schema_version: '1.0';
  courses: string[];
  excluded_courses: string[];
  course_groups: CourseChoiceGroup[];
  unavailable_blocks: AvailabilityBlock[];
  min_credits?: number | null;
  max_credits?: number | null;
  time_preference?: TimePreference | null;
  time_preference_strength?: ConstraintStrength | null;
  delivery_preference?: DeliveryMode | null;
  delivery_preference_strength?: ConstraintStrength | null;
  unresolved_requests: string[];
  issues: IntentIssue[];
}

export interface AIParseResult {
  success: boolean;
  constraints: ParsedScheduleConstraints;
  confidence: 'high' | 'medium' | 'low';
  usage?: {
    daily_count: number;
    daily_remaining: number;
    total_count: number;
    total_remaining: number;
  };
  meta?: {
    model: string;
    duration_ms: number;
    input_tokens: number;
    output_tokens: number;
  };
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
  const normalizedMinutes = ((minutes % 1440) + 1440) % 1440;
  const hours = Math.floor(normalizedMinutes / 60);
  const mins = normalizedMinutes % 60;
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;
  return `${displayHours}:${mins.toString().padStart(2, '0')} ${period}`;
}

export function formatAvailabilityRange(startMin: number, endMin: number): string {
  if (startMin === 0 && endMin === 1440) return 'All day';
  const endLabel = endMin === 1440 ? 'End of day' : minutesToTime(endMin);
  return `${minutesToTime(startMin)} – ${endLabel}`;
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

export const DAYS: DayOfWeek[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export const DAY_NAMES: Record<DayOfWeek, string> = {
  Mon: 'Monday',
  Tue: 'Tuesday',
  Wed: 'Wednesday',
  Thu: 'Thursday',
  Fri: 'Friday',
  Sat: 'Saturday',
  Sun: 'Sunday',
};

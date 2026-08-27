/**
 * Zustand store for application state
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  AvailabilityBlock,
  Course,
  CourseChoiceGroup,
  Schedule,
  ScheduleFilters,
  Status,
} from '@/types';

interface AppState {
  // Catalog
  courses: Course[];
  setCourses: (courses: Course[]) => void;
  mergeCourseDetails: (courses: Course[]) => void;

  // Selected courses
  selectedCourseKeys: string[];
  addCourse: (courseKey: string) => void;
  removeCourse: (courseKey: string) => void;

  // Course requirement groups
  courseChoiceGroups: CourseChoiceGroup[];
  addCourseChoiceGroup: (group: CourseChoiceGroup) => void;
  removeCourseChoiceGroup: (id: string) => void;

  // Required CRNs (specific sections that must be included)
  requiredCRNs: string[];
  addRequiredCRN: (crn: string) => void;
  removeRequiredCRN: (crn: string) => void;

  // Preferred professors per course
  preferredProfessors: Record<string, string[]>;
  addPreferredProfessor: (courseKey: string, professor: string) => void;
  removePreferredProfessor: (courseKey: string, professor: string) => void;

  // Availability blocks
  unavailableBlocks: AvailabilityBlock[];
  addUnavailableBlock: (block: AvailabilityBlock) => void;
  removeUnavailableBlock: (index: number) => void;
  clearUnavailableBlocks: () => void;

  // Credit range
  minCredits?: number;
  maxCredits?: number;
  setMinCredits: (credits?: number) => void;
  setMaxCredits: (credits?: number) => void;

  // Filters
  filters: ScheduleFilters;
  updateFilters: (filters: Partial<ScheduleFilters>) => void;

  // Generated schedules
  schedules: Schedule[];
  setSchedules: (schedules: Schedule[]) => void;

  // Selected schedule for viewing
  selectedScheduleIndex: number;
  setSelectedScheduleIndex: (index: number) => void;

  // Loading state
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;

  // Bookmarks
  bookmarkedSchedules: Schedule[];
  addBookmark: (schedule: Schedule) => void;
  removeBookmark: (index: number) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Catalog
      courses: [],
      setCourses: (courses) => set({ courses }),
      mergeCourseDetails: (detailedCourses) =>
        set((state) => {
          const detailedByKey = new Map(
            detailedCourses.map((course) => [course.course_key, course])
          );
          return {
            courses: state.courses.map((course) =>
              detailedByKey.has(course.course_key)
                ? { ...course, ...detailedByKey.get(course.course_key)! }
                : course
            ),
          };
        }),

      // Selected courses
      selectedCourseKeys: [],
      addCourse: (courseKey) =>
        set((state) => ({
          selectedCourseKeys: [...state.selectedCourseKeys, courseKey],
        })),
      removeCourse: (courseKey) =>
        set((state) => ({
          selectedCourseKeys: state.selectedCourseKeys.filter((k) => k !== courseKey),
          // Also remove any preferred professors for this course
          preferredProfessors: Object.fromEntries(
            Object.entries(state.preferredProfessors).filter(([k]) => k !== courseKey)
          ),
        })),

      // Course requirement groups
      courseChoiceGroups: [],
      addCourseChoiceGroup: (group) =>
        set((state) => ({
          courseChoiceGroups: [
            ...state.courseChoiceGroups.filter((current) => current.id !== group.id),
            group,
          ],
        })),
      removeCourseChoiceGroup: (id) =>
        set((state) => ({
          courseChoiceGroups: state.courseChoiceGroups.filter((group) => group.id !== id),
        })),

      // Required CRNs
      requiredCRNs: [],
      addRequiredCRN: (crn) =>
        set((state) => ({
          requiredCRNs: [...state.requiredCRNs, crn],
        })),
      removeRequiredCRN: (crn) =>
        set((state) => ({
          requiredCRNs: state.requiredCRNs.filter((c) => c !== crn),
        })),

      // Preferred professors
      preferredProfessors: {},
      addPreferredProfessor: (courseKey, professor) =>
        set((state) => ({
          preferredProfessors: {
            ...state.preferredProfessors,
            [courseKey]: [...(state.preferredProfessors[courseKey] || []), professor],
          },
        })),
      removePreferredProfessor: (courseKey, professor) =>
        set((state) => ({
          preferredProfessors: {
            ...state.preferredProfessors,
            [courseKey]: (state.preferredProfessors[courseKey] || []).filter(
              (p) => p !== professor
            ),
          },
        })),

      // Availability blocks
      unavailableBlocks: [],
      addUnavailableBlock: (block) =>
        set((state) => ({
          unavailableBlocks: [...state.unavailableBlocks, block],
        })),
      removeUnavailableBlock: (index) =>
        set((state) => ({
          unavailableBlocks: state.unavailableBlocks.filter((_, i) => i !== index),
        })),
      clearUnavailableBlocks: () => set({ unavailableBlocks: [] }),

      // Credit range
      minCredits: undefined,
      maxCredits: undefined,
      setMinCredits: (credits) => set({ minCredits: credits }),
      setMaxCredits: (credits) => set({ maxCredits: credits }),

      // Filters
      filters: {
        status: ['Open' as Status],
        include_honors: false,
      },
      updateFilters: (filters) =>
        set((state) => ({
          filters: { ...state.filters, ...filters },
        })),

      // Generated schedules
      schedules: [],
      setSchedules: (schedules) => set({ schedules, selectedScheduleIndex: 0 }),

      // Selected schedule
      selectedScheduleIndex: 0,
      setSelectedScheduleIndex: (index) => set({ selectedScheduleIndex: index }),

      // Loading
      isLoading: false,
      setIsLoading: (loading) => set({ isLoading: loading }),

      // Bookmarks
      bookmarkedSchedules: [],
      addBookmark: (schedule) =>
        set((state) => {
          const crns = schedule.offerings.map((o) => o.crn).sort().join(',');
          const alreadySaved = state.bookmarkedSchedules.some(
            (b) => b.offerings.map((o) => o.crn).sort().join(',') === crns
          );
          if (alreadySaved) return state;
          return { bookmarkedSchedules: [...state.bookmarkedSchedules, schedule] };
        }),
      removeBookmark: (index) =>
        set((state) => ({
          bookmarkedSchedules: state.bookmarkedSchedules.filter((_, i) => i !== index),
        })),
    }),
    {
      name: 'njit-schedule-pro-storage',
      version: 2,
      // Only persist bookmarks, not builder inputs or generated schedules.
      partialize: (state) => ({
        bookmarkedSchedules: state.bookmarkedSchedules,
      }),
      migrate: (persistedState) => {
        const persisted = persistedState as Partial<AppState>;
        return {
          bookmarkedSchedules: persisted.bookmarkedSchedules || [],
        };
      },
    }
  )
);

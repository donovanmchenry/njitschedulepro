/**
 * Zustand store for application state
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  AvailabilityBlock,
  Course,
  Schedule,
  ScheduleFilters,
  Status,
} from '@/types';

interface AppState {
  // Catalog
  courses: Course[];
  setCourses: (courses: Course[]) => void;

  // Selected courses
  selectedCourseKeys: string[];
  addCourse: (courseKey: string) => void;
  removeCourse: (courseKey: string) => void;

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

      // Filters
      filters: {
        status: ['Open' as Status],
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
        set((state) => ({
          bookmarkedSchedules: [...state.bookmarkedSchedules, schedule],
        })),
      removeBookmark: (index) =>
        set((state) => ({
          bookmarkedSchedules: state.bookmarkedSchedules.filter((_, i) => i !== index),
        })),
    }),
    {
      name: 'njit-schedule-pro-storage',
      // Only persist bookmarks, not temporary state
      partialize: (state) => ({
        bookmarkedSchedules: state.bookmarkedSchedules,
      }),
    }
  )
);

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

  // Availability blocks
  unavailableBlocks: AvailabilityBlock[];
  addUnavailableBlock: (block: AvailabilityBlock) => void;
  removeUnavailableBlock: (index: number) => void;
  clearUnavailableBlocks: () => void;

  // Filters
  filters: ScheduleFilters;
  updateFilters: (filters: Partial<ScheduleFilters>) => void;

  // Credits
  minCredits?: number;
  maxCredits?: number;
  setMinCredits: (value?: number) => void;
  setMaxCredits: (value?: number) => void;

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

      // Credits
      minCredits: undefined,
      maxCredits: undefined,
      setMinCredits: (value) => set({ minCredits: value }),
      setMaxCredits: (value) => set({ maxCredits: value }),

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

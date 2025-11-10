'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { X } from 'lucide-react';

export function CourseSelector() {
  const {
    courses,
    selectedCourseKeys,
    requiredCRNs,
    addCourse,
    removeCourse,
    addRequiredCRN,
    removeRequiredCRN,
  } = useAppStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [showingSectionsFor, setShowingSectionsFor] = useState<string | null>(null);

  // Check if search term looks like a CRN (5 digits)
  const looksLikeCRN = /^\d{4,6}$/.test(searchTerm.trim());

  const filteredCourses = courses.filter(
    (course) =>
      (course.course_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
        course.title.toLowerCase().includes(searchTerm.toLowerCase())) &&
      !selectedCourseKeys.includes(course.course_key)
  );

  const handleSelectCourse = (courseKey: string) => {
    // Show sections for this course
    setShowingSectionsFor(courseKey);
  };

  const handleSelectAnyCourse = (courseKey: string) => {
    addCourse(courseKey);
    setSearchTerm('');
    setShowDropdown(false);
    setShowingSectionsFor(null);
  };

  const handleSelectSection = (crn: string, courseKey: string) => {
    addRequiredCRN(crn);
    // Also add the course if not already added
    if (!selectedCourseKeys.includes(courseKey)) {
      addCourse(courseKey);
    }
    setSearchTerm('');
    setShowDropdown(false);
    setShowingSectionsFor(null);
  };

  const handleAddCRN = (crn: string) => {
    if (crn.trim()) {
      addRequiredCRN(crn.trim());
      setSearchTerm('');
      setShowDropdown(false);
    }
  };

  const handleSearch = () => {
    if (looksLikeCRN) {
      handleAddCRN(searchTerm);
    }
  };

  return (
    <div className="space-y-3">
      {/* Unified Search/CRN Input */}
      <div className="relative">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setShowDropdown(true);
          }}
          onFocus={() => setShowDropdown(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleSearch();
            }
          }}
          placeholder="Search courses (e.g., CS 100) or enter CRN..."
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* Dropdown */}
        {showDropdown && (
          <>
            {/* Course search results */}
            {!showingSectionsFor && searchTerm && (looksLikeCRN || filteredCourses.length > 0) && (
              <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-96 overflow-y-auto">
                {/* CRN option if input looks like a CRN */}
                {looksLikeCRN && !requiredCRNs.includes(searchTerm.trim()) && (
                  <button
                    onClick={() => handleAddCRN(searchTerm)}
                    className="w-full px-4 py-2 text-left hover:bg-green-50 dark:hover:bg-green-900/20 border-b dark:border-gray-600 bg-green-50/50 dark:bg-green-900/10"
                  >
                    <div className="font-semibold text-sm text-green-700 dark:text-green-400 flex items-center gap-2">
                      <span className="font-mono">{searchTerm}</span>
                      <span className="text-xs bg-green-200 dark:bg-green-800 px-2 py-0.5 rounded">
                        Add as CRN
                      </span>
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      Add this specific section to your schedule
                    </div>
                  </button>
                )}

                {/* Course results */}
                {filteredCourses.slice(0, 20).map((course) => (
                  <button
                    key={course.course_key}
                    onClick={() => handleSelectCourse(course.course_key)}
                    className="w-full px-4 py-2 text-left hover:bg-blue-50 dark:hover:bg-gray-600 border-b dark:border-gray-600 last:border-b-0"
                  >
                    <div className="font-semibold text-sm dark:text-white">{course.course_key}</div>
                    <div className="text-xs text-gray-600 dark:text-gray-300 truncate">{course.title}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{course.sections.length} sections available</div>
                  </button>
                ))}
              </div>
            )}

            {/* Section selection for a specific course */}
            {showingSectionsFor && (() => {
              const course = courses.find((c) => c.course_key === showingSectionsFor);
              if (!course) return null;

              return (
                <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-96 overflow-y-auto">
                  {/* Header with back button */}
                  <div className="sticky top-0 bg-gray-100 dark:bg-gray-800 border-b dark:border-gray-600 px-4 py-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-sm dark:text-white">{course.course_key}</div>
                        <div className="text-xs text-gray-600 dark:text-gray-400">{course.title}</div>
                      </div>
                      <button
                        onClick={() => setShowingSectionsFor(null)}
                        className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        ← Back
                      </button>
                    </div>
                  </div>

                  {/* Any section option */}
                  <button
                    onClick={() => handleSelectAnyCourse(course.course_key)}
                    className="w-full px-4 py-3 text-left hover:bg-blue-50 dark:hover:bg-gray-600 border-b dark:border-gray-600 bg-blue-50/30 dark:bg-blue-900/10"
                  >
                    <div className="font-semibold text-sm text-blue-700 dark:text-blue-400">
                      Any Section
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      Let the scheduler pick the best section
                    </div>
                  </button>

                  {/* Individual sections */}
                  {course.sections.map((section) => {
                    const isAlreadySelected = requiredCRNs.includes(section.crn);
                    return (
                      <button
                        key={section.crn}
                        onClick={() => handleSelectSection(section.crn, course.course_key)}
                        disabled={isAlreadySelected}
                        className={`w-full px-4 py-2 text-left border-b dark:border-gray-600 last:border-b-0 ${
                          isAlreadySelected
                            ? 'bg-gray-100 dark:bg-gray-800 opacity-50 cursor-not-allowed'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-650'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-sm dark:text-white">
                                Section {section.section}
                              </span>
                              <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
                                CRN: {section.crn}
                              </span>
                            </div>
                            <div className="text-xs text-gray-600 dark:text-gray-300 mt-0.5">
                              {section.instructor || 'Staff TBA'}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                              {section.delivery} • {section.credits || '?'} credits
                            </div>
                          </div>
                          <div className="flex-shrink-0">
                            <span
                              className={`text-xs px-2 py-0.5 rounded ${
                                section.status === 'Open'
                                  ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400'
                                  : section.status === 'Waitlist'
                                  ? 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-400'
                                  : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400'
                              }`}
                            >
                              {section.status}
                            </span>
                          </div>
                        </div>
                        {isAlreadySelected && (
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            Already selected
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })()}
          </>
        )}
      </div>

      {/* Required CRNs display */}
      {requiredCRNs.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {requiredCRNs.map((crn) => (
            <div
              key={crn}
              className="flex items-center gap-1 bg-green-100 dark:bg-green-900/40 px-2 py-1 rounded text-sm border border-green-200 dark:border-green-700"
            >
              <span className="font-mono text-green-800 dark:text-green-200">CRN: {crn}</span>
              <button
                onClick={() => removeRequiredCRN(crn)}
                className="text-red-600 hover:text-red-800 dark:text-red-400"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Selected courses */}
      <div className="space-y-2">
        {selectedCourseKeys.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400 italic">No courses selected</p>
        ) : (
          selectedCourseKeys.map((courseKey) => {
            const course = courses.find((c) => c.course_key === courseKey);
            // Get CRNs that belong to this course
            const courseCRNs = course?.sections
              .map((s) => s.crn)
              .filter((crn) => requiredCRNs.includes(crn)) || [];

            return (
              <div
                key={courseKey}
                className="bg-blue-100 dark:bg-blue-900/40 rounded-lg border border-blue-200 dark:border-blue-700"
              >
                <div className="flex items-center justify-between px-3 py-2">
                  <div className="flex-1">
                    <div className="font-semibold text-sm dark:text-blue-100">{courseKey}</div>
                    <div className="text-xs text-gray-600 dark:text-blue-200">
                      {course?.title || ''}
                    </div>
                    {courseCRNs.length > 0 && (
                      <div className="text-xs text-green-600 dark:text-green-400 mt-1">
                        {courseCRNs.length} specific section(s) selected
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => removeCourse(courseKey)}
                    className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 p-1"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { apiUrl } from '@/lib/api';
import { loadSubjectCatalog } from '@/lib/catalog';
import { X } from 'lucide-react';
import { fieldControlClass, iconButtonClass, secondaryButtonClass } from '@/lib/uiStyles';
import {
  courseMatchesRequirement,
  formatRequirementLabel,
  getCourseKeyParts,
  parseElectiveRequirement,
} from '@/lib/courseRequirement';

interface RmpRating {
  avg_rating: number;
  num_ratings: number;
  would_take_again: number;
  url: string;
}

export function CourseSelector() {
  const {
    courses,
    selectedCourseKeys,
    courseChoiceGroups,
    requiredCRNs,
    addCourse,
    addCourseChoiceGroup,
    removeCourse,
    removeCourseChoiceGroup,
    addRequiredCRN,
    removeRequiredCRN,
    mergeCourseDetails,
  } = useAppStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [showingSectionsFor, setShowingSectionsFor] = useState<string | null>(null);
  const [rmpRatings, setRmpRatings] = useState<Record<string, RmpRating | null>>({});
  const [sectionsLoading, setSectionsLoading] = useState(false);
  const [sectionsError, setSectionsError] = useState(false);

  useEffect(() => {
    if (!showingSectionsFor) return;
    const course = courses.find((current) => current.course_key === showingSectionsFor);
    if (!course || course.sections) return;
    let cancelled = false;
    setSectionsLoading(true);
    setSectionsError(false);
    loadSubjectCatalog(course.subject)
      .then((data) => {
        if (!cancelled) {
          // Clear this before the store update triggers the effect cleanup.
          setSectionsLoading(false);
          mergeCourseDetails(data.courses);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSectionsError(true);
          setSectionsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [courses, mergeCourseDetails, showingSectionsFor]);

  // Fetch RMP ratings when a course's sections are expanded
  useEffect(() => {
    if (!showingSectionsFor) return;
    const course = courses.find((c) => c.course_key === showingSectionsFor);
    if (!course?.sections) return;
    const names = [
      ...new Set(
        course.sections
          .map((section) => section.instructor)
          .filter((name): name is string => Boolean(name) && !(name! in rmpRatings))
      ),
    ];
    if (!names.length) return;

    fetch(apiUrl('/professors/ratings'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ names }),
    })
      .then((r) => (r.ok ? r.json() : {}))
      .then((data) => setRmpRatings((prev) => ({ ...prev, ...data })))
      .catch(() => {});
  }, [courses, rmpRatings, showingSectionsFor]);

  // Check if search term looks like a CRN (5 digits)
  const looksLikeCRN = /^\d{4,6}$/.test(searchTerm.trim());

  // Normalize: lowercase + strip all spaces so "cs114", "CS 114", "Cs114" all match
  const normalizeQuery = (s: string) => s.toLowerCase().replace(/\s+/g, '');
  const normalizedSearch = normalizeQuery(searchTerm);
  const electiveRequirement = parseElectiveRequirement(searchTerm);

  const filteredCourses = courses
    .filter((course) => {
      if (selectedCourseKeys.includes(course.course_key)) return false;
      if (electiveRequirement) {
        return courseMatchesRequirement(course.course_key, electiveRequirement);
      }
      return (
        normalizeQuery(course.course_key).includes(normalizedSearch) ||
        course.title.toLowerCase().includes(searchTerm.toLowerCase().trim())
      );
    })
    .sort((left, right) => {
      if (!electiveRequirement) return 0;
      const leftParts = getCourseKeyParts(left.course_key);
      const rightParts = getCourseKeyParts(right.course_key);
      if (!leftParts || !rightParts) return left.course_key.localeCompare(right.course_key);
      const departmentDifference =
        electiveRequirement.departments.indexOf(leftParts.department) -
        electiveRequirement.departments.indexOf(rightParts.department);
      return departmentDifference || leftParts.number - rightParts.number;
    });

  const matchingRequirementCount = electiveRequirement
    ? courses.filter(
        (course) =>
          !selectedCourseKeys.includes(course.course_key) &&
          courseMatchesRequirement(course.course_key, electiveRequirement)
      ).length
    : 0;
  const selectedRequirementCount = electiveRequirement
    ? selectedCourseKeys.filter((courseKey) =>
        courseMatchesRequirement(courseKey, electiveRequirement)
      ).length
    : 0;

  const handleAddRequirement = () => {
    if (!electiveRequirement) return;
    const matchingCourses = courses.filter(
      (course) =>
        !selectedCourseKeys.includes(course.course_key) &&
        courseMatchesRequirement(course.course_key, electiveRequirement)
    );
    const choose = electiveRequirement.courseCount ?? 1;
    addCourseChoiceGroup({
      id: `manual-${electiveRequirement.departments.join('-').toLowerCase()}-${electiveRequirement.minimumLevel}-${choose}`,
      label: formatRequirementLabel({ ...electiveRequirement, courseCount: choose }),
      eligible_course_keys: matchingCourses.map((course) => course.course_key),
      choose,
      total_course_count: matchingCourses.length,
      open_course_count: matchingCourses.filter((course) => course.open_section_count > 0).length,
      departments: electiveRequirement.departments,
      minimum_level: electiveRequirement.minimumLevel,
      source_text: searchTerm,
    });
    setSearchTerm('');
    setShowDropdown(false);
  };

  const handleSelectCourse = (courseKey: string) => {
    // Show sections for this course
    setShowingSectionsFor(courseKey);
  };

  const handleSelectAnyCourse = (courseKey: string) => {
    addCourse(courseKey);
    if (!electiveRequirement) {
      setSearchTerm('');
      setShowDropdown(false);
    }
    setShowingSectionsFor(null);
  };

  const handleSelectSection = (crn: string, courseKey: string) => {
    addRequiredCRN(crn);
    // Also add the course if not already added
    if (!selectedCourseKeys.includes(courseKey)) {
      addCourse(courseKey);
    }
    if (!electiveRequirement) {
      setSearchTerm('');
      setShowDropdown(false);
    }
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
    <div className="space-y-2">
      {/* Unified Search/CRN Input */}
      <div className="relative">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setShowingSectionsFor(null);
            setShowDropdown(true);
          }}
          onFocus={() => setShowDropdown(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleSearch();
            }
          }}
          placeholder="Search courses, CRNs, or requirements..."
          className={`w-full px-3 py-2 text-sm ${fieldControlClass}`}
        />

        {/* Dropdown */}
        {showDropdown && (
          <>
            {/* Course search results */}
            {!showingSectionsFor && searchTerm && (looksLikeCRN || electiveRequirement || filteredCourses.length > 0) && (
              <div className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-gray-300 bg-white shadow-sm dark:border-gray-600 dark:bg-gray-700 sm:max-h-96">
                {electiveRequirement && (
                  <div className="sticky top-0 z-10 border-b border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-600 dark:bg-gray-800">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-white">
                          {formatRequirementLabel(electiveRequirement)}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {matchingRequirementCount} matching {matchingRequirementCount === 1 ? 'course' : 'courses'}
                          {electiveRequirement.courseCount
                            ? ` · ${selectedRequirementCount} of ${electiveRequirement.courseCount} selected`
                            : ''}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={handleAddRequirement}
                        disabled={matchingRequirementCount < (electiveRequirement.courseCount ?? 1)}
                        className={`shrink-0 px-2 py-1 text-xs ${secondaryButtonClass}`}
                      >
                        Add requirement
                      </button>
                    </div>
                  </div>
                )}

                {/* CRN option if input looks like a CRN */}
                {looksLikeCRN && !requiredCRNs.includes(searchTerm.trim()) && (
                  <button
                    onClick={() => handleAddCRN(searchTerm)}
                    className="w-full border-b border-gray-200 bg-gray-50 px-3 py-2 text-left transition-colors hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:hover:bg-gray-700"
                  >
                    <div className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
                      <span className="font-mono">{searchTerm}</span>
                      <span className="rounded border border-gray-300 px-1.5 py-0.5 text-[10px] text-gray-600 dark:border-gray-600 dark:text-gray-300">
                        Add as CRN
                      </span>
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      Require this section
                    </div>
                  </button>
                )}

                {/* Course results */}
                {(electiveRequirement ? filteredCourses : filteredCourses.slice(0, 20)).map((course) => (
                  <button
                    key={course.course_key}
                    onClick={() => handleSelectCourse(course.course_key)}
                    className="w-full border-b border-gray-200 px-3 py-2 text-left transition-colors last:border-b-0 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-600"
                  >
                    <div className="font-semibold text-sm dark:text-white">{course.course_key}</div>
                    <div className="text-xs text-gray-600 dark:text-gray-300 truncate">{course.title}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {course.section_count} {course.section_count === 1 ? 'section' : 'sections'} available
                    </div>
                  </button>
                ))}

                {electiveRequirement && filteredCourses.length === 0 && (
                  <div className="px-3 py-4 text-center text-xs text-gray-500 dark:text-gray-400">
                    No additional matching courses
                  </div>
                )}
              </div>
            )}

            {/* Section selection for a specific course */}
            {showingSectionsFor && (() => {
              const course = courses.find((c) => c.course_key === showingSectionsFor);
              if (!course) return null;

              return (
                <div className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-gray-300 bg-white shadow-sm dark:border-gray-600 dark:bg-gray-700 sm:max-h-96">
                  {/* Header with back button */}
                  <div className="sticky top-0 border-b border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-600 dark:bg-gray-800">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-sm dark:text-white">{course.course_key}</div>
                        <div className="text-xs text-gray-600 dark:text-gray-400">{course.title}</div>
                      </div>
                      <button
                        onClick={() => setShowingSectionsFor(null)}
                        className={`px-2 py-1 text-xs ${secondaryButtonClass}`}
                      >
                        ← Back
                      </button>
                    </div>
                  </div>

                  {/* Any section option */}
                  <button
                    onClick={() => handleSelectAnyCourse(course.course_key)}
                    className="w-full border-b border-gray-200 bg-gray-50 px-3 py-2 text-left transition-colors hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:hover:bg-gray-700"
                  >
                    <div className="text-sm font-semibold text-gray-900 dark:text-white">
                      Any section
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      Use any section that fits
                    </div>
                  </button>

                  {sectionsLoading && (
                    <div className="px-3 py-4 text-center text-xs text-gray-500 dark:text-gray-400">
                      Loading sections…
                    </div>
                  )}
                  {sectionsError && (
                    <div className="px-3 py-4 text-center text-xs text-red-600 dark:text-red-400">
                      Sections could not be loaded. Close this list and try again.
                    </div>
                  )}

                  {/* Individual sections */}
                  {(course.sections || []).map((section) => {
                    const isAlreadySelected = requiredCRNs.includes(section.crn);
                    return (
                      <button
                        key={section.crn}
                        onClick={() => handleSelectSection(section.crn, course.course_key)}
                        disabled={isAlreadySelected}
                        className={`w-full border-b border-gray-200 px-3 py-3 text-left last:border-b-0 dark:border-gray-600 sm:py-2 ${
                          isAlreadySelected
                            ? 'bg-gray-100 dark:bg-gray-800 opacity-50 cursor-not-allowed'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-600'
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
                            <div className="text-xs text-gray-600 dark:text-gray-300 mt-0.5 flex items-center gap-1.5 flex-wrap">
                              {section.instructor || 'Staff TBA'}
                              {section.instructor && rmpRatings[section.instructor] && (
                                <a
                                  href={rmpRatings[section.instructor]!.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-amber-500 dark:text-amber-400 font-medium hover:underline"
                                >
                                  ★ {rmpRatings[section.instructor]!.avg_rating.toFixed(1)}
                                  <span className="text-gray-400 dark:text-gray-500 ml-0.5">
                                    ({rmpRatings[section.instructor]!.num_ratings})
                                  </span>
                                </a>
                              )}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                              {section.delivery} • {section.credits || '?'} credits
                            </div>
                          </div>
                          <div className="flex-shrink-0">
                            <span
                              className={`rounded-md px-2 py-0.5 text-xs ${
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
        <div className="flex flex-wrap gap-1">
          {requiredCRNs.map((crn) => (
            <div
              key={crn}
              className="flex items-center gap-1 rounded-md border border-gray-300 bg-gray-50 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800"
            >
              <span className="font-mono text-gray-700 dark:text-gray-300">CRN: {crn}</span>
              <button
                type="button"
                onClick={() => removeRequiredCRN(crn)}
                className="rounded text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
                aria-label={`Remove CRN ${crn}`}
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Selected courses */}
      <div className="space-y-1">
        {selectedCourseKeys.length === 0 && courseChoiceGroups.length === 0 ? (
          <p className="text-xs italic text-gray-500 dark:text-gray-400">No courses selected</p>
        ) : (
          <>
          {courseChoiceGroups.map((group) => (
            <div
              key={group.id}
              className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-gray-900 dark:text-white">
                    {group.label}
                  </div>
                  <div className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                    {group.open_course_count} open · {group.total_course_count} offered
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeCourseChoiceGroup(group.id)}
                  className={iconButtonClass}
                  aria-label={`Remove ${group.label}`}
                >
                  <X size={18} />
                </button>
              </div>
            </div>
          ))}
          {selectedCourseKeys.map((courseKey) => {
            const course = courses.find((c) => c.course_key === courseKey);
            // Get CRNs that belong to this course
            const courseCRNs = course?.sections
              ?.map((s) => s.crn)
              .filter((crn) => requiredCRNs.includes(crn)) || [];

            return (
              <div
                key={courseKey}
                className="rounded-md border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex items-center justify-between px-3 py-2">
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-gray-900 dark:text-white">{courseKey}</div>
                    <div className="text-xs text-gray-600 dark:text-gray-300">
                      {course?.title || ''}
                    </div>
                    {courseCRNs.length > 0 && (
                      <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        {courseCRNs.length} specific {courseCRNs.length === 1 ? 'section' : 'sections'}
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => removeCourse(courseKey)}
                    className={iconButtonClass}
                    aria-label={`Remove ${courseKey}`}
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>
            );
          })}
          </>
        )}
      </div>
    </div>
  );
}

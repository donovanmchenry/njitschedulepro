'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { X } from 'lucide-react';

export function CourseSelector() {
  const { courses, selectedCourseKeys, addCourse, removeCourse } = useAppStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);

  const filteredCourses = courses.filter(
    (course) =>
      (course.course_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
        course.title.toLowerCase().includes(searchTerm.toLowerCase())) &&
      !selectedCourseKeys.includes(course.course_key)
  );

  const handleSelectCourse = (courseKey: string) => {
    addCourse(courseKey);
    setSearchTerm('');
    setShowDropdown(false);
  };

  return (
    <div className="space-y-3">
      {/* Search input */}
      <div className="relative">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setShowDropdown(true);
          }}
          onFocus={() => setShowDropdown(true)}
          placeholder="Search courses (e.g., CS 100, MATH)..."
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* Dropdown */}
        {showDropdown && searchTerm && filteredCourses.length > 0 && (
          <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {filteredCourses.slice(0, 20).map((course) => (
              <button
                key={course.course_key}
                onClick={() => handleSelectCourse(course.course_key)}
                className="w-full px-4 py-2 text-left hover:bg-blue-50 border-b last:border-b-0"
              >
                <div className="font-semibold text-sm">{course.course_key}</div>
                <div className="text-xs text-gray-600 truncate">{course.title}</div>
                <div className="text-xs text-gray-500">{course.sections.length} sections</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected courses */}
      <div className="space-y-2">
        {selectedCourseKeys.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No courses selected</p>
        ) : (
          selectedCourseKeys.map((courseKey) => {
            const course = courses.find((c) => c.course_key === courseKey);
            return (
              <div
                key={courseKey}
                className="flex items-center justify-between bg-blue-100 dark:bg-blue-900 px-3 py-2 rounded-lg"
              >
                <div>
                  <div className="font-semibold text-sm">{courseKey}</div>
                  <div className="text-xs text-gray-600 dark:text-gray-300">
                    {course?.title || ''}
                  </div>
                </div>
                <button
                  onClick={() => removeCourse(courseKey)}
                  className="text-red-600 hover:text-red-800 dark:text-red-400"
                >
                  <X size={18} />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

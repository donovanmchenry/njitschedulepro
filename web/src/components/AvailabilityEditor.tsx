'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { AvailabilityBlock, DAYS, DAY_NAMES, DayOfWeek, minutesToTime } from '@/types';
import { X } from 'lucide-react';

export function AvailabilityEditor() {
  const {
    unavailableBlocks,
    addUnavailableBlock,
    removeUnavailableBlock,
  } = useAppStore();

  const [selectedDay, setSelectedDay] = useState<DayOfWeek>('Mon');
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('17:00');

  const handleAddBlock = () => {
    const [startHour, startMin] = startTime.split(':').map(Number);
    const [endHour, endMin] = endTime.split(':').map(Number);

    const start_min = startHour * 60 + startMin;
    const end_min = endHour * 60 + endMin;

    if (end_min <= start_min) {
      alert('End time must be after start time');
      return;
    }

    const block: AvailabilityBlock = {
      day: selectedDay,
      start_min,
      end_min,
    };

    addUnavailableBlock(block);
  };

  return (
    <div className="space-y-4">
      {/* Add availability block */}
      <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg space-y-3">
        <div>
          <label className="block text-sm font-medium mb-1 dark:text-gray-200">Day</label>
          <select
            value={selectedDay}
            onChange={(e) => setSelectedDay(e.target.value as DayOfWeek)}
            className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-600 dark:text-white rounded-lg"
          >
            {DAYS.map((day) => (
              <option key={day} value={day}>
                {DAY_NAMES[day]}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-sm font-medium mb-1 dark:text-gray-200">From</label>
            <input
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-600 dark:text-white rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 dark:text-gray-200">To</label>
            <input
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-600 dark:text-white rounded-lg"
            />
          </div>
        </div>

        <button
          onClick={handleAddBlock}
          className="w-full bg-njit-navy hover:bg-njit-navy/90 dark:bg-blue-600 dark:hover:bg-blue-700 text-white py-2 px-4 rounded-lg text-sm transition-colors"
        >
          Add Unavailable Time
        </button>
      </div>

      {/* Existing blocks */}
      <div className="space-y-2">
        {unavailableBlocks.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400 italic">No constraints set</p>
        ) : (
          unavailableBlocks.map((block, index) => (
            <div
              key={index}
              className="flex items-center justify-between bg-red-100 dark:bg-red-900/40 px-3 py-2 rounded-lg border border-red-200 dark:border-red-700"
            >
              <div className="text-sm dark:text-red-100">
                <span className="font-semibold">{DAY_NAMES[block.day]}</span>
                <span className="mx-2">•</span>
                <span>
                  {minutesToTime(block.start_min)} - {minutesToTime(block.end_min)}
                </span>
              </div>
              <button
                onClick={() => removeUnavailableBlock(index)}
                className="text-red-700 hover:text-red-900 dark:text-red-300 dark:hover:text-red-200"
              >
                <X size={18} />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { AvailabilityBlock, DAYS, DAY_NAMES, DayOfWeek, minutesToTime } from '@/types';
import { X } from 'lucide-react';

function selectsToMinutes(hour: string, minute: string, period: 'AM' | 'PM'): number {
  let h = parseInt(hour);
  if (period === 'AM' && h === 12) h = 0;
  if (period === 'PM' && h !== 12) h += 12;
  return h * 60 + parseInt(minute);
}

const SELECT_CLASS =
  'px-2 py-2 border dark:border-gray-600 dark:bg-gray-600 dark:text-white rounded-lg text-sm';

export function AvailabilityEditor() {
  const {
    unavailableBlocks,
    addUnavailableBlock,
    removeUnavailableBlock,
  } = useAppStore();

  const [selectedDay, setSelectedDay] = useState<DayOfWeek>('Mon');
  const [startHour, setStartHour] = useState('9');
  const [startMinute, setStartMinute] = useState('00');
  const [startPeriod, setStartPeriod] = useState<'AM' | 'PM'>('AM');
  const [endHour, setEndHour] = useState('5');
  const [endMinute, setEndMinute] = useState('00');
  const [endPeriod, setEndPeriod] = useState<'AM' | 'PM'>('PM');

  const handleAddBlock = () => {
    const start_min = selectsToMinutes(startHour, startMinute, startPeriod);
    const end_min = selectsToMinutes(endHour, endMinute, endPeriod);

    if (end_min <= start_min) {
      alert('End time must be after start time');
      return;
    }

    const block: AvailabilityBlock = { day: selectedDay, start_min, end_min };
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
            <div className="flex gap-1">
              <select value={startHour} onChange={(e) => setStartHour(e.target.value)} className={SELECT_CLASS}>
                {[1,2,3,4,5,6,7,8,9,10,11,12].map((h) => (
                  <option key={h} value={h}>{h}</option>
                ))}
              </select>
              <select value={startMinute} onChange={(e) => setStartMinute(e.target.value)} className={SELECT_CLASS}>
                {['00','15','30','45'].map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              <select value={startPeriod} onChange={(e) => setStartPeriod(e.target.value as 'AM' | 'PM')} className={SELECT_CLASS}>
                <option>AM</option>
                <option>PM</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 dark:text-gray-200">To</label>
            <div className="flex gap-1">
              <select value={endHour} onChange={(e) => setEndHour(e.target.value)} className={SELECT_CLASS}>
                {[1,2,3,4,5,6,7,8,9,10,11,12].map((h) => (
                  <option key={h} value={h}>{h}</option>
                ))}
              </select>
              <select value={endMinute} onChange={(e) => setEndMinute(e.target.value)} className={SELECT_CLASS}>
                {['00','15','30','45'].map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              <select value={endPeriod} onChange={(e) => setEndPeriod(e.target.value as 'AM' | 'PM')} className={SELECT_CLASS}>
                <option>AM</option>
                <option>PM</option>
              </select>
            </div>
          </div>
        </div>

        <button
          onClick={handleAddBlock}
          className="w-full bg-njit-red hover:bg-red-700 text-white py-2 px-4 rounded-lg text-sm transition-colors shadow-md"
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

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

const DAY_LABELS: Record<DayOfWeek, string> = {
  Mon: 'M', Tue: 'T', Wed: 'W', Thu: 'R', Fri: 'F',
};

function TimePicker({
  label,
  hour, minute, period,
  onHour, onMinute, onPeriod,
}: {
  label: string;
  hour: string; minute: string; period: 'AM' | 'PM';
  onHour: (v: string) => void;
  onMinute: (v: string) => void;
  onPeriod: (v: 'AM' | 'PM') => void;
}) {
  const selectClass =
    'bg-transparent dark:text-white text-sm text-center appearance-none cursor-pointer focus:outline-none py-2 px-1';

  return (
    <div className="flex-1">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 text-center">{label}</p>
      <div className="flex items-center divide-x divide-gray-200 dark:divide-gray-500 border border-gray-300 dark:border-gray-500 rounded-lg overflow-hidden bg-white dark:bg-gray-600">
        <select value={hour} onChange={(e) => onHour(e.target.value)} className={`${selectClass} w-10`}>
          {[1,2,3,4,5,6,7,8,9,10,11,12].map((h) => (
            <option key={h} value={h}>{h}</option>
          ))}
        </select>
        <select value={minute} onChange={(e) => onMinute(e.target.value)} className={`${selectClass} w-12`}>
          {['00','15','30','45'].map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select value={period} onChange={(e) => onPeriod(e.target.value as 'AM' | 'PM')} className={`${selectClass} w-12`}>
          <option>AM</option>
          <option>PM</option>
        </select>
      </div>
    </div>
  );
}

export function AvailabilityEditor() {
  const { unavailableBlocks, addUnavailableBlock, removeUnavailableBlock } = useAppStore();

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
    addUnavailableBlock({ day: selectedDay, start_min, end_min });
  };

  return (
    <div className="space-y-4">
      <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg space-y-4">

        {/* Day pill buttons */}
        <div className="flex gap-1.5">
          {DAYS.map((day) => (
            <button
              key={day}
              onClick={() => setSelectedDay(day)}
              className={`flex-1 py-2 rounded-lg text-sm font-semibold touch-manipulation transition-colors ${
                selectedDay === day
                  ? 'bg-njit-red text-white shadow-sm'
                  : 'bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-500'
              }`}
            >
              {DAY_LABELS[day]}
            </button>
          ))}
        </div>

        {/* From → To */}
        <div className="flex items-end gap-2">
          <TimePicker
            label="From"
            hour={startHour} minute={startMinute} period={startPeriod}
            onHour={setStartHour} onMinute={setStartMinute} onPeriod={setStartPeriod}
          />
          <span className="text-gray-400 dark:text-gray-400 pb-2.5 text-base">→</span>
          <TimePicker
            label="To"
            hour={endHour} minute={endMinute} period={endPeriod}
            onHour={setEndHour} onMinute={setEndMinute} onPeriod={setEndPeriod}
          />
        </div>

        <button
          onClick={handleAddBlock}
          className="w-full bg-njit-red hover:bg-red-700 text-white py-2.5 px-4 rounded-lg text-sm font-medium transition-colors shadow-md touch-manipulation"
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
                <span>{minutesToTime(block.start_min)} – {minutesToTime(block.end_min)}</span>
              </div>
              <button
                onClick={() => removeUnavailableBlock(index)}
                className="text-red-700 hover:text-red-900 dark:text-red-300 dark:hover:text-red-200 p-1"
              >
                <X size={16} />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

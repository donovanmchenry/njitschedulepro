'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { AvailabilityBlock, DAYS, DAY_NAMES, DayOfWeek, formatAvailabilityRange } from '@/types';
import { X } from 'lucide-react';
import { primaryButtonClass, selectedControlClass, unselectedControlClass } from '@/lib/uiStyles';
import { Notice } from './Notice';

function selectsToMinutes(hour: string, minute: string, period: 'AM' | 'PM'): number {
  let h = parseInt(hour);
  if (period === 'AM' && h === 12) h = 0;
  if (period === 'PM' && h !== 12) h += 12;
  return h * 60 + parseInt(minute);
}

const DAY_LABELS: Record<DayOfWeek, string> = {
  Mon: 'M', Tue: 'T', Wed: 'W', Thu: 'R', Fri: 'F', Sat: 'S', Sun: 'U',
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
    'cursor-pointer appearance-none bg-transparent px-1 py-1.5 text-center text-xs dark:text-white';

  return (
    <div className="min-w-0 flex-1">
      <p className="mb-1 text-center text-[11px] font-medium text-gray-500 dark:text-gray-400">{label}</p>
      <div className="flex items-center divide-x divide-gray-200 overflow-hidden rounded-md border border-gray-300 bg-white dark:divide-gray-600 dark:border-gray-600 dark:bg-gray-700">
        <select value={hour} onChange={(e) => onHour(e.target.value)} className={`${selectClass} min-w-0 flex-1`}>
          {[1,2,3,4,5,6,7,8,9,10,11,12].map((h) => (
            <option key={h} value={h}>{h}</option>
          ))}
        </select>
        <select value={minute} onChange={(e) => onMinute(e.target.value)} className={`${selectClass} min-w-0 flex-1`}>
          {['00','15','30','45'].map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select value={period} onChange={(e) => onPeriod(e.target.value as 'AM' | 'PM')} className={`${selectClass} min-w-0 flex-1`}>
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
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleAddBlock = () => {
    const start_min = selectsToMinutes(startHour, startMinute, startPeriod);
    const end_min = selectsToMinutes(endHour, endMinute, endPeriod);
    if (end_min <= start_min) {
      setValidationError('End time must be after start time.');
      return;
    }
    setValidationError(null);
    addUnavailableBlock({ day: selectedDay, start_min, end_min });
  };

  return (
    <div className="space-y-2">
      <div className="space-y-2 rounded-md border border-gray-200 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800">

        {/* Day pill buttons */}
        <div className="flex gap-1">
          {DAYS.map((day) => (
            <button
              key={day}
              onClick={() => setSelectedDay(day)}
              className={`flex-1 rounded-md border py-1.5 text-xs font-semibold touch-manipulation transition-colors ${
                selectedDay === day
                  ? selectedControlClass
                  : unselectedControlClass
              }`}
            >
              {DAY_LABELS[day]}
            </button>
          ))}
        </div>

        {/* From → To */}
        <div className="grid grid-cols-1 gap-1 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] sm:items-end">
          <TimePicker
            label="From"
            hour={startHour} minute={startMinute} period={startPeriod}
            onHour={setStartHour} onMinute={setStartMinute} onPeriod={setStartPeriod}
          />
          <span className="hidden pb-1.5 text-sm text-gray-400 sm:block">→</span>
          <TimePicker
            label="To"
            hour={endHour} minute={endMinute} period={endPeriod}
            onHour={setEndHour} onMinute={setEndMinute} onPeriod={setEndPeriod}
          />
        </div>

        <button
          onClick={handleAddBlock}
          className={`w-full px-3 py-2 text-xs touch-manipulation ${primaryButtonClass}`}
        >
          Add time to avoid
        </button>
      </div>

      {validationError && <Notice tone="error" className="text-xs">{validationError}</Notice>}

      {/* Existing blocks */}
      <div className="space-y-1">
        {unavailableBlocks.length === 0 ? (
          <p className="text-xs italic text-gray-500 dark:text-gray-400">No times added</p>
        ) : (
          unavailableBlocks.map((block, index) => (
            <div
              key={index}
              className="flex items-center justify-between rounded-md border border-gray-200 bg-gray-50 px-2 py-1 dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="text-xs text-gray-700 dark:text-gray-300">
                <span className="font-semibold">{DAY_NAMES[block.day]}</span>
                <span className="mx-2">•</span>
                <span>{formatAvailabilityRange(block.start_min, block.end_min)}</span>
              </div>
              <button
                type="button"
                onClick={() => removeUnavailableBlock(index)}
                className="rounded p-1 text-gray-500 transition-colors hover:bg-gray-200 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
                aria-label={`Remove unavailable time on ${DAY_NAMES[block.day]}`}
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

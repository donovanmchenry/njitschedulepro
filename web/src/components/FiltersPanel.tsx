'use client';

import { useAppStore } from '@/lib/store';
import { X } from 'lucide-react';
import { DeliveryMode, Status, minutesToTime } from '@/types';
import { fieldControlClass, selectedControlClass, unselectedControlClass } from '@/lib/uiStyles';

const DELIVERY_MODES: DeliveryMode[] = ['In-Person', 'Online', 'Hybrid', 'Async'];
const TIME_OPTIONS = Array.from({ length: 15 }, (_, index) => 7 * 60 + index * 60);

export function FiltersPanel() {
  const {
    filters,
    updateFilters,
    minCredits,
    maxCredits,
    setMinCredits,
    setMaxCredits,
  } = useAppStore();

  const toggleStatus = (status: Status) => {
    const current = filters.status || ['Open'];
    const next = current.includes(status)
      ? current.filter((item) => item !== status)
      : [...current, status];
    if (next.length > 0) updateFilters({ status: next });
  };

  const toggleDelivery = (mode: DeliveryMode) => {
    const current = filters.delivery || [];
    const next = current.includes(mode)
      ? current.filter((item) => item !== mode)
      : [...current, mode];
    updateFilters({ delivery: next.length ? next : undefined });
  };

  const pillClass = (selected: boolean) =>
    `rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors ${
      selected
        ? selectedControlClass
        : unselectedControlClass
    }`;

  return (
    <div className="space-y-3">
      <div>
        <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-300">
          Section availability
        </label>
        <div className="flex flex-wrap gap-1.5">
          {(['Open', 'Waitlist', 'Closed'] as Status[]).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => toggleStatus(status)}
              className={pillClass(filters.status?.includes(status) ?? false)}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {(filters.preferred_time || filters.preferred_delivery?.length) && (
        <div>
          <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-300">
            Preferences
          </label>
          <div className="flex flex-wrap gap-1.5">
            {filters.preferred_time && (
              <button
                type="button"
                onClick={() => updateFilters({ preferred_time: undefined })}
                className={`${pillClass(false)} flex items-center gap-1`}
              >
                {filters.preferred_time} <X size={12} />
              </button>
            )}
            {filters.preferred_delivery?.map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => updateFilters({ preferred_delivery: undefined })}
                className={`${pillClass(false)} flex items-center gap-1`}
              >
                {mode} <X size={12} />
              </button>
            ))}
          </div>
        </div>
      )}

      <div>
        <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-300">
          Class type
        </label>
        <div className="flex flex-wrap gap-1.5">
          {DELIVERY_MODES.map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => toggleDelivery(mode)}
              className={pillClass(filters.delivery?.includes(mode) ?? false)}
            >
              {mode === 'Async' ? 'Self-paced' : mode}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs font-semibold text-gray-600 dark:text-gray-300">
          First class
          <select
            value={filters.earliest_start ?? ''}
            onChange={(event) =>
              updateFilters({
                earliest_start: event.target.value ? Number(event.target.value) : undefined,
              })
            }
            className={`mt-1 w-full px-2 py-1.5 text-xs font-normal ${fieldControlClass}`}
          >
            <option value="">Any time</option>
            {TIME_OPTIONS.map((time) => (
              <option key={time} value={time}>{minutesToTime(time)}</option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold text-gray-600 dark:text-gray-300">
          Last class
          <select
            value={filters.latest_end ?? ''}
            onChange={(event) =>
              updateFilters({
                latest_end: event.target.value ? Number(event.target.value) : undefined,
              })
            }
            className={`mt-1 w-full px-2 py-1.5 text-xs font-normal ${fieldControlClass}`}
          >
            <option value="">Any time</option>
            {TIME_OPTIONS.map((time) => (
              <option key={time} value={time}>{minutesToTime(time)}</option>
            ))}
          </select>
        </label>
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-300">
          Credits
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs text-gray-500 dark:text-gray-400">
            Minimum
            <input
              type="number"
              min="0"
              max="30"
              value={minCredits ?? ''}
              onChange={(event) => setMinCredits(event.target.value ? Number(event.target.value) : undefined)}
              placeholder="No minimum"
              className={`mt-1 w-full px-2 py-1.5 text-xs font-normal ${fieldControlClass}`}
            />
          </label>
          <label className="text-xs text-gray-500 dark:text-gray-400">
            Maximum
            <input
              type="number"
              min="0"
              max="30"
              value={maxCredits ?? ''}
              onChange={(event) => setMaxCredits(event.target.value ? Number(event.target.value) : undefined)}
              placeholder="No maximum"
              className={`mt-1 w-full px-2 py-1.5 text-xs font-normal ${fieldControlClass}`}
            />
          </label>
        </div>
      </div>

      <label className="block text-xs font-semibold text-gray-600 dark:text-gray-300">
        Longest break between classes
        <div className="relative mt-1">
          <input
            type="number"
            min="0"
            max="480"
            step="15"
            value={filters.max_gap_min ?? ''}
            onChange={(event) =>
              updateFilters({
                max_gap_min: event.target.value ? Number(event.target.value) : undefined,
              })
            }
            placeholder="No limit"
            className={`w-full px-2 py-1.5 pr-16 text-xs font-normal ${fieldControlClass}`}
          />
          <span className="pointer-events-none absolute right-2 top-1.5 text-[11px] text-gray-400">minutes</span>
        </div>
      </label>

      <div>
        <label className="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-300">
          Include sections
        </label>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => updateFilters({ include_honors: !(filters.include_honors ?? true) })}
            className={pillClass(filters.include_honors ?? true)}
          >
            Honors
          </button>
          <button
            type="button"
            onClick={() => updateFilters({ include_non_honors: !(filters.include_non_honors ?? true) })}
            className={pillClass(filters.include_non_honors ?? true)}
          >
            Regular
          </button>
        </div>
      </div>
    </div>
  );
}

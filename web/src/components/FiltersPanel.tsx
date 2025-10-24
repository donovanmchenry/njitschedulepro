'use client';

import { useAppStore } from '@/lib/store';
import { Status } from '@/types';

export function FiltersPanel() {
  const { filters, updateFilters, minCredits, maxCredits, setMinCredits, setMaxCredits } =
    useAppStore();

  const toggleStatus = (status: Status) => {
    const currentStatuses = filters.status || ['Open'];
    const newStatuses = currentStatuses.includes(status)
      ? currentStatuses.filter((s) => s !== status)
      : [...currentStatuses, status];

    // Ensure at least one status is selected
    if (newStatuses.length === 0) return;

    updateFilters({ status: newStatuses });
  };

  return (
    <div className="space-y-4">
      {/* Status filters */}
      <div>
        <label className="block text-sm font-medium mb-2">Section Status</label>
        <div className="flex flex-wrap gap-2">
          {(['Open', 'Waitlist', 'Closed'] as Status[]).map((status) => {
            const isSelected = filters.status?.includes(status);
            return (
              <button
                key={status}
                onClick={() => toggleStatus(status)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  isSelected
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {status}
              </button>
            );
          })}
        </div>
      </div>

      {/* Credits */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">Min Credits</label>
          <input
            type="number"
            min="0"
            max="24"
            value={minCredits || ''}
            onChange={(e) =>
              setMinCredits(e.target.value ? Number(e.target.value) : undefined)
            }
            placeholder="None"
            className="w-full px-3 py-2 border rounded-lg"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Max Credits</label>
          <input
            type="number"
            min="0"
            max="24"
            value={maxCredits || ''}
            onChange={(e) =>
              setMaxCredits(e.target.value ? Number(e.target.value) : undefined)
            }
            placeholder="None"
            className="w-full px-3 py-2 border rounded-lg"
          />
        </div>
      </div>

      {/* Max gap */}
      <div>
        <label className="block text-sm font-medium mb-1">Max Gap Between Classes (min)</label>
        <input
          type="number"
          min="0"
          max="480"
          step="15"
          value={filters.max_gap_min || ''}
          onChange={(e) =>
            updateFilters({
              max_gap_min: e.target.value ? Number(e.target.value) : undefined,
            })
          }
          placeholder="Unlimited"
          className="w-full px-3 py-2 border rounded-lg"
        />
      </div>

      {/* Honors filter */}
      <div>
        <label className="block text-sm font-medium mb-2">Section Type</label>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() =>
              updateFilters({
                include_honors: !(filters.include_honors ?? true),
              })
            }
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
              filters.include_honors ?? true
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Honors (H##)
          </button>
          <button
            onClick={() =>
              updateFilters({
                include_non_honors: !(filters.include_non_honors ?? true),
              })
            }
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
              filters.include_non_honors ?? true
                ? 'bg-green-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Regular
          </button>
        </div>
        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
          Honors sections have &apos;H&apos; at the start (e.g., H02, H04)
        </p>
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { AlertTriangle, Check, Loader2 } from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { fieldControlClass, primaryButtonClass, secondaryButtonClass } from '@/lib/uiStyles';
import { Notice } from './Notice';
import {
  AIParseResult,
  DAY_NAMES,
  ParsedScheduleConstraints,
  formatAvailabilityRange,
} from '@/types';

interface AIScheduleInputProps {
  onConstraintsParsed: (constraints: ParsedScheduleConstraints) => void;
}

export function AIScheduleInput({ onConstraintsParsed }: AIScheduleInputProps) {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parsed, setParsed] = useState<AIParseResult | null>(null);

  const handleParse = async () => {
    if (!prompt.trim()) return;
    setIsLoading(true);
    setError(null);
    setParsed(null);

    try {
      const response = await fetch(apiUrl('/ai/parse-schedule'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not interpret that description');
      setParsed(data as AIParseResult);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not interpret that description');
    } finally {
      setIsLoading(false);
    }
  };

  const handleApply = () => {
    if (!parsed) return;
    onConstraintsParsed(parsed.constraints);
    setParsed(null);
    setPrompt('');
  };

  const constraints = parsed?.constraints;
  const blockingIssues = constraints?.issues.filter((issue) => issue.severity === 'blocking') || [];

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <h3 className="text-sm font-bold text-gray-900 dark:text-white">Describe your schedule</h3>
        <span className="text-[11px] text-gray-400">Optional</span>
      </div>

      <textarea
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) handleParse();
        }}
        placeholder="Example: CS 114 and MATH 111, no Friday classes, mornings only"
        disabled={isLoading}
        rows={2}
        maxLength={1000}
        className={`w-full resize-none px-2.5 py-2 text-sm ${fieldControlClass}`}
      />

      <div className="mt-2 flex justify-end">
        <button
          type="button"
          onClick={handleParse}
          disabled={isLoading || !prompt.trim()}
          className={`gap-1.5 px-3 py-1.5 text-xs ${secondaryButtonClass}`}
        >
          {isLoading && <Loader2 size={15} className="animate-spin" />}
          {isLoading ? 'Reading…' : 'Check details'}
        </button>
      </div>

      {error && (
        <Notice tone="error" className="mt-2 text-xs">{error}</Notice>
      )}

      {constraints && parsed && (
        <div className="mt-2 rounded-md border border-gray-200 bg-white p-2 dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-2 flex items-center justify-between">
            <div>
              <p className="text-sm font-bold text-gray-900 dark:text-white">Check these details</p>
            </div>
            <button
              type="button"
              onClick={handleApply}
              disabled={blockingIssues.length > 0}
              className={`gap-1 px-2.5 py-1.5 text-xs ${primaryButtonClass}`}
            >
              <Check size={14} /> {blockingIssues.length ? 'Needs changes' : 'Use these'}
            </button>
          </div>
          <div className="space-y-1 text-xs text-gray-600 dark:text-gray-300">
            {constraints.courses.length > 0 && (
              <p><span className="font-semibold">Courses:</span> {constraints.courses.join(', ')}</p>
            )}
            {constraints.course_groups.length > 0 && (
              <div>
                <span className="font-semibold">Course requirements:</span>
                <ul className="mt-0.5 space-y-0.5">
                  {constraints.course_groups.map((group) => (
                    <li key={group.id}>
                      {group.label} · {group.open_course_count} open of {group.total_course_count} offered
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {constraints.excluded_courses.length > 0 && (
              <p><span className="font-semibold">Leave out:</span> {constraints.excluded_courses.join(', ')}</p>
            )}
            {constraints.unavailable_blocks.length > 0 && (
              <div>
                <span className="font-semibold">No classes:</span>{' '}
                {constraints.unavailable_blocks.map((block) => (
                  <span key={`${block.day}-${block.start_min}-${block.end_min}`} className="mr-2 inline-block">
                    {DAY_NAMES[block.day]} {formatAvailabilityRange(block.start_min, block.end_min)}
                  </span>
                ))}
              </div>
            )}
            {(constraints.min_credits != null || constraints.max_credits != null) && (
              <p>
                <span className="font-semibold">Credits:</span>{' '}
                {constraints.min_credits != null && `minimum ${constraints.min_credits}`}
                {constraints.min_credits != null && constraints.max_credits != null && ' · '}
                {constraints.max_credits != null && `maximum ${constraints.max_credits}`}
              </p>
            )}
            {constraints.time_preference && (
              <p>
                <span className="font-semibold">Time:</span> {constraints.time_preference}
                {constraints.time_preference_strength === 'preferred' ? ' preferred' : ' only'}
              </p>
            )}
            {constraints.delivery_preference && (
              <p>
                <span className="font-semibold">Class type:</span> {constraints.delivery_preference}
                {constraints.delivery_preference_strength === 'preferred' ? ' preferred' : ' only'}
              </p>
            )}
            {constraints.issues.length > 0 && (
              <div className="mt-2 border-t border-gray-200 pt-2 dark:border-gray-700">
                {constraints.issues.map((issue, index) => (
                  <div
                    key={`${issue.code}-${index}`}
                    className={`flex items-start gap-1.5 py-0.5 ${
                      issue.severity === 'blocking'
                        ? 'text-red-700 dark:text-red-300'
                        : 'text-amber-700 dark:text-amber-300'
                    }`}
                  >
                    <AlertTriangle size={13} className="mt-0.5 shrink-0" />
                    <span>{issue.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

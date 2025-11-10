'use client';

import { useState } from 'react';
import { Sparkles, Settings, AlertCircle, Loader2, Info } from 'lucide-react';
import { apiUrl } from '@/lib/api';

interface AIScheduleInputProps {
  onConstraintsParsed: (constraints: any) => void;
}

export function AIScheduleInput({ onConstraintsParsed }: AIScheduleInputProps) {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('anthropic-api-key') || '';
    }
    return '';
  });
  const [usage, setUsage] = useState<any>(null);

  const saveApiKey = () => {
    if (apiKey.trim()) {
      localStorage.setItem('anthropic-api-key', apiKey.trim());
      setShowSettings(false);
    } else {
      localStorage.removeItem('anthropic-api-key');
    }
  };

  const clearApiKey = () => {
    setApiKey('');
    localStorage.removeItem('anthropic-api-key');
  };

  const handleParse = async () => {
    if (!prompt.trim()) {
      setError('Please describe your ideal schedule');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(apiUrl('/ai/parse-schedule'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          user_api_key: apiKey.trim() || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to parse schedule');
      }

      const data = await response.json();
      setUsage(data.usage);

      if (data.success && data.constraints) {
        onConstraintsParsed(data.constraints);
        setPrompt(''); // Clear input after success
      } else {
        setError('Could not understand your request. Please try rephrasing.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleParse();
    }
  };

  return (
    <div className="space-y-3">
      {/* Header with Settings */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="text-njit-red" size={20} />
          <h4 className="font-semibold text-gray-700 dark:text-gray-200">
            AI Schedule Assistant
          </h4>
        </div>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          title="API Key Settings"
        >
          <Settings size={16} className="text-gray-600 dark:text-gray-400" />
        </button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-3 border border-gray-200 dark:border-gray-700">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Anthropic API Key (Optional)
            </label>
            <div className="flex gap-2">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-ant-..."
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
              <button
                onClick={saveApiKey}
                className="px-4 py-2 bg-njit-red text-white rounded-lg text-sm hover:bg-red-700 transition-colors"
              >
                Save
              </button>
              {apiKey && (
                <button
                  onClick={clearApiKey}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              {apiKey
                ? '✓ Using your API key (unlimited)'
                : `Shared pool: ${usage?.daily_remaining || 5} requests left today`}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Get a key at{' '}
              <a
                href="https://console.anthropic.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-njit-red hover:underline"
              >
                console.anthropic.com
              </a>
            </p>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 flex gap-2">
        <Info size={16} className="text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-blue-700 dark:text-blue-300">
          <p className="font-medium mb-1">Describe your ideal schedule:</p>
          <p>Example: "I need CS 100 and CS 114, no Friday classes, prefer morning sessions"</p>
        </div>
      </div>

      {/* Input Area */}
      <div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe your ideal schedule..."
          disabled={isLoading}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm resize-none bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 disabled:opacity-50"
        />
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={handleParse}
          disabled={isLoading || !prompt.trim()}
          className="flex items-center gap-2 px-4 py-2 bg-njit-red hover:bg-red-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              Parsing...
            </>
          ) : (
            'Parse'
          )}
        </button>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Tip: Press Cmd/Ctrl + Enter to parse
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 flex gap-2">
          <AlertCircle size={16} className="text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Usage Display */}
      {usage && !apiKey && (
        <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
          <p>
            Daily: {usage.daily_count || 0}/{usage.daily_count + usage.daily_remaining || 5}
          </p>
          <p>
            Total: {usage.total_count || 0}/{usage.total_count + usage.total_remaining || 15}
          </p>
        </div>
      )}
    </div>
  );
}

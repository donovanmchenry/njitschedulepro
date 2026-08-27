import { Status } from '@/types';
import { getSectionStatusLabel } from '@/lib/sectionAvailability';

interface SectionStatusBadgeProps {
  status: Status | string;
  compact?: boolean;
}

export function SectionStatusBadge({ status, compact = false }: SectionStatusBadgeProps) {
  const label = getSectionStatusLabel(status);
  if (!label) return null;

  const tone = status === 'Closed'
    ? 'border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/70 dark:text-red-200'
    : 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/70 dark:text-amber-200';

  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-md border font-semibold ${tone} ${
        compact ? 'px-1 py-0.5 text-[9px]' : 'px-1.5 py-0.5 text-[10px]'
      }`}
    >
      {compact && status === 'Closed' ? 'Closed' : label}
    </span>
  );
}

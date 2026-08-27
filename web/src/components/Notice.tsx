import { AlertCircle, AlertTriangle, CheckCircle2, Info, LucideIcon } from 'lucide-react';

type NoticeTone = 'error' | 'warning' | 'success' | 'info';

interface NoticeProps {
  tone: NoticeTone;
  children: React.ReactNode;
  className?: string;
  icon?: LucideIcon;
  iconClassName?: string;
}

const toneStyles: Record<NoticeTone, string> = {
  error: 'border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200',
  warning: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200',
  info: 'border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

const toneIcons: Record<NoticeTone, LucideIcon> = {
  error: AlertCircle,
  warning: AlertTriangle,
  success: CheckCircle2,
  info: Info,
};

export function Notice({
  tone,
  children,
  className = '',
  icon,
  iconClassName = '',
}: NoticeProps) {
  const Icon = icon ?? toneIcons[tone];

  return (
    <div
      className={`flex items-start gap-2 rounded-md border px-3 py-2 text-sm ${toneStyles[tone]} ${className}`}
      role={tone === 'error' ? 'alert' : 'status'}
    >
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${iconClassName}`} />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

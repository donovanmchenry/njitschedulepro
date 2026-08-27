import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex min-h-48 items-center justify-center p-8 text-center">
      <div className="text-gray-400 dark:text-gray-500">
        <Icon className="mx-auto mb-2 h-10 w-10" strokeWidth={1.75} />
        <p className="font-semibold">{title}</p>
        <p className="mt-1 text-sm">{description}</p>
      </div>
    </div>
  );
}

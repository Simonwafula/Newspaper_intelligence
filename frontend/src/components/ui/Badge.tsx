import { ReactNode } from 'react';

type BadgeVariant = 'default' | 'blue' | 'green' | 'amber' | 'red' | 'purple';

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-stone-100 text-stone-700',
  blue: 'bg-blue-100 text-blue-800',
  green: 'bg-green-100 text-green-800',
  amber: 'bg-amber-100 text-amber-800',
  red: 'bg-red-100 text-red-800',
  purple: 'bg-purple-100 text-purple-800',
};

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
        ${variantStyles[variant]}
        ${className}
      `}
    >
      {children}
    </span>
  );
}

// Status badge specifically for Edition status
type EditionStatus = 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED' | 'ARCHIVED' | 'CANCELLED';

const statusVariants: Record<EditionStatus, BadgeVariant> = {
  UPLOADED: 'blue',
  PROCESSING: 'amber',
  READY: 'green',
  FAILED: 'red',
  ARCHIVED: 'purple',
  CANCELLED: 'red',
};

export function StatusBadge({ status }: { status: EditionStatus }) {
  return (
    <Badge variant={statusVariants[status]}>
      {status}
    </Badge>
  );
}

// Item type badge
type ItemType = 'STORY' | 'AD' | 'CLASSIFIED';

const itemTypeVariants: Record<ItemType, BadgeVariant> = {
  STORY: 'blue',
  AD: 'amber',
  CLASSIFIED: 'purple',
};

export function ItemTypeBadge({ type }: { type: ItemType }) {
  return (
    <Badge variant={itemTypeVariants[type]}>
      {type}
    </Badge>
  );
}

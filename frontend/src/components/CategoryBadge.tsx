import React from 'react';
import { Category } from '../types';

interface CategoryBadgeProps {
  category: Category;
  confidence?: number;
  showConfidence?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const CategoryBadge: React.FC<CategoryBadgeProps> = ({
  category,
  confidence,
  showConfidence = false,
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base'
  };

  return (
    <div
      className={`
        inline-flex items-center gap-1 rounded-full font-medium
        ${sizeClasses[size]}
      `}
      style={{
        backgroundColor: `${category.color}20`,
        color: category.color,
        border: `1px solid ${category.color}40`
      }}
    >
      <span>{category.name}</span>
      {showConfidence && confidence !== undefined && (
        <span className="text-xs opacity-75">
          {confidence}%
        </span>
      )}
    </div>
  );
};

interface CategoryListProps {
  categories: Array<{ category: Category; confidence?: number }>;
  showConfidence?: boolean;
  maxDisplay?: number;
  size?: 'sm' | 'md' | 'lg';
}

export const CategoryList: React.FC<CategoryListProps> = ({
  categories,
  showConfidence = false,
  maxDisplay = 3,
  size = 'sm'
}) => {
  if (!categories || categories.length === 0) {
    return null;
  }

  const displayCategories = categories.slice(0, maxDisplay);
  const hasMore = categories.length > maxDisplay;

  return (
    <div className="flex flex-wrap gap-1.5">
      {displayCategories.map((item, index) => (
        <CategoryBadge
          key={`${item.category.id}-${index}`}
          category={item.category}
          confidence={item.confidence}
          showConfidence={showConfidence}
          size={size}
        />
      ))}
      {hasMore && (
        <span className="text-xs text-gray-500 self-center">
          +{categories.length - maxDisplay} more
        </span>
      )}
    </div>
  );
};
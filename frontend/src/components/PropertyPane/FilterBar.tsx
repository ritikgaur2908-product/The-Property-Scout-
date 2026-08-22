import React from 'react';
import './FilterBar.css';

export type FilterChip = {
  key: string;
  label: string;
  value?: string;
};

interface FilterBarProps {
  activeCount: number;
  preferences?: Record<string, any>;
  onRemoveFilter?: (key: string, value?: string) => void;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  activeCount,
  preferences = {},
  onRemoveFilter,
}) => {
  const chips: FilterChip[] = [];

  if (preferences.localities?.length) {
    preferences.localities.forEach((loc: string) => {
      chips.push({ key: 'locality', label: `📍 ${loc}`, value: loc });
    });
  }
  if (preferences.min_bhk) {
    chips.push({ key: 'min_bhk', label: `🛏️ ${preferences.min_bhk}+ BHK` });
  }
  if (preferences.max_budget) {
    chips.push({
      key: 'max_budget',
      label: `💰 Max ₹${preferences.max_budget.toLocaleString('en-IN')}`,
    });
  }
  if (preferences.accommodation_type) {
    chips.push({
      key: 'accommodation_type',
      label: `🏢 ${preferences.accommodation_type === 'whole_flat' ? 'Whole Flat' : 'Shared Room'}`,
    });
  }
  if (preferences.parking) {
    chips.push({ key: 'parking', label: '🚗 Parking Required' });
  }
  if (preferences.gender && preferences.gender !== 'any') {
    chips.push({ key: 'gender', label: `👥 ${preferences.gender} only` });
  }

  return (
    <div className="filter-bar">
      <div className="filter-header">
        <h3 className="filter-title">Active Filters</h3>
        <span className="filter-count badge badge-info">
          Showing {activeCount} {activeCount === 1 ? 'property' : 'properties'}
        </span>
      </div>

      <div className="filter-active-chips" style={{ padding: '12px 16px', flexWrap: 'wrap' }}>
        {chips.length > 0 ? (
          chips.map((chip) => (
            <span
              key={`${chip.key}-${chip.value ?? chip.label}`}
              className="chip chip-active animate-fade-in"
              style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              {chip.label}
              {onRemoveFilter && (
                <button
                  type="button"
                  className="chip-remove-btn"
                  title="Remove this filter"
                  aria-label={`Remove ${chip.label}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveFilter(chip.key, chip.value);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    padding: '0 4px',
                    fontSize: '1.2em',
                    opacity: 0.7,
                    position: 'relative',
                    zIndex: 2,
                    lineHeight: 1,
                  }}
                >
                  ✕
                </button>
              )}
            </span>
          ))
        ) : (
          <span className="text-sm text-secondary">No specific filters applied yet.</span>
        )}
      </div>
    </div>
  );
};

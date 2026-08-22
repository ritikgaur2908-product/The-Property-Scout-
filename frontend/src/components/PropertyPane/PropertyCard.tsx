import React, { useState } from 'react';
import './PropertyCard.css';

interface PropertyCardProps {
  id: string;
  rent: number;
  bhk: string;
  type: string;
  address: string;
  reasoning: string;
  amenities: string[];
  neighborhoodInsights: string;
  move_in_time?: string;
  parking?: boolean;
  gender?: string;
  food?: string;
  smoking?: string;
  onBookVisit: (id: string) => void;
  onCompareToggle: (id: string) => void;
  isComparing: boolean;
}

export const PropertyCard: React.FC<PropertyCardProps & { rooms?: string }> = ({
  id, rent, bhk, type, address, reasoning = "Matched based on your preferences.", amenities, neighborhoodInsights,
  rooms, move_in_time, parking, gender, food, smoking,
  onBookVisit, onCompareToggle, isComparing
}) => {
  const [showSources, setShowSources] = useState(false);

  return (
    <div className={`card property-card ${isComparing ? 'comparing' : ''}`}>
      {/* Header */}
      <div className="property-header">
        <div>
          <h3 className="property-title">{bhk || `${rooms || ''} BHK`} {type === 'whole_flat' ? 'Whole Flat' : type === 'room_in_flat' ? 'Room' : type}</h3>
          <p className="property-address">📍 {address}</p>
        </div>
        <div className="property-price">
          ₹{rent.toLocaleString('en-IN')}<span className="text-sm text-secondary">/mo</span>
        </div>
      </div>

      {/* AI Reasoning */}
      <div className="property-reasoning">
        <span className="property-reasoning-icon">✨</span>
        <p>{reasoning}</p>
      </div>

      {/* Full Property Details Grid */}
      <div className="property-details-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '16px', fontSize: '0.85rem' }}>
        <div><span className="text-secondary">Type:</span> {type === 'whole_flat' ? 'Whole Flat' : 'Room in Flat'}</div>
        <div><span className="text-secondary">Move-in:</span> {move_in_time || 'Immediate'}</div>
        <div><span className="text-secondary">Gender:</span> {gender === 'any' ? 'Anyone' : (gender || 'Anyone')}</div>
        <div><span className="text-secondary">Parking:</span> {parking ? 'Available 🚗' : 'No Parking'}</div>
        {type === 'room_in_flat' && (
          <>
            <div><span className="text-secondary">Food:</span> {food === 'any' ? 'Any' : (food || 'Any')}</div>
            <div><span className="text-secondary">Smoking:</span> {smoking === 'any' ? 'Any' : (smoking || 'Any')}</div>
          </>
        )}
      </div>

      {/* Amenities Grid */}
      <div className="property-amenities">
        {amenities !== undefined && (
          <span className="text-xs text-secondary font-semibold mb-2 block" style={{ opacity: 0.8 }}>
            Nearby Amenities (within 1.5km)
          </span>
        )}
        {amenities === undefined ? (
          <div className="text-xs text-secondary italic mb-2 flex items-center gap-2">
            <span className="spinner-small" style={{ width: 12, height: 12, border: '2px solid #ccc', borderTopColor: '#333', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></span>
            Fetching live from OpenStreetMap...
          </div>
        ) : Array.isArray(amenities) && amenities.length > 0 ? (
          amenities.map(am => (
            <span key={am} className="badge badge-muted">
              {am}
            </span>
          ))
        ) : (
          <div className="text-xs text-secondary italic mb-2">
            No amenities found nearby.
          </div>
        )}
      </div>

      {/* Neighborhood Insights (RAG) */}
      <div className="property-neighborhood">
        <h4 className="property-neighborhood-title">Neighborhood Insights</h4>
        {neighborhoodInsights === undefined ? (
          <div className="text-xs text-secondary italic mb-2 flex items-center gap-2 mt-1">
            <span className="spinner-small" style={{ width: 12, height: 12, border: '2px solid #ccc', borderTopColor: '#333', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></span>
            Analyzing neighborhood data...
          </div>
        ) : neighborhoodInsights && neighborhoodInsights.trim().length > 0 ? (
          <>
            <p className="property-neighborhood-text" style={{ whiteSpace: 'pre-line' }}>{neighborhoodInsights}</p>
            <button 
              className="btn btn-ghost btn-sm property-sources-toggle"
              onClick={() => setShowSources(!showSources)}
            >
              {showSources ? 'Hide Sources' : 'View Sources'}
            </button>

            {showSources && (
              <div className="property-sources animate-fade-in-up">
                <p className="text-xs text-muted mb-1">Information synthesized from:</p>
                <a href="#" className="property-source-link text-xs">Verified RAG Data</a>
              </div>
            )}
          </>
        ) : (
          <div className="text-xs text-secondary italic mb-2 mt-1">
            No insights available for this specific area.
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="property-actions">
        <button 
          className="btn btn-secondary property-action-btn"
          onClick={() => onCompareToggle(id)}
        >
          {isComparing ? '✓ Added to Compare' : '⚖️ Compare'}
        </button>
        <button 
          className="btn btn-primary property-action-btn flex-2"
          onClick={() => onBookVisit(id)}
        >
          📅 Book Visit
        </button>
      </div>
    </div>
  );
};

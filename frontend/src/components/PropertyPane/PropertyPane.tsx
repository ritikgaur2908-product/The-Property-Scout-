import React, { useState } from 'react';
import { fetchApi } from '../../api/client';
import { FilterBar } from './FilterBar';
import { PropertyCard } from './PropertyCard';
import './PropertyPane.css';

export interface Property {
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
}

interface PropertyPaneProps {
  properties: Property[];
  preferences?: Record<string, any>;
  onBookVisit: (id: string) => void;
  onCompareToggle: (id: string) => void;
  comparingIds: string[];
  onShowCompare: () => void;
  onRemoveFilter?: (key: string, value?: string) => void;
}

export const PropertyPane: React.FC<PropertyPaneProps> = ({
  properties,
  preferences = {},
  onBookVisit,
  onCompareToggle,
  comparingIds,
  onShowCompare,
  onRemoveFilter,
}) => {
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [email, setEmail] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [sendSuccess, setSendSuccess] = useState(false);

  const handleEmailShortlist = async () => {
    if (!email.includes('@')) return;
    setIsSending(true);
    
    try {
      await fetchApi('/api/notify/shortlist', {
        method: 'POST',
        body: JSON.stringify({
          email: email.trim(),
          shortlist: properties
        })
      });
      
      setSendSuccess(true);
      setTimeout(() => {
        setShowEmailModal(false);
        setSendSuccess(false);
        setEmail('');
      }, 2000);
    } catch (e: any) {
      alert(e.message || "Failed to send email. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="property-pane animate-slide-in-right">
      <div className="property-pane-header">
        <h2 className="pane-title flex items-center gap-2">
          <span>🏠</span> Your Shortlist
          <span className="badge badge-info property-count">{properties.length}</span>
        </h2>
        
        <div className="flex gap-2">
          {properties.length > 0 && (
            <button className="btn btn-secondary btn-sm animate-fade-in" onClick={() => setShowEmailModal(true)}>
              📧 Email Shortlist
            </button>
          )}
          {comparingIds.length > 0 && (
            <button className="btn btn-accent btn-sm animate-fade-in" onClick={onShowCompare}>
              Compare {comparingIds.length} properties
            </button>
          )}
        </div>
      </div>

      <FilterBar
        activeCount={properties.length}
        preferences={preferences}
        onRemoveFilter={onRemoveFilter}
      />

      <div className="property-list">
        {properties.map(prop => (
          <PropertyCard
            key={prop.id}
            {...prop}
            onBookVisit={onBookVisit}
            onCompareToggle={onCompareToggle}
            isComparing={comparingIds.includes(prop.id)}
          />
        ))}
        
        {properties.length === 0 && (
          <div className="property-empty">
            <span className="property-empty-icon">🔍</span>
            <h3>No properties found</h3>
            <p className="text-secondary">Try adjusting your filters or asking the AI for broader criteria.</p>
          </div>
        )}
      </div>

      {/* Email Modal */}
      {showEmailModal && (
        <div className="overlay animate-fade-in" style={{ zIndex: 100 }}>
          <div className="modal animate-slide-up" style={{ maxWidth: '400px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Email Shortlist</h2>
              <button className="modal-close" onClick={() => setShowEmailModal(false)}>✕</button>
            </div>
            
            {sendSuccess ? (
              <div className="flex flex-col items-center text-center gap-4 py-4">
                <div className="text-4xl">📨</div>
                <h3 className="text-lg font-bold">Shortlist Sent!</h3>
                <p className="text-secondary text-sm">Your shortlist is on its way — check your inbox shortly.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <p className="text-secondary text-sm">
                  We'll send a beautiful digest of these {properties.length} properties to your email.
                </p>
                <input 
                  type="email" 
                  className="input"
                  placeholder="e.g. you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                />
                <div className="flex gap-2">
                  <button className="btn btn-secondary flex-1" onClick={() => setShowEmailModal(false)}>Cancel</button>
                  <button 
                    className="btn btn-primary flex-1" 
                    disabled={!email.includes('@') || isSending} 
                    onClick={handleEmailShortlist}
                  >
                    {isSending ? 'Sending...' : 'Send Email'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

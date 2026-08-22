import React from 'react';
import './CompareView.css';
import type { Property } from './PropertyPane'; // Assuming Property is exported from there

interface CompareViewProps {
  properties: Property[];
  onClose: () => void;
}

export const CompareView: React.FC<CompareViewProps> = ({ properties, onClose }) => {
  return (
    <div className="overlay animate-fade-in">
      <div className="modal compare-modal animate-slide-up">
        <div className="modal-header">
          <h2 className="modal-title">Compare Properties</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        
        <div className="compare-table-wrapper">
          <table className="compare-table">
            <thead>
              <tr>
                <th>Feature</th>
                {properties.map(p => (
                  <th key={p.id}>
                    <div className="compare-header-card">
                      <div className="text-sm">{p.bhk}</div>
                      <div className="text-lg text-gradient font-bold">₹{p.rent.toLocaleString('en-IN')}</div>
                      <div className="text-xs text-muted font-normal mt-1">{p.address}</div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="font-semibold text-sm">Type</td>
                {properties.map(p => <td key={p.id} className="text-sm">{p.type}</td>)}
              </tr>
              <tr>
                <td className="font-semibold text-sm">Amenities</td>
                {properties.map(p => (
                  <td key={p.id}>
                    <div className="flex flex-col gap-1">
                      {p.amenities.map(a => <span key={a} className="text-xs">• {a}</span>)}
                    </div>
                  </td>
                ))}
              </tr>
              <tr>
                <td className="font-semibold text-sm">Insights</td>
                {properties.map(p => (
                  <td key={p.id}>
                    <p className="text-xs text-secondary leading-snug">{p.neighborhoodInsights}</p>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

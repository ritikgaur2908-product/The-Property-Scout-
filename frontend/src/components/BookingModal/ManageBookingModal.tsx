import React, { useState } from 'react';

interface ManageBookingModalProps {
  onClose: () => void;
}

export const ManageBookingModal: React.FC<ManageBookingModalProps> = ({ onClose }) => {
  const [bookingId, setBookingId] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'found' | 'rescheduling' | 'cancelled'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [bookingData, setBookingData] = useState<any>(null);
  const [conflicts, setConflicts] = useState<string[]>([]);

  // Reschedule state
  const [date, setDate] = useState<string>('');
  const [time, setTime] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Map 12-hour AM/PM format to HH:MM:SS for backend
  const formatTimeForBackend = (timeStr: string) => {
    const [timeVal, modifier] = timeStr.split(' ');
    let [hours, minutes] = timeVal.split(':');
    if (hours === '12') hours = '00';
    if (modifier === 'PM') hours = String(parseInt(hours, 10) + 12);
    return `${hours.padStart(2, '0')}:${minutes}:00`;
  };

  const handleSearch = async () => {
    setStatus('loading');
    setError(null);
    try {
      const response = await fetch(`/api/bookings/${bookingId}`);
      if (response.ok) {
        const data = await response.json();
        setBookingData(data);
        setStatus('found');
      } else {
        setStatus('idle');
        setError('Booking not found. Please check your ID.');
      }
    } catch (err) {
      setStatus('idle');
      setError('Network error.');
    }
  };

  const handleReschedule = async () => {
    setIsSubmitting(true);
    setError(null);
    setConflicts([]);
    try {
      const response = await fetch(`/api/bookings/${bookingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          visit_date: date,
          visit_time: formatTimeForBackend(time)
        })
      });
      const data = await response.json();
      if (response.ok) {
        setBookingData({ ...bookingData, visit_date: data.visit_date, visit_time: data.visit_time, status: data.status });
        setStatus('found');
        alert('Rescheduled successfully!');
      } else if (response.status === 409) {
        setError(data.detail?.message || "Slot conflict.");
        setConflicts(data.detail?.alternative_slots || []);
      } else {
        setError(data.detail || "Error rescheduling.");
      }
    } catch (err) {
      setError("Network error.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`/api/bookings/${bookingId}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        setStatus('cancelled');
      } else {
        const data = await response.json();
        setError(data.detail || "Error cancelling booking.");
        setStatus('found');
      }
    } catch (err) {
      setError("Network error.");
      setStatus('found');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="overlay animate-fade-in">
      <div className="modal animate-slide-up">
        <div className="modal-header">
          <h2 className="modal-title">Manage Booking</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {status === 'idle' && (
          <div className="flex flex-col gap-4">
            <p className="text-secondary">Enter your Booking ID to view, reschedule, or cancel your visit.</p>
            <input
              type="text"
              className="input font-mono"
              placeholder="e.g. BK-A3F72K"
              value={bookingId}
              onChange={(e) => setBookingId(e.target.value.toUpperCase())}
            />
            {error && <div className="text-red-500 text-sm">{error}</div>}
            <button
              className="btn btn-primary"
              disabled={bookingId.length < 5}
              onClick={handleSearch}
            >
              Find Booking
            </button>
          </div>
        )}

        {status === 'loading' && (
          <div className="flex justify-center py-8">
            <div className="conv-speaking-indicator">
              <div className="conv-speaking-dot"></div>
              <div className="conv-speaking-dot"></div>
              <div className="conv-speaking-dot"></div>
            </div>
          </div>
        )}

        {status === 'found' && bookingData && (
          <div className="flex flex-col gap-4">
            <div className="bg-surface border border-border p-4 rounded-lg">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <div className="text-sm text-secondary">Booking ID</div>
                  <div className="font-mono font-bold text-lg">{bookingData.booking_id}</div>
                </div>
                <span className={`badge ${bookingData.status === 'cancelled' ? 'badge-danger' : 'badge-success'}`}>
                  {bookingData.status}
                </span>
              </div>

              <div className="mb-2"><strong>Property ID:</strong> {bookingData.property_id}</div>
              <div className="mb-2"><strong>Date:</strong> {bookingData.visit_date}</div>
              <div className="mb-2"><strong>Time:</strong> {bookingData.visit_time}</div>
              <div><strong>Email:</strong> {bookingData.user_email}</div>
            </div>

            {error && <div className="text-red-500 text-sm">{error}</div>}

            {bookingData.status !== 'cancelled' && (
              <div className="flex gap-2">
                <button className="btn btn-secondary flex-1" onClick={() => setStatus('rescheduling')} disabled={isSubmitting}>Reschedule</button>
                <button className="btn btn-danger flex-1" onClick={handleCancel} disabled={isSubmitting}>
                  {isSubmitting ? 'Processing...' : 'Cancel Visit'}
                </button>
              </div>
            )}
          </div>
        )}

        {status === 'rescheduling' && (
          <div className="flex flex-col gap-4">
            <h3 className="font-bold text-lg">Pick a New Time</h3>
            <input
              type="date"
              className="input"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />

            {date && (
              <div className="slot-grid">
                {['10:00 AM', '11:00 AM', '12:00 PM', '02:00 PM', '03:00 PM', '04:00 PM', '05:00 PM'].map((slot) => (
                  <button
                    key={slot}
                    className={`slot ${time === slot ? 'slot-selected' : ''}`}
                    onClick={() => setTime(slot)}
                  >
                    {slot}
                  </button>
                ))}
              </div>
            )}

            {error && (
              <div className="text-red-500 text-sm mt-2 p-2 bg-red-100 rounded">
                {error}
                {conflicts.length > 0 && (
                  <div className="mt-1 font-mono text-xs text-red-700">Alternative times: {conflicts.join(', ')}</div>
                )}
              </div>
            )}

            <div className="flex gap-2 mt-4">
              <button className="btn btn-secondary flex-1" onClick={() => { setStatus('found'); setError(null); }}>Back</button>
              <button
                className="btn btn-primary flex-1"
                disabled={!date || !time || isSubmitting}
                onClick={handleReschedule}
              >
                {isSubmitting ? 'Processing...' : 'Confirm New Time'}
              </button>
            </div>
          </div>
        )}

        {status === 'cancelled' && (
          <div className="flex flex-col items-center text-center gap-4 py-4">
            <div className="text-5xl">🚫</div>
            <h3 className="text-xl font-bold">Booking Cancelled</h3>
            <p className="text-secondary">Your site visit has been successfully cancelled.</p>
            <button className="btn btn-primary w-full mt-4" onClick={onClose}>Close</button>
          </div>
        )}
      </div>
    </div>
  );
};

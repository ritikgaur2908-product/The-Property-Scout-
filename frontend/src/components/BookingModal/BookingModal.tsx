import React, { useState } from 'react';

interface BookingModalProps {
  propertyId: string;
  onClose: () => void;
}

export const BookingModal: React.FC<BookingModalProps> = ({ propertyId, onClose }) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [date, setDate] = useState<string>('');
  const [time, setTime] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bookingId, setBookingId] = useState<string>('');
  const [conflicts, setConflicts] = useState<string[]>([]);

  // Map 12-hour AM/PM format to HH:MM:SS for backend
  const formatTimeForBackend = (timeStr: string) => {
    const [time, modifier] = timeStr.split(' ');
    let [hours, minutes] = time.split(':');
    if (hours === '12') hours = '00';
    if (modifier === 'PM') hours = String(parseInt(hours, 10) + 12);
    return `${hours.padStart(2, '0')}:${minutes}:00`;
  };

  const handleConfirm = async () => {
    setIsSubmitting(true);
    setError(null);
    setConflicts([]);
    
    try {
      const response = await fetch('/api/bookings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          property_id: propertyId,
          email: email,
          visit_date: date,
          visit_time: formatTimeForBackend(time)
        })
      });

      const data = await response.json();

      if (response.ok) {
        setBookingId(data.booking_id);
        setStep(4);
      } else if (response.status === 409) {
        setError(data.detail?.message || "Slot conflict.");
        setConflicts(data.detail?.alternative_slots || []);
      } else {
        setError(data.detail || "An error occurred.");
      }
    } catch (err) {
      setError("Network error, please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="overlay animate-fade-in">
      <div className="modal animate-slide-up">
        <div className="modal-header">
          <h2 className="modal-title">Book a Visit</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {/* Stepper */}
        <div className="stepper">
          <div className={`stepper-circle ${step >= 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}>1</div>
          <div className={`stepper-line ${step > 1 ? 'completed' : ''}`}></div>
          <div className={`stepper-circle ${step >= 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`}>2</div>
          <div className={`stepper-line ${step > 2 ? 'completed' : ''}`}></div>
          <div className={`stepper-circle ${step >= 3 ? 'active' : ''} ${step > 3 ? 'completed' : ''}`}>3</div>
        </div>

        {/* Step 1: Date */}
        {step === 1 && (
          <div className="flex flex-col gap-4">
            <p className="text-secondary">When would you like to visit property {propertyId}?</p>
            <input 
              type="date" 
              className="input"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              min={new Date().toISOString().split('T')[0]}
            />
            <button 
              className="btn btn-primary" 
              disabled={!date} 
              onClick={() => setStep(2)}
            >
              Next →
            </button>
          </div>
        )}

        {/* Step 2: Time */}
        {step === 2 && (
          <div className="flex flex-col gap-4">
            <p className="text-secondary">Available slots for {date}</p>
            <div className="slot-grid">
              {['10:00 AM', '11:00 AM', '12:00 PM', '02:00 PM', '03:00 PM', '04:00 PM', '05:00 PM'].map((slot) => {
                return (
                  <button 
                    key={slot}
                    className={`slot ${time === slot ? 'slot-selected' : ''}`}
                    onClick={() => setTime(slot)}
                  >
                    {slot}
                  </button>
                )
              })}
            </div>
            <div className="flex gap-2">
              <button className="btn btn-secondary flex-1" onClick={() => setStep(1)}>← Back</button>
              <button className="btn btn-primary flex-1" disabled={!time} onClick={() => setStep(3)}>Next →</button>
            </div>
          </div>
        )}

        {/* Step 3: Email */}
        {step === 3 && (
          <div className="flex flex-col gap-4">
            <p className="text-secondary">Where should we send your booking confirmation?</p>
            <input 
              type="email" 
              className="input"
              placeholder="e.g. you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            
            {error && (
              <div className="text-red-500 text-sm mt-2 p-2 bg-red-100 rounded">
                {error}
                {conflicts.length > 0 && (
                  <div className="mt-1 font-mono text-xs text-red-700">Alternative times: {conflicts.join(', ')}</div>
                )}
              </div>
            )}
            
            <div className="flex gap-2">
              <button className="btn btn-secondary flex-1" onClick={() => setStep(2)}>← Back</button>
              <button className="btn btn-primary flex-1" disabled={!email.includes('@') || isSubmitting} onClick={handleConfirm}>
                {isSubmitting ? 'Confirming...' : 'Confirm Visit'}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Success */}
        {step === 4 && (
          <div className="flex flex-col items-center text-center gap-4 py-4">
            <div className="text-5xl">✅</div>
            <h3 className="text-xl font-bold">Visit Confirmed!</h3>
            
            <div className="bg-surface border border-border p-4 rounded-lg w-full text-left">
              <div className="text-sm text-secondary mb-1">Your Booking ID</div>
              <div className="text-lg font-mono font-bold text-accent mb-4">{bookingId}</div>
              
              <div className="text-sm mb-1">📅 {date} at {time}</div>
              <div className="text-sm mb-1">📧 Confirmation sent to {email}</div>
            </div>
            
            <p className="text-xs text-muted">Save your Booking ID. You'll need it if you want to reschedule or cancel.</p>
            
            <button className="btn btn-primary w-full" onClick={onClose}>Done</button>
          </div>
        )}
      </div>
    </div>
  );
};

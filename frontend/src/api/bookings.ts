import { fetchApi } from './client';

export interface BookingRequest {
  property_id: string;
  email?: string;
  user_email?: string;
  visit_date: string;
  visit_time: string;
}

export interface BookingResponse {
  id?: string;
  booking_id: string;
  user_id: string;
  property_id: string;
  user_email: string;
  visit_date: string;
  visit_time: string;
  status: string;
}

export const BookingAPI = {
  createBooking: async (data: BookingRequest): Promise<BookingResponse> => {
    const payload = {
      property_id: data.property_id,
      email: (data.email || data.user_email || '').trim(),
      visit_date: data.visit_date,
      visit_time: data.visit_time,
    };
    return fetchApi<BookingResponse>('/api/bookings', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getBooking: async (bookingId: string): Promise<any> => {
    return fetchApi<any>(`/api/bookings/${bookingId}`);
  },

  rescheduleBooking: async (bookingId: string, data: { visit_date: string; visit_time: string }): Promise<any> => {
    return fetchApi<any>(`/api/bookings/${bookingId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  cancelBooking: async (bookingId: string): Promise<any> => {
    return fetchApi<any>(`/api/bookings/${bookingId}`, {
      method: 'DELETE',
    });
  },
};

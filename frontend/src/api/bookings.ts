import { fetchApi } from './client';

export interface BookingRequest {
  property_id: string;
  user_email: string;
  visit_date: string;
  visit_time: string;
}

export interface BookingResponse {
  booking_id: string;
  user_id: string;
  status: string;
}

export const BookingAPI = {
  createBooking: async (data: BookingRequest): Promise<BookingResponse> => {
    return fetchApi<BookingResponse>('/api/bookings', {
      method: 'POST',
      body: JSON.stringify(data),
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

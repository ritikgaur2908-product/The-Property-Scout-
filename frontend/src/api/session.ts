import { fetchApi } from './client';

export interface SessionResponse {
  session_id: string;
}

export const SessionAPI = {
  createSession: async (): Promise<SessionResponse> => {
    return fetchApi<SessionResponse>('/api/session', {
      method: 'POST',
      body: '{}',
    });
  },

  getSession: async (sessionId: string): Promise<any> => {
    return fetchApi<any>(`/api/session/${sessionId}`);
  },

  sendMessage: async (sessionId: string, message: string): Promise<any> => {
    return fetchApi<any>(`/api/session/${sessionId}/message`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },

  removeFilter: async (
    sessionId: string,
    key: string,
    value?: string
  ): Promise<{ preferences: Record<string, any>; shortlist: any[] }> => {
    return fetchApi(`/api/session/${sessionId}/remove-filter`, {
      method: 'POST',
      body: JSON.stringify({ key, value }),
    });
  },
};

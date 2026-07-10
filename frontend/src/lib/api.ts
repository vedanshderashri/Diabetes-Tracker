/**
 * MedAI Assistant - API Client
 * Centralized API communication layer with auth token management.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  isFormData?: boolean;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('medai_access_token');
  }

  setToken(token: string): void {
    localStorage.setItem('medai_access_token', token);
  }

  setRefreshToken(token: string): void {
    localStorage.setItem('medai_refresh_token', token);
  }

  clearTokens(): void {
    localStorage.removeItem('medai_access_token');
    localStorage.removeItem('medai_refresh_token');
    localStorage.removeItem('medai_user');
  }

  getUser(): any {
    if (typeof window === 'undefined') return null;
    const user = localStorage.getItem('medai_user');
    return user ? JSON.parse(user) : null;
  }

  setUser(user: any): void {
    localStorage.setItem('medai_user', JSON.stringify(user));
  }

  async request<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
    const { method = 'GET', body, headers = {}, isFormData = false } = options;

    const token = this.getToken();
    const requestHeaders: Record<string, string> = {
      ...headers,
    };

    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
    }

    if (!isFormData) {
      requestHeaders['Content-Type'] = 'application/json';
    }

    const config: RequestInit = {
      method,
      headers: requestHeaders,
      ...(method === 'GET' ? { cache: 'no-store' } : {}),
    };

    if (body) {
      config.body = isFormData ? (body as FormData) : JSON.stringify(body);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, config);

    if (response.status === 401) {
      // Try refresh token
      const refreshed = await this.refreshToken();
      if (refreshed) {
        // Retry original request
        requestHeaders['Authorization'] = `Bearer ${this.getToken()}`;
        const retryResponse = await fetch(`${this.baseUrl}${endpoint}`, {
          ...config,
          headers: requestHeaders,
        });
        if (!retryResponse.ok) {
          throw new ApiError(retryResponse.status, await retryResponse.text());
        }
        if (retryResponse.status === 204) {
          return null as any;
        }
        return retryResponse.json();
      } else {
        this.clearTokens();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        throw new ApiError(401, 'Session expired');
      }
    }

    if (!response.ok) {
      let errorMessage = 'An error occurred';
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        errorMessage = await response.text();
      }
      throw new ApiError(response.status, errorMessage);
    }

    if (response.status === 204) {
      return null as any;
    }

    return response.json();
  }

  private async refreshToken(): Promise<boolean> {
    const refreshToken = localStorage.getItem('medai_refresh_token');
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        this.setToken(data.access_token);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  // ── Auth ──────────────────────────────────────────────────────────────
  async register(data: { email: string; password: string; full_name: string; phone?: string; language_preference?: string }) {
    const result = await this.request<any>('/api/v1/auth/register', { method: 'POST', body: data });
    this.setToken(result.access_token);
    this.setRefreshToken(result.refresh_token);
    this.setUser(result.user);
    return result;
  }

  async login(email: string, password: string) {
    const result = await this.request<any>('/api/v1/auth/login', { method: 'POST', body: { email, password } });
    this.setToken(result.access_token);
    this.setRefreshToken(result.refresh_token);
    this.setUser(result.user);
    return result;
  }

  async getMe() {
    return this.request<any>('/api/v1/auth/me');
  }

  async updateAccount(data: { full_name?: string; phone?: string; language_preference?: string; password?: string }) {
    return this.request<any>('/api/v1/auth/me', {
      method: 'PUT',
      body: data,
    });
  }

  async deleteAccount() {
    return this.request<any>('/api/v1/auth/me', {
      method: 'DELETE',
    });
  }

  logout(): void {
    this.clearTokens();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }

  // ── Chat ──────────────────────────────────────────────────────────────
  async createChatSession(title?: string, language?: string) {
    return this.request<any>('/api/v1/chat/sessions', {
      method: 'POST',
      body: { title: title || 'New Conversation', language: language || 'en' },
    });
  }

  async getChatSessions() {
    return this.request<any[]>('/api/v1/chat/sessions');
  }

  async getChatMessages(sessionId: string) {
    return this.request<any[]>(`/api/v1/chat/sessions/${sessionId}/messages`);
  }

  async sendMessage(sessionId: string, content: string) {
    return this.request<any>(`/api/v1/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: { content },
    });
  }

  async deleteChatSession(sessionId: string) {
    return this.request<any>(`/api/v1/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  async clearAllChatSessions() {
    return this.request<any>('/api/v1/chat/sessions', {
      method: 'DELETE',
    });
  }

  // ── Reports ───────────────────────────────────────────────────────────
  async extractDocumentText(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.request<any>('/api/v1/reports/extract', {
      method: 'POST',
      body: formData,
      isFormData: true,
    });
  }

  async uploadReport(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.request<any>('/api/v1/reports/upload', {
      method: 'POST',
      body: formData,
      isFormData: true,
    });
  }

  async getReports() {
    return this.request<any[]>('/api/v1/reports');
  }

  async getReport(reportId: string) {
    return this.request<any>(`/api/v1/reports/${reportId}`);
  }

  async deleteReport(reportId: string) {
    return this.request<any>(`/api/v1/reports/${reportId}`, {
      method: 'DELETE',
    });
  }

  async clearAllReports() {
    return this.request<any>('/api/v1/reports', {
      method: 'DELETE',
    });
  }

  // ── Predictions ───────────────────────────────────────────────────────
  async predictSymptoms(data: { symptoms: string[]; age?: number; gender?: string }) {
    return this.request<any>('/api/v1/prediction/symptoms', { method: 'POST', body: data });
  }

  async predictDiabetesRisk(data: any) {
    return this.request<any>('/api/v1/prediction/diabetes-risk', { method: 'POST', body: data });
  }

  // ── Patient Profile ───────────────────────────────────────────────────
  async getProfile() {
    return this.request<any>('/api/v1/patients/profile');
  }

  async updateProfile(data: any) {
    return this.request<any>('/api/v1/patients/profile', { method: 'PUT', body: data });
  }

  async getMedicalHistory() {
    return this.request<any[]>('/api/v1/patients/medical-history');
  }

  async addMedicalHistory(data: any) {
    return this.request<any>('/api/v1/patients/medical-history', { method: 'POST', body: data });
  }

  async getMedications() {
    return this.request<any[]>('/api/v1/patients/medications');
  }

  async addMedication(data: any) {
    return this.request<any>('/api/v1/patients/medications', { method: 'POST', body: data });
  }

  async getAllergies() {
    return this.request<any[]>('/api/v1/patients/allergies');
  }

  async addAllergy(data: any) {
    return this.request<any>('/api/v1/patients/allergies', { method: 'POST', body: data });
  }

  async deleteMedication(medicationId: string) {
    return this.request<any>(`/api/v1/patients/medications/${medicationId}`, { method: 'DELETE' });
  }

  async deleteMedicalHistory(historyId: string) {
    return this.request<any>(`/api/v1/patients/medical-history/${historyId}`, { method: 'DELETE' });
  }

  async deleteAllergy(allergyId: string) {
    return this.request<any>(`/api/v1/patients/allergies/${allergyId}`, { method: 'DELETE' });
  }


  // ── Dashboard ─────────────────────────────────────────────────────────
  async getDashboard() {
    return this.request<any>('/api/v1/dashboard');
  }

  // ── Doctor Summary ────────────────────────────────────────────────────
  async generateDoctorSummary(data?: any) {
    return this.request<any>('/api/v1/summary/generate', {
      method: 'POST',
      body: data || { include_reports: true, include_chat_history: true },
    });
  }

  // ── Admin ─────────────────────────────────────────────────────────────
  async getAdminUsers(page = 1) {
    return this.request<any>(`/api/v1/admin/users?page=${page}`);
  }

  async getAdminAnalytics() {
    return this.request<any>('/api/v1/admin/analytics');
  }

  async getSystemHealth() {
    return this.request<any>('/api/v1/admin/system');
  }
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

export const api = new ApiClient(API_BASE);
export { ApiError };

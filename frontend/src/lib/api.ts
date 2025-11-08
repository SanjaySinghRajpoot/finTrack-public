// const API_BASE_URL = "http://localhost:8000/api";

interface ImportMeta {
  env: {
    VITE_API_BASE_URL: string;
  };
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Cookie utilities
const JWT_COOKIE_NAME = "expense_tracker_jwt";

export const setJwtCookie = (jwt: string) => {
  document.cookie = `${JWT_COOKIE_NAME}=${jwt}; path=/; max-age=${60 * 60 * 24 * 7}`; // 7 days
};

export const getJwtCookie = (): string | null => {
  const cookies = document.cookie.split(';');

  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === JWT_COOKIE_NAME) {
      return value;
    }
  }
  return null;
};

export const clearJwtCookie = () => {
  document.cookie = `${JWT_COOKIE_NAME}=; path=/; max-age=0`;
};

// Helper to get auth headers
const getAuthHeaders = (): HeadersInit => {
  const jwt = getJwtCookie();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  return headers;
};

export interface Expense {
  uuid: string;
  user_id: number;
  currency: string;
  description: string;
  id: number;
  amount: number;
  category: string;
  created_at: string;
}

export interface CreateExpenseRequest {
  amount: number;
  currency: string;
  category: string;
  description: string;
  is_import?: boolean;
  processed_data_id?: number;
}

export interface ImportedExpense {
  id: number;
  reference_id: string | null;
  vendor_name: string;
  created_at: string;
  user_id: number;
  issue_date: string | null;
  vendor_gstin: string | null;
  updated_at: string | null;
  source_id: number;
  due_date: string | null;
  category: string | null;
  email_id: string | null;
  payment_date: string | null;
  tags: string[];
  document_type: string;
  amount: number;
  file_url: string | null;
  title: string;
  currency: string;
  meta_data: string[];
  description: string;
  is_paid: boolean;
  is_imported: boolean;
  document_number: string | null;
  payment_method: string | null;
  source: {
    type: string;
    external_id: string;
    id: number;
    created_at: string;
  };
  attachment: {
    user_id: number;
    source_id: number;
    filename: string;
    size: number;
    storage_path: string | null;
    extracted_text: string;
    id: number;
    attachment_id: string;
    mime_type: string;
    file_hash: string;
    s3_url: string;
    created_at: string;
  } | null;
  processed_items: ProcessedItem[];
}

export interface ProcessedItem {
  id: number;
  processed_email_id: number;
  category: string | null;
  item_name: string;
  item_code: string | null;
  unit: string | null;
  quantity: number;
  rate: number;
  discount: number;
  tax_percent: number;
  total_amount: number;
  currency: string;
  meta_data: Record<string, string>;
  created_at: string;
  updated_at: string | null;
}

export interface AuthResponse {
  jwt: string;
  google_access_token: string;
  google_refresh_token: string;
  expires_in: number;
  user: {
    id: number;
    email: string;
  };
}

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  locale: string;
  profile_image: string | null;
  country: string;
  created_at: string;
  updated_at: string;
}

export interface UpdateUserDetailsPayload {
  first_name?: string;
  last_name?: string;
  profile_image?: string;
  country?: string;
  locale?: string;
}

export interface Feature {
  feature_key: string;
  display_name: string;
  description: string;
  category: string;
  credit_cost: number;
  can_use: boolean;
  usage_reason: string;
  execution_order: number | null;
}

export interface Integration {
  integration_id: string;
  integration_type: string;
  status: string;
  error_message: string | null;
  last_synced_at: string | null;
  next_sync_at: string | null;
  sync_interval_minutes: number;
  last_sync_duration: number | null;
  total_syncs: number;
  created_at: string;
  updated_at: string;
  integration_name: string;
  integration_slug: string;
  provider: string;
  category: string;
  description: string;
  icon_url: string;
  features: Feature[];
  can_use_integration: boolean;
  usage_reason: string;
  primary_feature: Feature;
}

export interface Subscription {
  has_subscription: boolean;
  credit_balance: number;
  plan_name: string;
  plan_slug: string;
  subscription_status: string;
  expires_at: string;
  auto_renewal: boolean;
}

export interface Credits {
  current_balance: number;
  total_allocated: number;
  credits_used: number;
  usage_percentage: number;
}

export interface UserSettings {
  integrations: Integration[];
  subscription: Subscription;
  features: Record<string, Feature>;
  credits: Credits;
}

export interface UploadSuccessData {
  success: boolean;
  attachment_id: number;
  manual_upload_id: number;
  filename: string;
  s3_key: string;
  file_size: number;
  document_type: string;
}

export interface UploadSuccessResponse {
  message: string;
  data: UploadSuccessData;
}

export interface UploadErrorResponse {
  error: string;
}

export const api = {
  // Auth
  login: () => {
    // Since the backend returns JSON directly, we need to use full page redirect
    window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=1053645079359-f1vdjlvg1q7hcta1fji9s8b60ucgl9pu.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Femails%2Foauth2callback&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile&access_type=offline&prompt=consent`;
  },

  logout: () => {
    clearJwtCookie();
  },

  // Expenses
  getExpenses: async (): Promise<Expense[]> => {
    const response = await fetch(`${API_BASE_URL}/expense`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch expenses');
    const result = await response.json();

    return result.data
  },

  getExpense: async (id: string): Promise<Expense> => {
    const response = await fetch(`${API_BASE_URL}/expense/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch expense');
    return response.json();
  },

  createExpense: async (data: CreateExpenseRequest): Promise<Expense> => {
    const response = await fetch(`${API_BASE_URL}/expense`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create expense');
    return response.json();
  },

  updateExpense: async (id: string, data: Partial<CreateExpenseRequest>): Promise<Expense> => {
    const response = await fetch(`${API_BASE_URL}/expense/${id}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update expense');
    return response.json();
  },

  deleteExpense: async (id: number): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/expense/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to delete expense');
  },

  // Imported Expenses
  getImportedExpenses: async (): Promise<ImportedExpense[]> => {
    const response = await fetch(`${API_BASE_URL}/processed-expense/info`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch imported expenses');
    const result = await response.json();

    return result.data
  },

  // User
  getUser: async (): Promise<User> => {
    const response = await fetch(`${API_BASE_URL}/user`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch user');
    return response.json();
  },

  updateUser: async (data: UpdateUserDetailsPayload): Promise<User> => {
    const response = await fetch(`${API_BASE_URL}/user`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update user details');
    return response.json();
  },

  // Settings
  getUserSettings: async (): Promise<UserSettings> => {
    const response = await fetch(`${API_BASE_URL}/user/settings`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch user settings');
    return response.json();
  },

  // File Upload
  uploadFile: async (file: File, documentType: string = "INVOICE", uploadNotes?: string): Promise<UploadSuccessResponse> => {
    const jwt = getJwtCookie();
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (uploadNotes) {
      formData.append('upload_notes', uploadNotes);
    }

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers: {
        'Authorization': jwt ? `Bearer ${jwt}` : '',
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to upload file');
    }

    return response.json();
  },

  // Attachment
  getAttachmentSignedUrl: async (s3Url: string): Promise<{ url: string }> => {
    const response = await fetch(`${API_BASE_URL}/attachment/view?s3_url=${encodeURIComponent(s3Url)}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch attachment signed URL');
    return response.json();
  },
};

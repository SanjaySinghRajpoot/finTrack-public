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
  // Get the current domain
  const hostname = window.location.hostname;
  
  // For production domains (not localhost), extract the root domain
  let domain = '';
  if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
    domain = `; domain=${hostname}`;
  }
  
  // Clear cookie with multiple attempts to ensure it's removed
  // 1. Clear with domain and path
  document.cookie = `${JWT_COOKIE_NAME}=; path=/; max-age=0${domain}`;
  
  // 2. Clear without domain (for localhost)
  document.cookie = `${JWT_COOKIE_NAME}=; path=/; max-age=0`;
  
  // 3. Set expires to past date as fallback
  document.cookie = `${JWT_COOKIE_NAME}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT${domain}`;
  document.cookie = `${JWT_COOKIE_NAME}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
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
  source_id: number | null;
  updated_at: string | null;
  deleted_at: string | null;
  processed_data?: ImportedExpense[];
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
  meta_data: {
    custom_fields?: Record<string, any>;
  } & Record<string, any>;
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

export interface FileUploadRequest {
  filename: string;
  content_type: string;
  file_hash: string;
  file_size: number;
}

export interface PresignedUrlRequest {
  files: FileUploadRequest[];
}

export interface PresignedUrlData {
  filename: string;
  file_hash: string;
  presigned_url: string | null;
  s3_key: string | null;
  remark: string; // 'success' or 'duplicate'
  duplicate_attachment_id: number | null;
}

export interface PresignedUrlResponse {
  message: string;
  data: PresignedUrlData[];
}

export interface FileMetadata {
  filename: string;
  file_hash: string;
  s3_key: string;
  file_size: number;
  content_type: string;
  document_type?: string;
  upload_notes?: string;
}

export interface FileMetadataRequest {
  files: FileMetadata[];
}

export interface ProcessedFileData {
  filename: string;
  file_hash: string;
  attachment_id: number;
  manual_upload_id: number;
  status: string; // 'created', 'existing', or 'queued_for_processing'
}

export interface FileMetadataResponse {
  message: string;
  data: ProcessedFileData[];
}

// Staging Documents Types
export interface StagingDocument {
  id: number;
  uuid: string;
  filename: string;
  file_hash: string | null;
  s3_key: string | null;
  mime_type: string | null;
  file_size: number | null;
  document_type: string | null;
  source_type: string;
  upload_notes: string | null;
  processing_status: string;
  processing_attempts: number;
  max_attempts: number;
  error_message: string | null;
  meta_data: Record<string, unknown> | null;
  priority: number;
  created_at: string | null;
  updated_at: string | null;
  processing_started_at: string | null;
  processing_completed_at: string | null;
  source: {
    id: number;
    type: string;
    external_id: string | null;
    created_at: string | null;
  } | null;
}

export interface StagingDocumentsPagination {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface StagingDocumentsResponse {
  data: StagingDocument[];
  pagination: StagingDocumentsPagination;
}

// Custom Schema Types
export interface CustomFieldDefinition {
  name: string;
  label: string;
  type: string; // 'string' | 'number' | 'date' | 'boolean' | 'select' | 'array'
  required: boolean;
  default_value?: unknown;
  options?: string[];
  description?: string;
  order?: number;
}

export interface DefaultSchemaField {
  name: string;
  label: string;
  type: string;
  required: boolean;
  source: string; // 'default' or 'custom'
  description?: string;
}

export interface CustomSchemaCreate {
  fields: CustomFieldDefinition[];
  schema_name?: string;
  description?: string;
  is_active?: boolean;
}

export interface CustomSchemaUpdate {
  fields?: CustomFieldDefinition[];
  schema_name?: string;
  description?: string;
  is_active?: boolean;
}

export interface CustomSchemaResponse {
  id: number;
  user_id: number;
  fields: CustomFieldDefinition[];
  schema_name: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface FullSchemaResponse {
  default_fields: DefaultSchemaField[];
  custom_fields: CustomFieldDefinition[];
  schema_name: string | null;
  description: string | null;
  is_active: boolean;
  has_custom_schema: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

export const api = {
  // Auth
  login: async () => {
    // Fetch the auth URL from the backend
    const response = await fetch(`${API_BASE_URL}/login`);
    if (!response.ok) throw new Error('Failed to get login URL');
    const { auth_url } = await response.json();
    
    // Redirect to the Google OAuth URL
    window.location.href = auth_url;
  },

  logout: () => {
    clearJwtCookie();
  },

  // Expenses
  getExpenses: async (limit: number = 10, offset: number = 0): Promise<PaginatedResponse<Expense>> => {
    // Ensure parameters are integers
    const intLimit = Math.floor(Number(limit));
    const intOffset = Math.floor(Number(offset));
    
    const params = new URLSearchParams({
      limit: String(intLimit),
      offset: String(intOffset),
    });
    
    const response = await fetch(`${API_BASE_URL}/expense?${params.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch expenses');
    const result = await response.json();

    // Transform backend response to match our pagination format
    return {
      data: result.data || [],
      pagination: {
        total: result.pagination?.total || result.total || result.data?.length || 0,
        limit: intLimit,
        offset: intOffset,
        has_more: result.pagination?.has_more || result.has_more || false,
      }
    };
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

  deleteExpense: async (uuid: string): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/expense/${uuid}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to delete expense');
  },

  // Imported Expenses
  getImportedExpenses: async (limit: number = 10, offset: number = 0): Promise<PaginatedResponse<ImportedExpense>> => {
    // Ensure parameters are integers
    const intLimit = Math.floor(Number(limit));
    const intOffset = Math.floor(Number(offset));
    
    const params = new URLSearchParams({
      limit: String(intLimit),
      offset: String(intOffset),
    });
    
    const response = await fetch(`${API_BASE_URL}/processed-expense/info?${params.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch imported expenses');
    const result = await response.json();

    // Transform backend response to match our pagination format
    return {
      data: result.data || [],
      pagination: {
        total: result.pagination?.total || result.total || result.data?.length || 0,
        limit: intLimit,
        offset: intOffset,
        has_more: result.pagination?.has_more || result.has_more || false,
      }
    };
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

  // New presigned URL upload flow
  getPresignedUrls: async (request: PresignedUrlRequest): Promise<PresignedUrlResponse> => {
    const response = await fetch(`${API_BASE_URL}/files/presigned-urls`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get presigned URLs');
    }

    return response.json();
  },

  submitFileMetadata: async (request: FileMetadataRequest): Promise<FileMetadataResponse> => {
    const response = await fetch(`${API_BASE_URL}/files/metadata`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to submit file metadata');
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

  // Integrations
  linkIntegration: async (slug: string): Promise<{ auth_url: string }> => {
    const response = await fetch(`${API_BASE_URL}/integration/${slug}/link`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to initiate integration linking');
    return response.json();
  },

  delinkIntegration: async (slug: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE_URL}/integration/${slug}/delink`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to delink integration');
    return response.json();
  },

  // Staging Documents
  getStagingDocuments: async (
    limit: number = 10,
    offset: number = 0,
    status?: string
  ): Promise<StagingDocumentsResponse> => {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    if (status) {
      params.append('status', status);
    }

    const response = await fetch(`${API_BASE_URL}/staging-documents?${params.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch staging documents');
    return response.json();
  },

  // Custom Schema
  getDocumentSchema: async (): Promise<FullSchemaResponse> => {
    const response = await fetch(`${API_BASE_URL}/schema`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch document schema');
    return response.json();
  },

  saveCustomSchema: async (data: CustomSchemaCreate): Promise<{ message: string; data: CustomSchemaResponse }> => {
    const response = await fetch(`${API_BASE_URL}/schema/custom`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to save custom schema');
    return response.json();
  },

  updateCustomSchema: async (data: CustomSchemaUpdate): Promise<{ message: string; data: CustomSchemaResponse }> => {
    const response = await fetch(`${API_BASE_URL}/schema/custom`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update custom schema');
    return response.json();
  },

  deleteCustomSchema: async (): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE_URL}/schema/custom`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to delete custom schema');
    return response.json();
  },
};

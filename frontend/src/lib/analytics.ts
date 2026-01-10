import { usePostHog } from 'posthog-js/react';
import { useCallback } from 'react';

// Define event names as constants for consistency
export const EVENTS = {
  // Authentication events
  LOGIN_INITIATED: 'login_initiated',
  LOGIN_SUCCESS: 'login_success',
  LOGOUT: 'logout',
  
  // Expense events
  EXPENSE_CREATED: 'expense_created',
  EXPENSE_UPDATED: 'expense_updated',
  EXPENSE_DELETED: 'expense_deleted',
  EXPENSE_FORM_OPENED: 'expense_form_opened',
  EXPENSE_FORM_CANCELLED: 'expense_form_cancelled',
  
  // File events
  FILE_UPLOADED: 'file_uploaded',
  FILE_DELETED: 'file_deleted',
  FILE_DOWNLOADED: 'file_downloaded',
  FILE_VIEWED: 'file_viewed',
  IMAGE_CAPTURED: 'image_captured',
  
  // Gmail integration events
  GMAIL_CONNECT_INITIATED: 'gmail_connect_initiated',
  GMAIL_CONNECTED: 'gmail_connected',
  GMAIL_DISCONNECTED: 'gmail_disconnected',
  GMAIL_SYNC: 'gmail_sync',
  
  // Navigation events
  PAGE_VIEW: 'page_view',
  NAVIGATION: 'navigation',
  
  // Export events
  EXPORT_INITIATED: 'export_initiated',
  EXPORT_COMPLETED: 'export_completed',
  
  // Settings events
  SETTINGS_UPDATED: 'settings_updated',
  THEME_CHANGED: 'theme_changed',
  
  // Search and filter events
  SEARCH_PERFORMED: 'search_performed',
  FILTER_APPLIED: 'filter_applied',
  
  // Chart interactions
  CHART_VIEWED: 'chart_viewed',
  CHART_INTERACTED: 'chart_interacted',
  
  // NEW: Custom events added
  IMPORTED_SECTION_CLICKED: 'imported_section_clicked',
  SCHEMA_BUTTON_CLICKED: 'schema_button_clicked',
  EXPORT_BUTTON_CLICKED: 'export_button_clicked',
  FILE_INFO_VIEWED: 'file_info_viewed',
  PROFILE_EDIT_INITIATED: 'profile_edit_initiated',
  PROFILE_UPDATE_ATTEMPTED: 'profile_update_attempted',
  PROFILE_UPDATE_SUCCESS: 'profile_update_success',
  PROFILE_UPDATE_FAILED: 'profile_update_failed',
  PROFILE_EDIT_CANCELLED: 'profile_edit_cancelled',
} as const;

// Custom hook for analytics
export const useAnalytics = () => {
  const posthog = usePostHog();

  const trackEvent = useCallback((
    eventName: string,
    properties?: Record<string, any>
  ) => {
    if (!posthog) return;
    
    posthog.capture(eventName, {
      ...properties,
      timestamp: new Date().toISOString(),
    });
  }, [posthog]);

  const identifyUser = useCallback((
    userId: string,
    properties?: Record<string, any>
  ) => {
    if (!posthog) return;
    
    posthog.identify(userId, properties);
  }, [posthog]);

  const setUserProperties = useCallback((
    properties: Record<string, any>
  ) => {
    if (!posthog) return;
    
    posthog.setPersonProperties(properties);
  }, [posthog]);

  const resetUser = useCallback(() => {
    if (!posthog) return;
    
    posthog.reset();
  }, [posthog]);

  const trackPageView = useCallback((
    pageName: string,
    properties?: Record<string, any>
  ) => {
    if (!posthog) return;
    
    posthog.capture(EVENTS.PAGE_VIEW, {
      page_name: pageName,
      ...properties,
    });
  }, [posthog]);

  return {
    trackEvent,
    identifyUser,
    setUserProperties,
    resetUser,
    trackPageView,
    posthog,
  };
};

// Utility function for tracking errors
export const trackError = (
  posthog: any,
  error: Error,
  context?: Record<string, any>
) => {
  if (!posthog) return;
  
  posthog.capture('error_occurred', {
    error_message: error.message,
    error_stack: error.stack,
    ...context,
  });
};

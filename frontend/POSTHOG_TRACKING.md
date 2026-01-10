# PostHog Event Tracking Implementation Guide

This guide explains how PostHog event tracking is implemented in the FinTrack application and how to add tracking to new features.

## Setup

PostHog is already initialized in `main.tsx` with the `PostHogProvider` wrapper.

## Custom Analytics Hook

Located at `/lib/analytics.ts`, this provides:
- `useAnalytics()` - Main hook for tracking events
- `EVENTS` - Constant event names for consistency
- `trackError()` - Utility for error tracking

## Usage Examples

### Basic Event Tracking

```tsx
import { useAnalytics, EVENTS } from '@/lib/analytics';

const MyComponent = () => {
  const { trackEvent } = useAnalytics();
  
  const handleAction = () => {
    trackEvent(EVENTS.EXPENSE_CREATED, {
      amount: 100,
      currency: 'USD',
      category: 'Food',
    });
  };
};
```

### User Identification (Already implemented in ProtectedRoute)

```tsx
const { identifyUser, setUserProperties } = useAnalytics();

// Identify user on login
identifyUser(user.email, {
  email: user.email,
  name: user.name,
  plan: 'premium',
});

// Update user properties
setUserProperties({
  total_expenses: 50,
  last_active: new Date().toISOString(),
});
```

### Page View Tracking (Automatic)

Page views are automatically tracked in `App.tsx` via the `PageViewTracker` component when routes change.

### Reset User on Logout (Already implemented)

```tsx
const { resetUser } = useAnalytics();

const handleLogout = () => {
  resetUser(); // Clears PostHog user session
  // ... logout logic
};
```

## Available Events

### Authentication
- `LOGIN_INITIATED` - User clicks login button
- `LOGIN_SUCCESS` - User successfully authenticates
- `LOGOUT` - User logs out

### Expense Management
- `EXPENSE_CREATED` - New expense added
- `EXPENSE_UPDATED` - Expense modified
- `EXPENSE_DELETED` - Expense removed
- `EXPENSE_FORM_OPENED` - Expense form displayed
- `EXPENSE_FORM_CANCELLED` - Form closed without saving

### File Management
- `FILE_UPLOADED` - File uploaded
- `FILE_DELETED` - File removed
- `FILE_DOWNLOADED` - File downloaded
- `FILE_VIEWED` - File opened/viewed ✅ **TRACKED**
- `IMAGE_CAPTURED` - Camera used to capture receipt
- `FILE_INFO_VIEWED` - User clicked to view file details ✅ **TRACKED**

### Gmail Integration
- `GMAIL_CONNECT_INITIATED` - User starts Gmail connection
- `GMAIL_CONNECTED` - Gmail successfully connected
- `GMAIL_DISCONNECTED` - Gmail disconnected
- `GMAIL_SYNC` - Gmail sync triggered

### Navigation & Views
- `PAGE_VIEW` - User navigates to page (automatic) ✅ **TRACKED**
- `NAVIGATION` - User clicks navigation item ✅ **TRACKED**
- `IMPORTED_SECTION_CLICKED` - User switches to imported transactions view ✅ **TRACKED**

### Export & Schema
- `EXPORT_INITIATED` - Export process started
- `EXPORT_COMPLETED` - Export finished
- `EXPORT_BUTTON_CLICKED` - Export button clicked on transactions page ✅ **TRACKED**
- `SCHEMA_BUTTON_CLICKED` - Schema customization button clicked ✅ **TRACKED**

### Profile Management
- `PROFILE_EDIT_INITIATED` - User clicks edit profile button ✅ **TRACKED**
- `PROFILE_UPDATE_ATTEMPTED` - User tries to save profile changes ✅ **TRACKED**
- `PROFILE_UPDATE_SUCCESS` - Profile updated successfully ✅ **TRACKED**
- `PROFILE_UPDATE_FAILED` - Profile update failed ✅ **TRACKED**
- `PROFILE_EDIT_CANCELLED` - User cancels profile editing ✅ **TRACKED**

### Settings
- `SETTINGS_UPDATED` - Settings changed
- `THEME_CHANGED` - Theme toggled

### Search & Filters
- `SEARCH_PERFORMED` - Search query submitted ✅ **TRACKED**
- `FILTER_APPLIED` - Filter criteria applied ✅ **TRACKED**

### Charts
- `CHART_VIEWED` - Chart rendered
- `CHART_INTERACTED` - User interacts with chart

## Where Tracking is Implemented

### ✅ Already Tracked

1. **Auth.tsx** - Login initiation
2. **ProtectedRoute.tsx** - Login success & user identification
3. **TopBar.tsx** - Logout & navigation
4. **ExpenseForm.tsx** - Expense creation/updates
5. **App.tsx** - Automatic page view tracking
6. **Transactions.tsx** - ✅ **NEW**
   - Imported section clicks
   - Schema button clicks
   - Export button clicks
   - Search interactions
   - Filter applications
7. **Files.tsx** - ✅ **NEW**
   - File info viewing (details modal)
   - File viewing (direct and from modal)
   - Status filter changes
8. **Profile.tsx** - ✅ **NEW**
   - Profile edit initiation
   - Profile update attempts
   - Profile update success/failure
   - Profile edit cancellation

## 🎯 Suggested Additional Tracking Opportunities

### High Priority

#### 1. **Dashboard Analytics Page**
Track engagement with visualizations and insights:
```tsx
// When user views the dashboard
trackEvent('dashboard_viewed', {
  has_expenses: expenses.length > 0,
  total_expenses: expenses.length,
  date_range: selectedDateRange,
});

// When user interacts with spending chart
trackEvent(EVENTS.CHART_INTERACTED, {
  chart_type: 'spending_by_category',
  interaction_type: 'click',
  category: clickedCategory,
});

// When user changes time period filter
trackEvent('time_period_changed', {
  previous_period: oldPeriod,
  new_period: newPeriod,
  source: 'dashboard',
});
```

#### 2. **File Upload & Image Capture**
Track document processing journey:
```tsx
// In FileUploadModal
trackEvent(EVENTS.FILE_UPLOADED, {
  file_type: file.type,
  file_size: file.size,
  upload_source: 'manual_upload',
  has_notes: !!notes,
});

// In ImageCaptureModal
trackEvent(EVENTS.IMAGE_CAPTURED, {
  source: 'camera',
  device_type: isMobile ? 'mobile' : 'desktop',
});
```

#### 3. **Expense Deletion**
Track when users remove expenses:
```tsx
trackEvent(EVENTS.EXPENSE_DELETED, {
  expense_id: expenseId,
  amount: expense.amount,
  category: expense.category,
  age_days: calculateDaysSinceCreation(expense.created_at),
});
```

#### 4. **Import Actions**
Track when users import expenses from staging:
```tsx
trackEvent('expense_imported_from_staging', {
  imported_expense_id: importedExpense.id,
  amount: importedExpense.amount,
  category: importedExpense.category,
  has_attachment: !!importedExpense.attachment,
});
```

### Medium Priority

#### 5. **Transaction Details Modal**
Track when users view transaction details:
```tsx
trackEvent('transaction_details_viewed', {
  transaction_type: isExpense ? 'expense' : 'imported',
  has_attachment: !!attachment,
  has_custom_fields: customFieldCount > 0,
});
```

#### 6. **Gmail Integration**
Track email sync and connection:
```tsx
// In GmailIntegration component
trackEvent(EVENTS.GMAIL_CONNECT_INITIATED, {
  has_previous_connection: isAlreadyConnected,
});

trackEvent(EVENTS.GMAIL_SYNC, {
  sync_type: 'manual',
  last_sync: lastSyncTimestamp,
});
```

#### 7. **Custom Schema Management**
Track schema customization:
```tsx
trackEvent('custom_field_added', {
  field_name: fieldName,
  field_type: fieldType,
  field_order: order,
});

trackEvent('custom_field_removed', {
  field_name: fieldName,
  total_fields_remaining: remainingFields,
});
```

#### 8. **Export Modal**
Track export format selection:
```tsx
trackEvent(EVENTS.EXPORT_INITIATED, {
  format: exportFormat,
  record_count: data.length,
  includes_custom_fields: includeCustomFields,
  view_type: viewType,
});

trackEvent(EVENTS.EXPORT_COMPLETED, {
  format: exportFormat,
  success: true,
  download_time_ms: downloadTime,
});
```

### Low Priority (Nice to Have)

#### 9. **Pagination Interactions**
```tsx
trackEvent('pagination_clicked', {
  page_number: pageNumber,
  source: 'transactions_page',
  view_type: viewType,
});
```

#### 10. **Attachment Viewer**
```tsx
trackEvent('attachment_viewer_opened', {
  file_type: mimeType,
  source: 'transactions_page',
});
```

#### 11. **Form Validation Errors**
```tsx
trackEvent('form_validation_error', {
  form_type: 'expense_form',
  error_fields: ['amount', 'category'],
});
```

#### 12. **Session Duration Tracking**
```tsx
// Track time spent on each page
useEffect(() => {
  const startTime = Date.now();
  return () => {
    const duration = Date.now() - startTime;
    trackEvent('page_session_duration', {
      page: 'transactions',
      duration_seconds: Math.round(duration / 1000),
    });
  };
}, []);
```

#### 13. **Feature Discovery**
Track first-time feature usage:
```tsx
trackEvent('feature_first_use', {
  feature_name: 'expense_import',
  days_since_signup: daysSinceSignup,
});
```

## Event Properties Best Practices

### 1. Context Properties (Always Include)
- `source` - Where the event originated (e.g., 'transactions_page', 'dashboard')
- `timestamp` - Automatically added by analytics hook
- `user_email` - For user-specific events

### 2. Action Properties
- What was clicked/changed
- Previous and new values for state changes
- Success/failure status

### 3. Data Properties
- Record counts
- File sizes/types
- Amounts and currencies
- Categories

### 4. Environment Properties
- Device type (mobile/desktop)
- Browser info (automatically captured by PostHog)
- Feature flags status

## Sample Event Data

```json
{
  "event": "imported_section_clicked",
  "properties": {
    "view_type": "imported",
    "source": "transactions_page",
    "previous_view": "expenses",
    "imported_count": 15,
    "timestamp": "2026-01-07T10:30:00Z"
  }
}
```

## Testing Your Events

1. Open your app in development mode
2. Open browser DevTools → Network tab
3. Filter by "posthog" or "batch"
4. Perform actions in your app
5. Verify events are being sent with correct properties

**OR** use PostHog's built-in debugging:
```tsx
// In main.tsx, add debug flag
options={{
  api_host: import.meta.env.VITE_PUBLIC_POSTHOG_HOST,
  debug: import.meta.env.MODE === "development", // ✅ Already enabled
}}
```

Check browser console for PostHog debug logs.

## Analytics Dashboard Tips

### Key Metrics to Track

1. **User Engagement**
   - DAU/MAU (Daily/Monthly Active Users)
   - Pages per session
   - Session duration
   - Feature adoption rate

2. **Expense Management**
   - Expenses created per user
   - Import vs manual entry ratio
   - Most used categories
   - Average expense amount

3. **File Processing**
   - Upload success rate
   - Processing time
   - File types distribution
   - Error rates

4. **User Journey**
   - Time to first expense
   - Feature discovery patterns
   - Drop-off points
   - Conversion funnels

### Creating Useful Insights

1. **Funnel Analysis**: Track user journey from signup → first expense → regular usage
2. **Retention Cohorts**: Monitor user retention over time
3. **Feature Usage**: Identify most/least used features
4. **Error Tracking**: Monitor and fix issues proactively

## Privacy & Compliance

- ✅ Don't track sensitive financial details (full account numbers, passwords)
- ✅ Track amounts and categories (anonymized aggregates are fine)
- ✅ Use user IDs/emails for identification (with user consent)
- ✅ Respect user privacy preferences
- ⚠️ Consider GDPR compliance for EU users

## Feature Flags (Advanced)

PostHog supports A/B testing and feature flags:
```tsx
const { posthog } = useAnalytics();

const isNewUIEnabled = posthog?.isFeatureEnabled('new-dashboard-ui');

if (isNewUIEnabled) {
  trackEvent('feature_flag_active', {
    flag_name: 'new-dashboard-ui',
  });
  return <NewDashboard />;
}
return <OldDashboard />;
```

## Next Steps

1. ✅ **Completed**: Login, logout, page views, expense operations, file viewing, profile updates
2. 🔄 **Recommended Next**: Add tracking to Dashboard, File Upload Modal, Gmail Integration
3. 📊 **Review**: Check PostHog dashboard for first insights after 24-48 hours
4. 🎯 **Optimize**: Based on data, focus development on high-engagement features

## Support & Resources

- [PostHog Documentation](https://posthog.com/docs)
- [PostHog React SDK](https://posthog.com/docs/libraries/react)
- [Event Naming Conventions](https://posthog.com/docs/integrate/client/js#event-naming)

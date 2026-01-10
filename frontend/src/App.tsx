import { Suspense, lazy, useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Outlet, useLocation } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "./store";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { api, getJwtCookie } from "./lib/api";
import { useAnalytics } from "./lib/analytics";

// Lazy load all pages for code splitting - reduces initial bundle size
const DashboardAnalytics = lazy(() => import("./pages/DashboardAnalytics"));
const Transactions = lazy(() => import("./pages/Transactions"));
const Files = lazy(() => import("./pages/Files"));
const Settings = lazy(() => import("./pages/Settings"));
const Profile = lazy(() => import("./pages/Profile"));
const Support = lazy(() => import("./pages/Support"));
const Auth = lazy(() => import("./pages/Auth"));
const AuthCallback = lazy(() => import("./pages/AuthCallback"));
const NotFound = lazy(() => import("./pages/NotFound"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
      refetchOnWindowFocus: false,
    },
  },
});

// Prefetch critical data if user is authenticated
const prefetchCriticalData = () => {
  const jwt = getJwtCookie();
  if (jwt) {
    // Prefetch in parallel - these will be cached and ready when components mount
    queryClient.prefetchQuery({
      queryKey: ["user"],
      queryFn: api.getUser,
      staleTime: 5 * 60 * 1000,
    });
    queryClient.prefetchQuery({
      queryKey: ["expenses"],
      queryFn: () => api.getExpenses(100, 0), // Fetch first 100 expenses
    });
    queryClient.prefetchQuery({
      queryKey: ["importedExpenses"],
      queryFn: () => api.getImportedExpenses(100, 0), // Fetch first 100 imported expenses
    });
  }
};

// Start prefetching immediately
prefetchCriticalData();

// Loading fallback component for full page (auth, etc.)
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

// Loading fallback for content area only (keeps layout stable)
const ContentLoader = () => (
  <div className="flex items-center justify-center min-h-[60vh]">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

// Layout wrapper that includes Suspense for nested routes
const LayoutWithSuspense = () => (
  <ProtectedRoute>
    <Layout>
      <Suspense fallback={<ContentLoader />}>
        <Outlet />
      </Suspense>
    </Layout>
  </ProtectedRoute>
);

// Page view tracker component
const PageViewTracker = () => {
  const location = useLocation();
  const { trackPageView } = useAnalytics();

  useEffect(() => {
    const pageName = location.pathname === '/' ? 'Dashboard' : 
      location.pathname.split('/')[1]?.charAt(0).toUpperCase() + 
      location.pathname.split('/')[1]?.slice(1) || 'Unknown';
    
    trackPageView(pageName, {
      path: location.pathname,
      search: location.search,
    });
  }, [location, trackPageView]);

  return null;
};

const App = () => (
  <Provider store={store}>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <PageViewTracker />
          <Routes>
            {/* Auth routes with full page loader */}
            <Route path="/auth" element={<Suspense fallback={<PageLoader />}><Auth /></Suspense>} />
            <Route path="/api/emails/oauth2callback" element={<Suspense fallback={<PageLoader />}><AuthCallback /></Suspense>} />
            
            {/* Protected routes with shared Layout - only content area reloads */}
            <Route element={<LayoutWithSuspense />}>
              <Route path="/" element={<DashboardAnalytics />} />
              <Route path="/transactions" element={<Transactions />} />
              <Route path="/files" element={<Files />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/support" element={<Support />} />
            </Route>
            
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<Suspense fallback={<PageLoader />}><NotFound /></Suspense>} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </Provider>
);

export default App;

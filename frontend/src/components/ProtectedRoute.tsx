import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppSelector } from "@/store/hooks";
import { getJwtCookie } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { useAnalytics, EVENTS } from "@/lib/analytics";

export const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const navigate = useNavigate();
  const { identifyUser, setUserProperties, trackEvent } = useAnalytics();
  const isAuthenticated = useAppSelector((state) => state.user.isAuthenticated);
  const user = useAppSelector((state) => state.user.user);
  const jwt = getJwtCookie();

  useEffect(() => {
    if (!jwt && !isAuthenticated) {
      navigate('/auth');
    }
  }, [jwt, isAuthenticated, navigate]);

  // Identify user when they're authenticated
  useEffect(() => {
    if (isAuthenticated && user) {
      identifyUser(user.email, {
        email: user.email,
        name: user.name,
        login_count: user.login_count || 1,
      });
      
      trackEvent(EVENTS.LOGIN_SUCCESS, {
        method: 'google',
        user_email: user.email,
      });
    }
  }, [isAuthenticated, user, identifyUser, trackEvent]);

  if (!jwt && !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return <>{children}</>;
};

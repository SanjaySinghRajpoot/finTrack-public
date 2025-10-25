import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppSelector } from "@/store/hooks";
import { getJwtCookie } from "@/lib/api";
import { Loader2 } from "lucide-react";

export const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const navigate = useNavigate();
  const isAuthenticated = useAppSelector((state) => state.user.isAuthenticated);
  const jwt = getJwtCookie();

  useEffect(() => {
    if (!jwt && !isAuthenticated) {
      navigate('/auth');
    }
  }, [jwt, isAuthenticated, navigate]);

  if (!jwt && !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return <>{children}</>;
};

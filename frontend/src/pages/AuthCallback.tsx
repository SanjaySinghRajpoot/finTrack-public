import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { setJwtCookie } from "@/lib/api";
import { useAppDispatch } from "@/store/hooks";
import { setUser } from "@/store/slices/userSlice";

const AuthCallback = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  useEffect(() => {
    try {
      const bodyText = document.body.innerText;
      const jsonData = JSON.parse(bodyText);
      
      if (jsonData.jwt && jsonData.user) {
        setJwtCookie(jsonData.jwt);
        // Set user in Redux store
        dispatch(setUser({ email: jsonData.user.email, id: jsonData.user.id.toString() }));
        navigate('/');
      } else {
        navigate('/auth');
      }
    } catch (error) {
      console.error('Error parsing auth response:', error);
      navigate('/auth');
    }
  }, [navigate, dispatch]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary via-secondary to-accent flex items-center justify-center">
      <div className="text-center text-white space-y-4">
        <Loader2 className="h-12 w-12 animate-spin mx-auto" />
        <p className="text-xl font-semibold">Completing authentication...</p>
        <p className="text-white/80">Please wait while we sign you in</p>
      </div>
    </div>
  );
};

export default AuthCallback;

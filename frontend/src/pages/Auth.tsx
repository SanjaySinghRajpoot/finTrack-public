import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, TrendingUp, PieChart, Shield } from "lucide-react";
import { api, getJwtCookie } from "@/lib/api";

const Auth = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is already authenticated
    const checkAuth = async () => {
      const jwt = getJwtCookie();
      if (jwt) {
        try {
          await api.getExpenses();
          navigate("/");
        } catch (error) {
          // JWT invalid, stay on auth page
        }
      }
    };
    checkAuth();
  }, [navigate]);

  const handleGoogleLogin = () => {
    api.login(); // redirects to Google → backend → frontend /
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-muted/20 to-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl"></div>
      </div>

      <div className="w-full max-w-6xl grid md:grid-cols-2 gap-8 md:gap-12 items-center relative z-10">
        {/* Left side - Branding */}
        <div className="space-y-8 hidden md:block">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-lg">
                <Sparkles className="h-7 w-7 text-primary-foreground" />
              </div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                FinTrack
              </h1>
            </div>
            
            <h2 className="text-4xl font-bold text-foreground leading-tight">
              Take control of your finances
            </h2>
            <p className="text-muted-foreground text-lg leading-relaxed">
              Track expenses, manage budgets, and achieve your financial goals with ease.
            </p>
          </div>

          <div className="space-y-6 pt-4">
            <div className="flex items-start gap-4 p-5 rounded-2xl bg-card shadow-soft hover:shadow-elevated transition-smooth border border-border/50">
              <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center shrink-0">
                <TrendingUp className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-1">Smart Analytics</h3>
                <p className="text-muted-foreground text-sm">Get insights into your spending patterns with detailed charts and reports</p>
              </div>
            </div>

            <div className="flex items-start gap-4 p-5 rounded-2xl bg-card shadow-soft hover:shadow-elevated transition-smooth border border-border/50">
              <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-secondary/20 to-secondary/10 flex items-center justify-center shrink-0">
                <PieChart className="h-6 w-6 text-secondary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-1">Category Tracking</h3>
                <p className="text-muted-foreground text-sm">Organize and analyze expenses by custom categories</p>
              </div>
            </div>

            <div className="flex items-start gap-4 p-5 rounded-2xl bg-card shadow-soft hover:shadow-elevated transition-smooth border border-border/50">
              <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-accent/20 to-accent/10 flex items-center justify-center shrink-0">
                <Shield className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-1">Secure & Private</h3>
                <p className="text-muted-foreground text-sm">Your financial data is encrypted and protected with industry-standard security</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right side - Login Card */}
        <Card className="shadow-elevated hover:shadow-xl transition-smooth border-border/50 bg-card backdrop-blur-sm relative overflow-hidden">
          {/* Card decoration */}
          <div className="absolute top-0 right-0 w-40 h-40 bg-gradient-to-br from-primary/10 to-transparent rounded-full blur-2xl"></div>
          
          <CardHeader className="space-y-3 pb-6 relative z-10">
            <div className="md:hidden flex items-center gap-3 mb-2">
              <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-md">
                <Sparkles className="h-6 w-6 text-primary-foreground" />
              </div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                FinTrack
              </h1>
            </div>
            <CardTitle className="text-2xl md:text-3xl font-bold text-foreground">Welcome back</CardTitle>
            <CardDescription className="text-base">
              Sign in with your Google account to continue managing your finances
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 relative z-10">
            <Button 
              onClick={handleGoogleLogin}
              className="w-full h-12 md:h-14 text-base font-semibold shadow-md hover:shadow-lg transition-smooth bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary"
              size="lg"
            >
              <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </Button>

            <p className="text-center text-xs md:text-sm text-muted-foreground leading-relaxed px-2 md:px-4">
              By continuing, you agree to our <span className="text-primary font-medium hover:underline cursor-pointer">Terms of Service</span> and <span className="text-primary font-medium hover:underline cursor-pointer">Privacy Policy</span>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Auth;

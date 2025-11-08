import { Heart, Github, Twitter } from "lucide-react";

export const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-card border-t border-border mt-auto">
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Left side - Branding */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">FT</span>
            </div>
            <div className="text-sm">
              <span className="font-semibold text-foreground">FinTrack</span>
              <span className="text-muted-foreground ml-2">Manage your finances with ease</span>
            </div>
          </div>

          {/* Center - Links */}
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <a 
              href="#" 
              className="hover:text-foreground transition-colors"
            >
              Privacy Policy
            </a>
            <a 
              href="#" 
              className="hover:text-foreground transition-colors"
            >
              Terms of Service
            </a>
            <a 
              href="#" 
              className="hover:text-foreground transition-colors"
            >
              Support
            </a>
          </div>

          {/* Right side - Copyright & Social */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <a 
                href="#" 
                className="text-muted-foreground hover:text-foreground transition-colors"
                aria-label="GitHub"
              >
                <Github className="h-4 w-4" />
              </a>
              <a 
                href="#" 
                className="text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Twitter"
              >
                <Twitter className="h-4 w-4" />
              </a>
            </div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <span>© {currentYear} Made with</span>
              <Heart className="h-3 w-3 text-red-500 fill-current" />
              <span>by FinTrack</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};
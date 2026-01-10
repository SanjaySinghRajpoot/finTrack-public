import { NavLink, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Home, Receipt, Settings, User, LogOut, Menu, Sparkles, FolderOpen, Loader2, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { api } from "@/lib/api";

const navItems = [
  { title: "Dashboard", icon: Home, path: "/" },
  { title: "Transactions", icon: Receipt, path: "/transactions" },
  { title: "Files", icon: FolderOpen, path: "/files" },
  { title: "Profile", icon: User, path: "/profile" },
  { title: "Support", icon: HelpCircle, path: "/support" },
  { title: "Settings", icon: Settings, path: "/settings" },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export const Sidebar = ({ collapsed, onToggle }: SidebarProps) => {
  const isMobile = useIsMobile();
  const navigate = useNavigate();

  // Fetch user data
  const { data: user, isLoading: isUserLoading } = useQuery({
    queryKey: ["user"],
    queryFn: api.getUser,
    retry: false,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const handleLogout = () => {
    api.logout();
    navigate("/auth");
  };

  const getInitials = () => {
    if (!user) return "U";
    const firstInitial = user.first_name?.[0] || '';
    const lastInitial = user.last_name?.[0] || '';
    return (firstInitial + lastInitial).toUpperCase() || user.email[0].toUpperCase();
  };

  const getFullName = () => {
    if (!user) return "User";
    const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim();
    return fullName || user.email.split("@")[0];
  };

  return (
    <>
      {isMobile && (
        <button
          onClick={onToggle}
          className="fixed top-4 left-4 z-50 p-2 rounded-lg bg-primary text-primary-foreground shadow-lg md:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
      )}

      <aside
        className={cn(
          "fixed left-0 top-0 h-screen bg-card text-foreground border-r border-border transition-all duration-300 flex flex-col shadow-sm z-40",
          collapsed ? "-translate-x-full md:translate-x-0 md:w-20" : "translate-x-0 w-64"
        )}
      >
        <div className={cn(
          "h-16 flex items-center border-b border-border",
          collapsed ? "justify-center px-4" : "px-4"
        )}>
          {!collapsed && (
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-md">
                <Sparkles className="h-5 w-5 text-primary-foreground" />
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                FinTrack
              </h1>
            </div>
          )}
          {collapsed && !isMobile && (
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-md">
              <Sparkles className="h-5 w-5 text-primary-foreground" />
            </div>
          )}
        </div>

        <nav className="flex-1 py-6 px-3">
          <div className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => isMobile && onToggle()}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-4 py-3 rounded-xl transition-all group",
                      isActive
                        ? "bg-primary text-primary-foreground shadow-md"
                        : "hover:bg-muted text-muted-foreground hover:text-foreground"
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon className="h-5 w-5 flex-shrink-0" />
                      {!collapsed && (
                        <span className="font-medium">
                          {item.title}
                        </span>
                      )}
                    </>
                  )}
                </NavLink>
              );
            })}
          </div>
        </nav>

        <div className="p-4 border-t border-border">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                className={cn(
                  "w-full h-auto p-2 hover:bg-muted flex items-center gap-3",
                  collapsed ? "justify-center" : "justify-start"
                )}
              >
                <Avatar className="h-10 w-10 border-2 border-primary/20 shrink-0">
                  {user?.profile_image ? (
                    <AvatarImage
                      src={user.profile_image}
                      alt={getFullName()}
                      className="object-cover"
                      onError={(e) => {
                        // Hide broken image and show fallback
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                  ) : null}
                  <AvatarFallback className="bg-primary text-primary-foreground font-semibold">
                    {isUserLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      getInitials()
                    )}
                  </AvatarFallback>
                </Avatar>
                {!collapsed && (
                  <div className="flex flex-col items-start overflow-hidden">
                    <span className="text-sm font-medium text-foreground truncate w-full text-left">
                      {isUserLoading ? "Loading..." : getFullName()}
                    </span>
                    <span className="text-xs text-muted-foreground truncate w-full text-left">
                      {user?.email || ""}
                    </span>
                  </div>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" side="top" className="w-56 bg-card border-border shadow-lg mb-2">
              {/* Show user info in dropdown when collapsed */}
              {collapsed && (
                <>
                  <div className="px-3 py-2 border-b border-border">
                    <p className="text-sm font-medium text-foreground truncate">
                      {getFullName()}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {user?.email || ""}
                    </p>
                  </div>
                </>
              )}
              <DropdownMenuItem 
                onClick={() => navigate("/profile")}
                className="flex items-center gap-2 cursor-pointer hover:bg-muted focus:bg-muted"
              >
                <User className="h-4 w-4" />
                <span>View Profile</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="flex items-center gap-2 text-destructive hover:bg-destructive/10 focus:bg-destructive/10 focus:text-destructive cursor-pointer">
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      {isMobile && !collapsed && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={onToggle}
        />
      )}
    </>
  );
};

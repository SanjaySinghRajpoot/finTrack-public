import { NavLink, useNavigate } from "react-router-dom";
import { Home, Receipt, Settings, User, LogOut, Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { api } from "@/lib/api";
import { useAppSelector } from "@/store/hooks";

const navItems = [
  { title: "Dashboard", icon: Home, path: "/" },
  { title: "Transactions", icon: Receipt, path: "/transactions" },
  { title: "Profile", icon: User, path: "/profile" },
  { title: "Settings", icon: Settings, path: "/settings" },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export const Sidebar = ({ collapsed, onToggle }: SidebarProps) => {
  const isMobile = useIsMobile();
  const navigate = useNavigate();
  const userEmail = useAppSelector((state) => state.user.email);

  const handleLogout = () => {
    api.logout();
    navigate("/auth");
  };

  const getInitials = () => {
    if (!userEmail) return "U";
    return userEmail.charAt(0).toUpperCase();
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
        <div className="h-16 flex items-center justify-center border-b border-border px-4">
          {!collapsed && (
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-sm">
                <span className="text-primary-foreground font-bold text-lg">FT</span>
              </div>
              <h1 className="text-xl font-bold text-primary">FinTrack</h1>
            </div>
          )}
          {collapsed && !isMobile && (
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-sm">
              <span className="text-primary-foreground font-bold text-lg">FT</span>
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
                className="w-full h-auto p-2 hover:bg-muted flex items-center justify-center"
              >
                <Avatar className="h-10 w-10 bg-primary border-2 border-primary/20">
                  <AvatarFallback className="bg-primary text-primary-foreground font-semibold">
                      <User className="h-5 w-5 text-primary-foreground" />
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" side="top" className="w-56 bg-card border-border shadow-lg mb-2">
              <div className="px-2 py-2 border-b border-border">
                <p className="text-sm font-medium text-foreground truncate">
                  {userEmail || "User"}
                </p>
              </div>
              <DropdownMenuItem 
                onClick={() => navigate("/profile")}
                className="flex items-center gap-2 cursor-pointer hover:bg-muted focus:bg-muted"
              >
                <User className="h-4 w-4" />
                <span>Profile</span>
              </DropdownMenuItem>
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

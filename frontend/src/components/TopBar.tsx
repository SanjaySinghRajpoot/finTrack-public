import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, User, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useAppSelector } from "@/store/hooks";

export const TopBar = () => {
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
    <header className="h-16 bg-card border-b border-border sticky top-0 z-30 backdrop-blur-sm bg-card/95">
      <div className="h-full px-6 flex items-center justify-between gap-4">
        {/* App Title / Breadcrumb */}
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-foreground hidden md:block">FinTrack</h2>
        </div>

        {/* User Profile */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-10 w-10 rounded-full hover:bg-muted">
              <Avatar className="h-10 w-10 bg-primary border-2 border-primary/20">
                <AvatarFallback className="bg-primary text-primary-foreground font-semibold">
                  {getInitials()}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56 bg-card border-border shadow-lg z-50">
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
    </header>
  );
};

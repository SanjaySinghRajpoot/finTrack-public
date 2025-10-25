import { ReactNode, useState } from "react";
import { Sidebar } from "./Sidebar";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";

interface LayoutProps {
  children: ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  const isMobile = useIsMobile();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(isMobile);

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div 
        className={cn(
          "flex-1 flex flex-col transition-all duration-300 w-full min-w-0",
          sidebarCollapsed ? "ml-0 md:ml-20" : "ml-0 md:ml-64"
        )}
      >
        <main className="flex-1 p-3 sm:p-4 md:p-6 lg:p-8 w-full overflow-x-hidden">
          {children}
        </main>
      </div>
    </div>
  );
};

import { Card, CardContent } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string;
  icon: LucideIcon;
  trend?: {
    value: string;
    positive: boolean;
  };
  className?: string;
}

export function StatCard({ title, value, icon: Icon, trend, className }: StatCardProps) {
  return (
    <Card className={cn("gradient-card shadow-soft hover:shadow-elevated transition-smooth border-0", className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">{title}</p>
            <p className="text-3xl font-bold text-foreground">{value}</p>
            {trend && (
              <div className="flex items-center gap-1">
                <span className={cn(
                  "inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold",
                  trend.positive ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"
                )}>
                  {trend.positive ? "↑" : "↓"} {trend.value}
                </span>
              </div>
            )}
          </div>
          <div className="h-14 w-14 rounded-2xl gradient-accent flex items-center justify-center shadow-soft">
            <Icon className="h-7 w-7 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

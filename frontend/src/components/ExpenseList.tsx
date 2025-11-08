import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pencil, Trash2 } from "lucide-react";
import { Expense } from "@/lib/api";
import { getCategoryConfig } from "@/lib/categories";
import { format } from "date-fns";

interface ExpenseListProps {
  expenses: Expense[];
  onEdit: (expense: Expense) => void;
  onDelete: (id: number) => void;
  onTransactionClick?: (expense: Expense) => void;
}

export function ExpenseList({ expenses, onEdit, onDelete, onTransactionClick }: ExpenseListProps) {
  if (expenses.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No expenses yet. Add your first expense to get started!</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {expenses.map((expense) => {
        const categoryConfig = getCategoryConfig(expense.category);
        const Icon = categoryConfig.icon;

        return (
          <Card key={expense.uuid} className="shadow-sm hover:shadow-md transition-smooth border border-border/50 bg-card">
            <CardContent className="p-3">
              <div className="flex items-center gap-3">
                <div
                  className="h-10 w-10 rounded-lg flex items-center justify-center shrink-0"
                  style={{ backgroundColor: categoryConfig.bgColor }}
                >
                  <Icon className="h-5 w-5" style={{ color: categoryConfig.color }} />
                </div>
                
                <div 
                  className="flex-1 min-w-0 cursor-pointer" 
                  onClick={() => onTransactionClick?.(expense)}
                >
                  <div className="flex items-baseline gap-2">
                    <h3 className="font-medium text-sm text-foreground truncate">{expense.description}</h3>
                    <span className="text-xs px-2 py-0.5 rounded-md bg-accent/10 text-accent-foreground shrink-0">
                      {expense.category}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {format(new Date(expense.created_at), "MMM dd, yyyy • HH:mm")}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <p className="text-base font-bold text-foreground">
                    {expense.currency} {expense.amount.toFixed(2)}
                  </p>
                  
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onEdit(expense)}
                      className="h-8 w-8 rounded-md hover:bg-primary/10 text-primary transition-smooth"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDelete(expense.id)}
                      className="h-8 w-8 rounded-md hover:bg-destructive/10 text-destructive transition-smooth"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ExpenseForm } from "@/components/ExpenseForm";
import { ExpenseList } from "@/components/ExpenseList";
import { ImportedExpenseList } from "@/components/ImportedExpenseList";
import { TableSkeleton } from "@/components/ui/table-skeleton";
import { Plus, Receipt, Calendar } from "lucide-react";
import { toast } from "sonner";
import { api, Expense, CreateExpenseRequest, ImportedExpense } from "@/lib/api";
import { startOfMonth, startOfWeek, endOfWeek, isWithinInterval, format } from "date-fns";

const Transactions = () => {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [viewMode, setViewMode] = useState<"month" | "week">("month");

  const { data: expenses = [], isLoading } = useQuery({
    queryKey: ["expenses"],
    queryFn: api.getExpenses,
    retry: false,
  });

  const { data: importedExpenses = [] } = useQuery({
    queryKey: ["importedExpenses"],
    queryFn: api.getImportedExpenses,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: api.createExpense,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Expense created successfully");
      setIsDialogOpen(false);
    },
    onError: () => {
      toast.error("Failed to create expense");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CreateExpenseRequest> }) =>
      api.updateExpense(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Expense updated successfully");
      setIsDialogOpen(false);
      setEditingExpense(null);
    },
    onError: () => {
      toast.error("Failed to update expense");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteExpense,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Expense deleted successfully");
    },
    onError: () => {
      toast.error("Failed to delete expense");
    },
  });

  const handleSubmit = (data: CreateExpenseRequest) => {
    if (editingExpense) {
      updateMutation.mutate({ id: editingExpense.uuid, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEdit = (expense: Expense) => {
    setEditingExpense(expense);
    setIsDialogOpen(true);
  };

  const handleImport = (importedExpense: ImportedExpense) => {
    const expenseData: CreateExpenseRequest = {
      amount: importedExpense.amount,
      currency: importedExpense.currency,
      category: importedExpense.category || "Other",
      description: importedExpense.title + (importedExpense.description ? ` - ${importedExpense.description}` : ""),
      is_import: true,
      processed_data_id: importedExpense.id
    };
    createMutation.mutate(expenseData);
  };

  // Group expenses by month or week
  const groupedExpenses = useMemo(() => {
    if (viewMode === "month") {
      const groups: { [key: string]: Expense[] } = {};
      expenses.forEach((expense) => {
        const monthKey = format(new Date(expense.created_at), "MMMM yyyy");
        if (!groups[monthKey]) groups[monthKey] = [];
        groups[monthKey].push(expense);
      });
      return groups;
    } else {
      const groups: { [key: string]: Expense[] } = {};
      expenses.forEach((expense) => {
        const weekStart = startOfWeek(new Date(expense.created_at), { weekStartsOn: 1 });
        const weekEnd = endOfWeek(new Date(expense.created_at), { weekStartsOn: 1 });
        const weekKey = `${format(weekStart, "MMM dd")} - ${format(weekEnd, "MMM dd, yyyy")}`;
        if (!groups[weekKey]) groups[weekKey] = [];
        groups[weekKey].push(expense);
      });
      return groups;
    }
  }, [expenses, viewMode]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-primary">
            All Transactions
          </h1>
          <p className="text-sm md:text-base text-muted-foreground mt-1">Manage all your expenses and imports</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-muted p-1 rounded-lg">
            <Button
              variant={viewMode === "month" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("month")}
              className="h-9"
            >
              <Calendar className="h-4 w-4 mr-2" />
              Monthly
            </Button>
            <Button
              variant={viewMode === "week" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("week")}
              className="h-9"
            >
              <Calendar className="h-4 w-4 mr-2" />
              Weekly
            </Button>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button 
                className="bg-primary hover:bg-primary/90 shadow-lg"
                onClick={() => setEditingExpense(null)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Expense
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle className="text-xl">
                  {editingExpense ? "Edit Expense" : "Add New Expense"}
                </DialogTitle>
              </DialogHeader>
              <ExpenseForm
                onSubmit={handleSubmit}
                defaultValues={editingExpense || undefined}
                isLoading={createMutation.isPending || updateMutation.isPending}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card className="shadow-soft border">
        <CardContent className="p-4 md:p-6">
          <Tabs defaultValue="expenses" className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-muted p-1 h-auto">
              <TabsTrigger 
                value="expenses"
                className="rounded-md data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-all"
              >
                <Receipt className="h-4 w-4 mr-2" />
                <span className="hidden sm:inline">My Expenses</span> ({expenses.length})
              </TabsTrigger>
              <TabsTrigger 
                value="imported"
                className="rounded-md data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-all"
              >
                <Receipt className="h-4 w-4 mr-2" />
                <span className="hidden sm:inline">Imported</span> ({importedExpenses.length})
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="expenses" className="mt-4 md:mt-6">
              {isLoading ? (
                <TableSkeleton rows={10} />
              ) : expenses.length === 0 ? (
                <div className="text-center py-12 md:py-16">
                  <div className="inline-flex items-center justify-center w-12 h-12 md:w-16 md:h-16 rounded-full bg-primary/10 mb-4">
                    <Receipt className="h-6 w-6 md:h-8 md:w-8 text-primary" />
                  </div>
                  <p className="text-base md:text-lg font-medium text-foreground">No expenses yet</p>
                  <p className="text-xs md:text-sm text-muted-foreground mt-1">Add your first expense to get started</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {Object.entries(groupedExpenses).map(([period, periodExpenses]) => (
                    <div key={period} className="space-y-3">
                      <div className="flex items-center gap-3 pb-2 border-b border-border">
                        <Calendar className="h-5 w-5 text-primary" />
                        <h3 className="text-lg font-semibold text-foreground">{period}</h3>
                        <span className="ml-auto text-sm text-muted-foreground">
                          {periodExpenses.length} transaction{periodExpenses.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <ExpenseList
                        expenses={periodExpenses}
                        onEdit={handleEdit}
                        onDelete={(id) => deleteMutation.mutate(id)}
                      />
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="imported" className="mt-4 md:mt-6">
              {importedExpenses.length === 0 ? (
                <div className="text-center py-12 md:py-16">
                  <div className="inline-flex items-center justify-center w-12 h-12 md:w-16 md:h-16 rounded-full bg-primary/10 mb-4">
                    <Receipt className="h-6 w-6 md:h-8 md:w-8 text-primary" />
                  </div>
                  <p className="text-base md:text-lg font-medium text-foreground">No imported expenses yet</p>
                  <p className="text-xs md:text-sm text-muted-foreground mt-1">Import expenses to see them here</p>
                </div>
              ) : (
                <ImportedExpenseList
                  expenses={importedExpenses}
                  onImport={handleImport}
                />
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export default Transactions;

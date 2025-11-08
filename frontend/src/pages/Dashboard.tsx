import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton } from "@/components/ui/stat-card-skeleton";
import { TableSkeleton } from "@/components/ui/table-skeleton";
import { ExpenseForm } from "@/components/ExpenseForm";
import { ExpenseList } from "@/components/ExpenseList";
import { ImportedExpenseList } from "@/components/ImportedExpenseList";
import { toast } from "sonner";
import { Wallet, TrendingDown, Calendar, Plus, LogOut, DollarSign, CalendarDays, Receipt, Target, CalendarCheck } from "lucide-react";
import { api, Expense, CreateExpenseRequest, ImportedExpense, getJwtCookie } from "@/lib/api";

const Dashboard = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);

  // Fetch expenses
  const { data: expenses = [], isLoading, error } = useQuery({
    queryKey: ["expenses"],
    queryFn: api.getExpenses,
    retry: false,
  });

  // Fetch imported expenses
  const { data: importedExpenses = [] } = useQuery({
    queryKey: ["importedExpenses"],
    queryFn: api.getImportedExpenses,
    retry: false,
  });

  // Create expense mutation
  const createMutation = useMutation({
    mutationFn: api.createExpense,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["importedExpenses"] });
      toast.success("Expense created successfully");
      setIsDialogOpen(false);
    },
    onError: () => {
      toast.error("Failed to create expense");
    },
  });

  // Update expense mutation
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

  // Delete expense mutation
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

  // Handle form submission
  const handleSubmit = (data: CreateExpenseRequest) => {
    if (editingExpense) {
      updateMutation.mutate({ id: editingExpense.uuid, data });
    } else {
      createMutation.mutate(data);
    }
  };

  // Handle edit
  const handleEdit = (expense: Expense) => {
    setEditingExpense(expense);
    setIsDialogOpen(true);
  };

  // Handle import
  const handleImport = (importedExpense: ImportedExpense) => {
    const expenseData: CreateExpenseRequest = {
      amount: importedExpense.amount,
      currency: importedExpense.currency,
      category: importedExpense.category || "Other",
      description: importedExpense.title + (importedExpense.description ? ` - ${importedExpense.description}` : ""),
      is_import: true,  // in case of imports
      processed_data_id: importedExpense.id
    };
    createMutation.mutate(expenseData);
  };

  // Calculate stats
  const currentMonth = new Date().getMonth();
  const currentYear = new Date().getFullYear();
  const monthlyExpenses = expenses.filter((exp) => {
    const expDate = new Date(exp.created_at);
    return expDate.getMonth() === currentMonth && expDate.getFullYear() === currentYear;
  });
  const monthlyTotal = monthlyExpenses.reduce((sum, exp) => sum + exp.amount, 0);

  // Check if user is authenticated
  useEffect(() => {
    const jwt = getJwtCookie();
    if (!jwt || error) {
      navigate("/auth");
    }
  }, [error, navigate]);

  if (error) {
    return null;
  }

  // Calculate average expense
  const avgExpense = expenses.length > 0 ? monthlyTotal / expenses.length : 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card shadow-soft sticky top-0 z-10 backdrop-blur-sm bg-card/80">
        <div className="container mx-auto px-4 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-xl gradient-primary flex items-center justify-center shadow-md">
                <Wallet className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">ExpenseTracker</h1>
                <p className="text-xs text-muted-foreground">Manage your expenses</p>
              </div>
            </div>
            <Button 
              variant="ghost" 
              size="icon"
              className="rounded-xl hover:bg-accent/20 transition-smooth"
              onClick={() => {
                api.logout();
                navigate("/auth");
              }}
            >
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 lg:px-8 py-8 space-y-6">
        {/* Stats Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {isLoading ? (
            <>
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
            </>
          ) : (
            <>
              <StatCard
                title="Monthly Total"
                value={`$${monthlyTotal.toFixed(2)}`}
                icon={CalendarCheck}
                trend={{ value: "21%", positive: false }}
              />
              <StatCard
                title="Total Expenses"
                value={expenses.length.toString()}
                icon={Receipt}
              />
              <StatCard
                title="This Month"
                value={monthlyExpenses.length.toString()}
                icon={CalendarDays}
              />
              <StatCard
                title="Average"
                value={`$${avgExpense.toFixed(2)}`}
                icon={Target}
              />
            </>
          )}
        </div>

        {/* Expenses Section */}
        <Card className="shadow-elevated border-0 overflow-hidden">
          <CardHeader className="bg-gradient-to-r from-card to-muted/20 border-b">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <CardTitle className="text-2xl font-bold text-foreground">Latest Transactions</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">Track and manage your expenses</p>
              </div>
              <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogTrigger asChild>
                  <Button 
                    className="gradient-primary shadow-md hover:shadow-lg transition-smooth border-0"
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
          </CardHeader>
          <CardContent className="p-6">
            <Tabs defaultValue="expenses" className="w-full">
              <TabsList className="grid w-full grid-cols-2 bg-muted/50 p-1 h-auto">
                <TabsTrigger 
                  value="expenses"
                  className="rounded-md data-[state=active]:bg-card data-[state=active]:shadow-sm transition-smooth"
                >
                  My Expenses
                </TabsTrigger>
                <TabsTrigger 
                  value="imported"
                  className="rounded-md data-[state=active]:bg-card data-[state=active]:shadow-sm transition-smooth"
                >
                  Imported ({importedExpenses.length})
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="expenses" className="mt-6">
                {isLoading ? (
                  <TableSkeleton rows={8} />
                ) : expenses.length === 0 ? (
                  <div className="text-center py-16">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
                      <Wallet className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <p className="text-lg font-medium text-foreground">No expenses yet</p>
                    <p className="text-sm text-muted-foreground mt-1">Add your first expense to get started</p>
                  </div>
                ) : (
                  <ExpenseList
                    expenses={expenses}
                    onEdit={handleEdit}
                    onDelete={(id) => deleteMutation.mutate(id)}
                  />
                )}
              </TabsContent>

              <TabsContent value="imported" className="mt-6">
                <ImportedExpenseList
                  expenses={importedExpenses}
                  onImport={handleImport}
                />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default Dashboard;

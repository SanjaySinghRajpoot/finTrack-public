import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton } from "@/components/ui/stat-card-skeleton";
import { TableSkeleton } from "@/components/ui/table-skeleton";
import { ExpenseForm } from "@/components/ExpenseForm";
import { ExpenseList } from "@/components/ExpenseList";
import { TransactionDetailsModal } from "@/components/TransactionDetailsModal";
import { toast } from "sonner";
import { Wallet, Plus, LogOut, CalendarCheck, Receipt, CalendarDays, Target, TrendingUp, TrendingDown, DollarSign } from "lucide-react";
import { api, Expense, CreateExpenseRequest, ImportedExpense, getJwtCookie } from "@/lib/api";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from "recharts";

const Dashboard = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<Expense | ImportedExpense | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);

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

  // Handle transaction click
  const handleTransactionClick = (transaction: Expense | ImportedExpense) => {
    setSelectedTransaction(transaction);
    setIsDetailsModalOpen(true);
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

  // Get the most common currency from expenses or default to INR
  const primaryCurrency = expenses.length > 0 
    ? expenses[0].currency 
    : "INR";

  // Calculate chart data - Last 7 days of spending
  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    const dayExpenses = expenses.filter(exp => {
      const expDate = new Date(exp.created_at);
      return expDate.toDateString() === date.toDateString();
    });
    const dayImported = importedExpenses.filter(exp => {
      const expDate = new Date(exp.created_at);
      return expDate.toDateString() === date.toDateString();
    });
    
    return {
      day: date.toLocaleDateString('en-US', { weekday: 'short' }),
      manual: dayExpenses.reduce((sum, exp) => sum + exp.amount, 0),
      imported: dayImported.reduce((sum, exp) => sum + exp.amount, 0),
      total: dayExpenses.reduce((sum, exp) => sum + exp.amount, 0) + dayImported.reduce((sum, exp) => sum + exp.amount, 0)
    };
  });

  // Calculate category breakdown
  const categoryBreakdown = expenses.reduce((acc: any[], exp) => {
    const existing = acc.find(item => item.category === exp.category);
    if (existing) {
      existing.amount += exp.amount;
      existing.count += 1;
    } else {
      acc.push({ category: exp.category, amount: exp.amount, count: 1 });
    }
    return acc;
  }, []).sort((a, b) => b.amount - a.amount).slice(0, 5);

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Subtle Background Graphics */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* Top Right Circle */}
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-gradient-to-br from-primary/5 to-secondary/5 rounded-full blur-3xl"></div>
        
        {/* Bottom Left Circle */}
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-gradient-to-tr from-accent/5 to-primary/5 rounded-full blur-3xl"></div>
        
        {/* Finance Icons Watermark */}
        <div className="absolute top-1/4 right-10 opacity-[0.02] text-9xl">💰</div>
        <div className="absolute bottom-1/4 left-10 opacity-[0.02] text-9xl">📊</div>
        <div className="absolute top-1/2 right-1/4 opacity-[0.02] text-8xl">💳</div>
        
        {/* Grid Pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#8882_1px,transparent_1px),linear-gradient(to_bottom,#8882_1px,transparent_1px)] bg-[size:64px_64px] opacity-[0.015]"></div>
      </div>

      {/* Header */}
      <header className="border-b bg-card/80 shadow-soft sticky top-0 z-10 backdrop-blur-sm relative">
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
      <main className="container mx-auto px-4 lg:px-8 py-8 space-y-6 relative">
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
                value={`${primaryCurrency} ${monthlyTotal.toFixed(2)}`}
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
                value={`${primaryCurrency} ${avgExpense.toFixed(2)}`}
                icon={Target}
              />
            </>
          )}
        </div>

        {/* Master Chart - Central Element */}
        <Card className="shadow-elevated border-0 overflow-hidden bg-gradient-to-br from-card via-card to-primary/5">
          <CardHeader className="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border-b">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <CardTitle className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                  Financial Overview
                </CardTitle>
                <p className="text-sm text-muted-foreground mt-1">Your spending patterns and trends</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 to-blue-600"></div>
                  <span className="text-muted-foreground">Manual</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-3 h-3 rounded-full bg-gradient-to-r from-purple-500 to-purple-600"></div>
                  <span className="text-muted-foreground">Imported</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-3 h-3 rounded-full bg-gradient-to-r from-primary to-primary/60"></div>
                  <span className="text-muted-foreground">Total</span>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid gap-6 lg:grid-cols-3 mb-6">
              {/* Spending Chart */}
              <div className="lg:col-span-2">
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-foreground mb-1">7-Day Spending Trend</h3>
                  <p className="text-xs text-muted-foreground">Track your daily expenses at a glance</p>
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={last7Days}>
                    <defs>
                      <linearGradient id="colorManual" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="rgb(59, 130, 246)" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="rgb(59, 130, 246)" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorImported" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="rgb(168, 85, 247)" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="rgb(168, 85, 247)" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                    <XAxis 
                      dataKey="day" 
                      stroke="hsl(var(--muted-foreground))" 
                      fontSize={12}
                      tickLine={false}
                    />
                    <YAxis 
                      stroke="hsl(var(--muted-foreground))" 
                      fontSize={12}
                      tickLine={false}
                      tickFormatter={(value) => `${primaryCurrency} ${value}`}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '12px',
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                      }}
                      formatter={(value: any) => [`${primaryCurrency} ${value.toFixed(2)}`, '']}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="manual" 
                      stroke="rgb(59, 130, 246)" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorManual)" 
                      name="Manual"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="imported" 
                      stroke="rgb(168, 85, 247)" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorImported)" 
                      name="Imported"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="total" 
                      stroke="hsl(var(--primary))" 
                      strokeWidth={3}
                      fillOpacity={1} 
                      fill="url(#colorTotal)" 
                      name="Total"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Top Categories */}
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-1">Top Categories</h3>
                  <p className="text-xs text-muted-foreground mb-4">Your biggest spending areas</p>
                </div>
                <div className="space-y-3">
                  {categoryBreakdown.length === 0 ? (
                    <p className="text-xs text-muted-foreground text-center py-8">No data yet</p>
                  ) : (
                    categoryBreakdown.map((cat, index) => (
                      <div key={cat.category} className="relative">
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${
                              index === 0 ? 'bg-primary' :
                              index === 1 ? 'bg-blue-500' :
                              index === 2 ? 'bg-purple-500' :
                              index === 3 ? 'bg-pink-500' :
                              'bg-amber-500'
                            }`}></div>
                            <span className="text-xs font-medium text-foreground">{cat.category}</span>
                          </div>
                          <span className="text-xs font-bold text-primary">{primaryCurrency} {cat.amount.toFixed(0)}</span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              index === 0 ? 'bg-gradient-to-r from-primary to-primary/60' :
                              index === 1 ? 'bg-gradient-to-r from-blue-500 to-blue-400' :
                              index === 2 ? 'bg-gradient-to-r from-purple-500 to-purple-400' :
                              index === 3 ? 'bg-gradient-to-r from-pink-500 to-pink-400' :
                              'bg-gradient-to-r from-amber-500 to-amber-400'
                            }`}
                            style={{ 
                              width: `${(cat.amount / categoryBreakdown[0].amount) * 100}%`,
                              transition: 'width 0.5s ease-in-out'
                            }}
                          ></div>
                        </div>
                        <p className="text-[10px] text-muted-foreground mt-1">{cat.count} transaction{cat.count !== 1 ? 's' : ''}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Quick Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border/50">
              <div className="text-center p-3 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5">
                <div className="flex items-center justify-center gap-2 mb-1">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  <p className="text-xs text-muted-foreground">Highest Day</p>
                </div>
                <p className="text-lg font-bold text-foreground">
                  {primaryCurrency} {Math.max(...last7Days.map(d => d.total)).toFixed(0)}
                </p>
              </div>
              <div className="text-center p-3 rounded-lg bg-gradient-to-br from-blue-500/10 to-blue-500/5">
                <div className="flex items-center justify-center gap-2 mb-1">
                  <TrendingDown className="h-4 w-4 text-blue-600" />
                  <p className="text-xs text-muted-foreground">Lowest Day</p>
                </div>
                <p className="text-lg font-bold text-foreground">
                  {primaryCurrency} {Math.min(...last7Days.map(d => d.total)).toFixed(0)}
                </p>
              </div>
              <div className="text-center p-3 rounded-lg bg-gradient-to-br from-purple-500/10 to-purple-500/5">
                <div className="flex items-center justify-center gap-2 mb-1">
                  <DollarSign className="h-4 w-4 text-purple-600" />
                  <p className="text-xs text-muted-foreground">Daily Avg</p>
                </div>
                <p className="text-lg font-bold text-foreground">
                  {primaryCurrency} {(last7Days.reduce((sum, d) => sum + d.total, 0) / 7).toFixed(0)}
                </p>
              </div>
              <div className="text-center p-3 rounded-lg bg-gradient-to-br from-amber-500/10 to-amber-500/5">
                <div className="flex items-center justify-center gap-2 mb-1">
                  <Receipt className="h-4 w-4 text-amber-600" />
                  <p className="text-xs text-muted-foreground">Total Txns</p>
                </div>
                <p className="text-lg font-bold text-foreground">{expenses.length + importedExpenses.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Transactions Table */}
        <Card className="shadow-elevated border-0 overflow-hidden">
          <CardHeader className="bg-gradient-to-r from-card to-muted/20 border-b">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <CardTitle className="text-2xl font-bold text-foreground">All Transactions</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">Complete list of your expenses</p>
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
            {isLoading ? (
              <TableSkeleton rows={10} />
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
                onTransactionClick={handleTransactionClick}
              />
            )}
          </CardContent>
        </Card>
      </main>

      {/* Transaction Details Modal */}
      <TransactionDetailsModal
        transaction={selectedTransaction}
        isOpen={isDetailsModalOpen}
        onClose={() => {
          setIsDetailsModalOpen(false);
          setSelectedTransaction(null);
        }}
      />
    </div>
  );
};

export default Dashboard;

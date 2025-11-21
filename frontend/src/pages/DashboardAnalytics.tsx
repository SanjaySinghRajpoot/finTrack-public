import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton } from "@/components/ui/stat-card-skeleton";
import { TableSkeleton } from "@/components/ui/table-skeleton";
import { ExpenseForm } from "@/components/ExpenseForm";
import { ExpenseList } from "@/components/ExpenseList";
import { TransactionDetailsModal } from "@/components/TransactionDetailsModal";
import { DollarSign, TrendingDown, Calendar, TrendingUp, Plus, Receipt, Upload, Lightbulb, Target, PiggyBank, TrendingUpIcon } from "lucide-react";
import { api, CreateExpenseRequest, Expense, ImportedExpense } from "@/lib/api";
import { toast } from "sonner";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

const DashboardAnalytics = () => {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<Expense | ImportedExpense | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);

  const { data: user } = useQuery({
    queryKey: ["user"],
    queryFn: api.getUser,
    retry: false,
  });

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

  const getUserName = () => {
    if (user?.first_name) return user.first_name;
    return "User";
  };

  const getCurrentDate = () => {
    const now = new Date();
    const options: Intl.DateTimeFormatOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return now.toLocaleDateString('en-US', options);
  };

  // Handle file upload
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile) {
      toast.error("Please select a file");
      return;
    }

    setUploadingFile(true);
    try {
      // TODO: Implement actual file upload API call
      await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate upload
      toast.success("Invoice uploaded successfully");
      setIsUploadDialogOpen(false);
      setSelectedFile(null);
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["importedExpenses"] });
    } catch (error) {
      toast.error("Failed to upload invoice");
    } finally {
      setUploadingFile(false);
    }
  };

  // Calculate stats
  const currentMonth = new Date().getMonth();
  const currentYear = new Date().getFullYear();
  const monthlyExpenses = expenses.filter((exp) => {
    const expDate = new Date(exp.created_at);
    return expDate.getMonth() === currentMonth && expDate.getFullYear() === currentYear;
  });
  const monthlyTotal = monthlyExpenses.reduce((sum, exp) => sum + exp.amount, 0);
  const totalExpenses = expenses.reduce((sum, exp) => sum + exp.amount, 0);
  const avgExpense = expenses.length > 0 ? totalExpenses / expenses.length : 0;

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

  // Calculate category breakdown for top 5
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
    <div className="space-y-6">
      {/* Header with Greeting, Date and Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="flex flex-col gap-2">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground">
              Hi, {getUserName()} 👋
            </h1>
            <p className="text-base md:text-lg text-muted-foreground mt-2">{getCurrentDate()}</p>
          </div>
        </div>
        <div className="flex gap-3 self-start">
          <Dialog open={isUploadDialogOpen} onOpenChange={setIsUploadDialogOpen}>
            <DialogTrigger asChild>
              <Button 
                variant="outline"
                className="shadow-sm hover:shadow-md transition-smooth border-primary/20 hover:border-primary/40"
              >
                <Upload className="h-4 w-4 mr-2" />
                Upload Invoice
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle className="text-xl">Upload Invoice</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-primary/50 transition-colors">
                  <input
                    type="file"
                    id="invoice-upload"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <label htmlFor="invoice-upload" className="cursor-pointer">
                    <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-sm font-medium text-foreground mb-1">
                      {selectedFile ? selectedFile.name : "Click to upload or drag and drop"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      PDF, JPG, JPEG or PNG (MAX. 10MB)
                    </p>
                  </label>
                </div>
                <Button 
                  onClick={handleFileUpload} 
                  disabled={!selectedFile || uploadingFile}
                  className="w-full"
                >
                  {uploadingFile ? "Uploading..." : "Upload Invoice"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          
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
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
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
              value={`${monthlyTotal.toFixed(2)}`}
              icon={DollarSign}
            />
            <StatCard
              title="Total Expenses"
              value={`${primaryCurrency} ${totalExpenses.toFixed(2)}`}
              icon={TrendingDown}
            />
            <StatCard
              title="This Month"
              value={monthlyExpenses.length.toString()}
              icon={Calendar}
            />
            <StatCard
              title="Average"
              value={`${primaryCurrency} ${avgExpense.toFixed(2)}`}
              icon={TrendingUp}
            />
          </>
        )}
      </div>

      {/* Master Chart - Financial Overview (No Header) */}
      <Card className="shadow-elevated border-0 overflow-hidden bg-gradient-to-br from-card via-card to-primary/5">
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

      {/* Recent Transactions and Tips Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Transactions Table */}
        <Card className="shadow-elevated border-0 overflow-hidden">
          <CardHeader className="bg-gradient-to-r from-card to-muted/20 border-b">
            <CardTitle className="text-2xl font-bold text-foreground">Recent Transactions</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {isLoading ? (
              <TableSkeleton rows={8} />
            ) : expenses.length === 0 ? (
              <div className="text-center py-16">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
                  <Receipt className="h-8 w-8 text-muted-foreground" />
                </div>
                <p className="text-lg font-medium text-foreground">No expenses yet</p>
                <p className="text-sm text-muted-foreground mt-1">Add your first expense to get started</p>
              </div>
            ) : (
              <ExpenseList
                expenses={expenses.slice(0, 10)}
                onEdit={handleEdit}
                onDelete={(id) => deleteMutation.mutate(id)}
                onTransactionClick={handleTransactionClick}
              />
            )}
          </CardContent>
        </Card>

        {/* Tips and Advice Section */}
        <Card className="shadow-elevated border-0 overflow-hidden bg-gradient-to-br from-card via-card to-purple-500/5">
          <CardHeader className="bg-gradient-to-r from-card to-purple-500/10 border-b">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-6 w-6 text-purple-600" />
              <CardTitle className="text-2xl font-bold text-foreground">Tips & Advice</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            {/* Smart Saving Tip */}
            <div className="group relative overflow-hidden rounded-xl p-5 bg-gradient-to-br from-blue-500/10 via-blue-500/5 to-transparent border border-blue-500/20 hover:border-blue-500/40 transition-all duration-300 hover:shadow-lg">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <PiggyBank className="h-6 w-6 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h4 className="font-bold text-foreground mb-2 text-lg">Smart Saving Strategy</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Try the 50/30/20 rule: allocate 50% of your income to needs, 30% to wants, and 20% to savings. This balanced approach helps build wealth while enjoying life.
                  </p>
                </div>
              </div>
            </div>

            {/* Budget Tracking */}
            <div className="group relative overflow-hidden rounded-xl p-5 bg-gradient-to-br from-purple-500/10 via-purple-500/5 to-transparent border border-purple-500/20 hover:border-purple-500/40 transition-all duration-300 hover:shadow-lg">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Target className="h-6 w-6 text-purple-600" />
                </div>
                <div className="flex-1">
                  <h4 className="font-bold text-foreground mb-2 text-lg">Set Monthly Budgets</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Create category-specific budgets to track spending patterns. Review weekly to identify areas where you can cut back and redirect funds to savings goals.
                  </p>
                </div>
              </div>
            </div>

            {/* Investment Insight */}
            <div className="group relative overflow-hidden rounded-xl p-5 bg-gradient-to-br from-emerald-500/10 via-emerald-500/5 to-transparent border border-emerald-500/20 hover:border-emerald-500/40 transition-all duration-300 hover:shadow-lg">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <TrendingUpIcon className="h-6 w-6 text-emerald-600" />
                </div>
                <div className="flex-1">
                  <h4 className="font-bold text-foreground mb-2 text-lg">Start Small, Grow Big</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Even small investments compound over time. Start with 10% of your savings in low-risk index funds. Consistency beats timing the market every time.
                  </p>
                </div>
              </div>
            </div>

            {/* Emergency Fund */}
            <div className="group relative overflow-hidden rounded-xl p-5 bg-gradient-to-br from-amber-500/10 via-amber-500/5 to-transparent border border-amber-500/20 hover:border-amber-500/40 transition-all duration-300 hover:shadow-lg">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-amber-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Receipt className="h-6 w-6 text-amber-600" />
                </div>
                <div className="flex-1">
                  <h4 className="font-bold text-foreground mb-2 text-lg">Build Emergency Funds</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Aim for 3-6 months of expenses in an easily accessible account. This safety net protects you from unexpected costs and reduces financial stress.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

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

export default DashboardAnalytics;

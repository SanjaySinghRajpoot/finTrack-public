import { useState, lazy, Suspense } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton } from "@/components/ui/stat-card-skeleton";
import { TableSkeleton } from "@/components/ui/table-skeleton";
import { ExpenseList } from "@/components/ExpenseList";
import { Coins, TrendingDown, Calendar, TrendingUp, Plus, Receipt, Upload, Lightbulb, Target, PiggyBank, TrendingUpIcon, X, Mail, Sparkles, CheckCircle2, ArrowRight, FileText, PieChart, BarChart3, Clock } from "lucide-react";
import { api, CreateExpenseRequest, Expense, ImportedExpense } from "@/lib/api";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

// Lazy load heavy components - recharts is ~1.2MB!
const SpendingChart = lazy(() => import("@/components/SpendingChart"));
const ExpenseForm = lazy(() => import("@/components/ExpenseForm").then(m => ({ default: m.ExpenseForm })));
const TransactionDetailsModal = lazy(() => import("@/components/TransactionDetailsModal").then(m => ({ default: m.TransactionDetailsModal })));
const FileUploadModal = lazy(() => import("@/components/FileUploadModal").then(m => ({ default: m.FileUploadModal })));

// Chart loading skeleton
const ChartSkeleton = () => (
  <div className="w-full h-[280px] bg-muted/30 rounded-lg animate-pulse flex items-center justify-center">
    <BarChart3 className="h-12 w-12 text-muted-foreground/30" />
  </div>
);

// Header skeleton for instant LCP
const HeaderSkeleton = () => (
  <div className="flex flex-col gap-2">
    <div className="h-10 w-48 bg-muted/50 rounded-lg animate-pulse" />
    <div className="h-6 w-64 bg-muted/30 rounded animate-pulse" />
  </div>
);

// Welcome Screen Component for First-Time Users
const WelcomeScreen = ({ onAddExpense, onClose }: { onAddExpense: () => void; onClose: () => void }) => {
  const navigate = useNavigate();

  const quickStartFeatures = [
    {
      icon: Plus,
      title: "Add Your First Expense",
      description: "Start by manually adding an expense to see how it works",
      action: "Add Expense",
      color: "bg-gradient-to-br from-primary to-primary/80",
      onClick: () => { onAddExpense(); onClose(); }
    },
    {
      icon: Mail,
      title: "Connect Your Email",
      description: "Automatically import receipts and invoices from your emails",
      action: "Import Emails",
      color: "bg-gradient-to-br from-secondary to-secondary/80",
      onClick: () => { onClose(); navigate("/settings"); }
    },
    {
      icon: Upload,
      title: "Upload Documents",
      description: "Upload PDF receipts and invoices for automatic processing",
      action: "Upload Files",
      color: "bg-gradient-to-br from-accent to-accent/80",
      onClick: () => { onClose(); navigate("/transactions"); }
    }
  ];

  const features = [
    {
      icon: FileText,
      title: "Smart Receipt Processing",
      description: "AI-powered extraction of expense details from receipts and invoices"
    },
    {
      icon: PieChart,
      title: "Detailed Analytics",
      description: "Comprehensive charts and insights into your spending patterns"
    },
    {
      icon: BarChart3,
      title: "Category Management",
      description: "Organize expenses by categories for better tracking"
    },
    {
      icon: Clock,
      title: "Real-time Sync",
      description: "All your data synced across devices in real-time"
    }
  ];

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Hero Section */}
      <Card className="shadow-elevated border-border/50 overflow-hidden bg-gradient-to-br from-card via-muted/20 to-card relative">
        {/* Close Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="absolute top-4 right-4 z-10 rounded-full hover:bg-destructive/10 hover:text-destructive transition-smooth"
          title="Close welcome screen"
        >
          <X className="h-5 w-5" />
        </Button>

        <CardContent className="p-8 md:p-12 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 md:w-24 md:h-24 rounded-2xl md:rounded-3xl bg-gradient-to-br from-primary to-primary/80 mb-6 md:mb-8 shadow-lg">
            <Sparkles className="h-10 w-10 md:h-12 md:w-12 text-primary-foreground" />
          </div>
          
          <h1 className="text-3xl md:text-5xl font-bold text-foreground mb-4 md:mb-6 bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            Welcome to FinTrack! 👋
          </h1>
          
          <p className="text-lg md:text-2xl text-muted-foreground mb-3 md:mb-4 max-w-3xl mx-auto font-medium">
            Your journey to better financial management starts here
          </p>
          
          <p className="text-base md:text-lg text-muted-foreground mb-8 md:mb-10 max-w-2xl mx-auto leading-relaxed">
            Track expenses, analyze spending patterns, and take control of your finances with ease.
          </p>

          <div className="inline-flex items-center gap-2 text-xs md:text-sm text-muted-foreground bg-primary/5 px-3 md:px-4 py-1.5 md:py-2 rounded-full border border-primary/10">
            <CheckCircle2 className="h-3.5 w-3.5 md:h-4 md:w-4 text-primary" />
            <span>Get started with your first transaction</span>
          </div>
        </CardContent>
      </Card>

      {/* Quick Start Features */}
      <Card className="shadow-elevated border-border/50">
        <CardHeader className="bg-gradient-to-r from-card to-muted/20 border-b pb-4 md:pb-6">
          <div className="text-center">
            <CardTitle className="text-2xl md:text-3xl font-bold text-foreground flex items-center justify-center gap-2 md:gap-3 mb-2 md:mb-3">
              <CheckCircle2 className="h-6 w-6 md:h-8 md:w-8 text-primary" />
              Quick Start
            </CardTitle>
            <p className="text-muted-foreground text-base md:text-lg">
              Choose how you want to begin tracking your expenses
            </p>
          </div>
        </CardHeader>
        <CardContent className="p-6 md:p-8">
          <div className="grid gap-4 md:gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {quickStartFeatures.map((feature, index) => (
              <div 
                key={index}
                className="group relative p-5 md:p-6 rounded-xl md:rounded-2xl border-2 border-border/50 hover:border-primary/50 transition-smooth hover:shadow-lg cursor-pointer bg-gradient-to-br from-card to-muted/5 hover:from-primary/5 hover:to-primary/10"
                onClick={feature.onClick}
              >
                <div className="text-center">
                  <div className="inline-flex items-center justify-center mb-4 md:mb-5">
                    <div className={`p-3 md:p-4 rounded-xl md:rounded-2xl ${feature.color} shadow-md group-hover:shadow-lg group-hover:scale-110 transition-smooth`}>
                      <feature.icon className="h-6 w-6 md:h-8 md:w-8 text-primary-foreground" />
                    </div>
                  </div>
                  
                  <h3 className="text-lg md:text-xl font-bold text-foreground mb-2 md:mb-3 group-hover:text-primary transition-colors">
                    {feature.title}
                  </h3>
                  
                  <p className="text-xs md:text-sm text-muted-foreground mb-4 md:mb-5 leading-relaxed">
                    {feature.description}
                  </p>
                  
                  <Button 
                    variant="ghost" 
                    size="sm"
                    className="text-primary hover:text-primary hover:bg-primary/10 font-semibold group-hover:translate-x-1 transition-transform text-xs md:text-sm"
                  >
                    {feature.action}
                    <ArrowRight className="h-3.5 w-3.5 md:h-4 md:w-4 ml-1.5 md:ml-2" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Features Overview */}
      <Card className="shadow-elevated border-border/50 overflow-hidden">
        <CardHeader className="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border-b">
          <div className="text-center">
            <CardTitle className="text-2xl md:text-3xl font-bold text-foreground mb-2">
              Powerful Features Waiting For You
            </CardTitle>
            <p className="text-muted-foreground text-base md:text-lg">
              Once you start tracking, you'll unlock these amazing capabilities
            </p>
          </div>
        </CardHeader>
        <CardContent className="p-6 md:p-8">
          <div className="grid gap-4 md:gap-6 sm:grid-cols-2">
            {features.map((feature, index) => (
              <div key={index} className="flex items-start gap-4 md:gap-5 p-4 md:p-5 rounded-xl bg-gradient-to-br from-muted/30 to-muted/10 hover:from-primary/5 hover:to-primary/10 transition-smooth border border-border/50 hover:border-primary/30 hover:shadow-md">
                <div className="p-2.5 md:p-3 rounded-lg md:rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex-shrink-0">
                  <feature.icon className="h-5 w-5 md:h-6 md:w-6 text-primary" />
                </div>
                <div>
                  <h4 className="font-bold text-foreground mb-1.5 md:mb-2 text-base md:text-lg">
                    {feature.title}
                  </h4>
                  <p className="text-xs md:text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Motivational CTA */}
      <Card className="shadow-elevated border-border/50 bg-gradient-to-r from-primary/10 via-primary/5 to-secondary/10 overflow-hidden relative">
        <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
        <CardContent className="p-8 md:p-10 text-center relative z-10">
          <div className="max-w-2xl mx-auto">
            <h3 className="text-xl md:text-2xl font-bold text-foreground mb-3 md:mb-4">
              🚀 Ready to Take Control of Your Finances?
            </h3>
            <p className="text-muted-foreground mb-5 md:mb-6 text-base md:text-lg leading-relaxed">
              Join thousands of users who are already managing their expenses smarter. 
              Start by adding your first expense and watch your financial insights come to life!
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Tips Card */}
      <Card className="shadow-elevated border-border/50 bg-gradient-to-r from-card via-muted/20 to-card">
        <CardContent className="p-5 md:p-6">
          <div className="flex items-start gap-3 md:gap-4">
            <div className="p-2.5 md:p-3 rounded-lg md:rounded-xl bg-gradient-to-br from-primary to-primary/80 flex-shrink-0 shadow-md">
              <Receipt className="h-5 w-5 md:h-6 md:w-6 text-primary-foreground" />
            </div>
            <div>
              <h4 className="font-bold text-foreground mb-2 md:mb-3 text-base md:text-lg flex items-center gap-2">
                💡 Pro Tips to Get Started
              </h4>
              <ul className="text-xs md:text-sm text-muted-foreground space-y-2 md:space-y-2.5 leading-relaxed">
                <li className="flex items-start gap-2">
                  <span className="text-primary font-bold mt-0.5">•</span>
                  <span>Use descriptive names for your expenses to easily identify them later</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary font-bold mt-0.5">•</span>
                  <span>Categorize expenses properly - it helps generate better insights and reports</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary font-bold mt-0.5">•</span>
                  <span>Upload receipts to keep digital records and never lose track of important transactions</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary font-bold mt-0.5">•</span>
                  <span>Check your dashboard regularly to understand your spending patterns and trends</span>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const DashboardAnalytics = () => {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<Expense | ImportedExpense | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [showWelcomeScreen, setShowWelcomeScreen] = useState(() => {
    // Check localStorage to see if user has dismissed the welcome screen
    const dismissed = localStorage.getItem('welcomeScreenDismissed');
    return dismissed !== 'true';
  });

  // Fetch user data - lower priority, doesn't block render
  const { data: user, isLoading: isUserLoading } = useQuery({
    queryKey: ["user"],
    queryFn: api.getUser,
    retry: false,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  // Fetch expenses - main data, higher priority
  const { data: expensesResponse, isLoading } = useQuery({
    queryKey: ["expenses"],
    queryFn: () => api.getExpenses(100, 0), // Fetch first 100 for dashboard
    retry: false,
    staleTime: 30 * 1000, // Cache for 30 seconds
  });

  const expenses = expensesResponse?.data || [];

  // Fetch imported expenses - can load in background
  const { data: importedExpensesResponse } = useQuery({
    queryKey: ["importedExpenses"],
    queryFn: () => api.getImportedExpenses(100, 0), // Fetch first 100 for dashboard
    retry: false,
    staleTime: 30 * 1000,
  });

  const importedExpenses = importedExpensesResponse?.data || [];

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
    return "User"; // Friendlier default
  };

  const getCurrentDate = () => {
    const now = new Date();
    const options: Intl.DateTimeFormatOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return now.toLocaleDateString('en-US', options);
  };

  // Handle welcome screen close
  const handleCloseWelcomeScreen = () => {
    setShowWelcomeScreen(false);
    localStorage.setItem('welcomeScreenDismissed', 'true');
    toast.success("Welcome screen hidden. You can always add expenses using the button above!");
  };

  // Handle add expense click
  const handleAddExpenseClick = () => {
    setEditingExpense(null);
    setIsDialogOpen(true);
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

  // Calculate total expenses
  const totalExpenseAmount = expenses.reduce((sum, exp) => sum + exp.amount, 0);
  const totalImportedAmount = importedExpenses.reduce((sum, exp) => sum + exp.amount, 0);
  const grandTotal = totalExpenseAmount + totalImportedAmount;

  // Check if user is a first-time user (no expenses and welcome screen not dismissed)
  const isFirstTimeUser = !isLoading && grandTotal === 0 && showWelcomeScreen;

  return (
    <div className="space-y-6">
      {/* Show Welcome Screen for first-time users */}
      {isFirstTimeUser ? (
        <WelcomeScreen 
          onAddExpense={handleAddExpenseClick} 
          onClose={handleCloseWelcomeScreen}
        />
      ) : (
        <>
          {/* Header with Greeting, Date and Action Buttons - Shows immediately with skeleton */}
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            {isUserLoading ? (
              <HeaderSkeleton />
            ) : (
              <div className="flex flex-col gap-2">
                <div>
                  <h1 className="text-3xl md:text-4xl font-bold text-foreground">
                    Hi, {getUserName()} 👋
                  </h1>
                  <p className="text-base md:text-lg text-muted-foreground mt-2">{getCurrentDate()}</p>
                </div>
              </div>
            )}
            <div className="flex gap-3 self-start">
              <Button 
                variant="outline"
                className="shadow-sm hover:shadow-md transition-smooth border-primary/20 hover:border-primary/40"
                onClick={() => setIsUploadModalOpen(true)}
              >
                <Upload className="h-4 w-4 mr-2" />
                Upload Invoice
              </Button>
              
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
                  <Suspense fallback={<div>Loading...</div>}>
                    <ExpenseForm
                      onSubmit={handleSubmit}
                      defaultValues={editingExpense || undefined}
                      isLoading={createMutation.isPending || updateMutation.isPending}
                    />
                  </Suspense>
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
                  icon={Coins}
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
                  <Suspense fallback={<ChartSkeleton />}>
                    <SpendingChart data={last7Days} primaryCurrency={primaryCurrency} />
                  </Suspense>
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
                    <Coins className="h-4 w-4 text-purple-600" />
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
                    onDelete={(uuid) => deleteMutation.mutate(uuid)}
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
          <Suspense fallback={<div>Loading...</div>}>
            <TransactionDetailsModal
              transaction={selectedTransaction}
              isOpen={isDetailsModalOpen}
              onClose={() => {
                setIsDetailsModalOpen(false);
                setSelectedTransaction(null);
              }}
            />
          </Suspense>

          {/* File Upload Modal */}
          <Suspense fallback={<div>Loading...</div>}>
            <FileUploadModal
              isOpen={isUploadModalOpen}
              onClose={() => setIsUploadModalOpen(false)}
            />
          </Suspense>
        </>
      )}
    </div>
  );
};

export default DashboardAnalytics;

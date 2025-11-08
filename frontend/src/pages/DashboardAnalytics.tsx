import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton } from "@/components/ui/stat-card-skeleton";
import { ExpenseForm } from "@/components/ExpenseForm";
import { ExpenseList } from "@/components/ExpenseList";
import { ImportedExpenseList } from "@/components/ImportedExpenseList";
import { DollarSign, TrendingDown, Calendar, TrendingUp, Plus, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { api, CreateExpenseRequest } from "@/lib/api";
import { toast } from "sonner";
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";

const DashboardAnalytics = () => {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);

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

  // Handle form submission
  const handleSubmit = (data: CreateExpenseRequest) => {
    createMutation.mutate(data);
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

  // Calculate category breakdown for pie chart
  const categoryData = expenses.reduce((acc: any[], exp) => {
    const existing = acc.find(item => item.category === exp.category);
    if (existing) {
      existing.value += exp.amount;
    } else {
      acc.push({ category: exp.category, value: exp.amount });
    }
    return acc;
  }, []);

  // Calculate monthly trend for line chart (last 6 months)
  const monthlyTrend = Array.from({ length: 6 }, (_, i) => {
    const date = new Date();
    date.setMonth(date.getMonth() - (5 - i));
    const month = date.toLocaleString('default', { month: 'short' });
    const monthExpenses = expenses.filter(exp => {
      const expDate = new Date(exp.created_at);
      return expDate.getMonth() === date.getMonth() && expDate.getFullYear() === date.getFullYear();
    });
    return {
      month,
      amount: monthExpenses.reduce((sum, exp) => sum + exp.amount, 0)
    };
  });

  // Get last 20 transactions
  const lastTransactions = [...expenses].sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  ).slice(0, 20);

  // Get last 10 imported transactions
  const lastImported = [...importedExpenses].sort((a, b) => b.id - a.id).slice(0, 10);

  const COLORS = ['hsl(var(--chart-1))', 'hsl(var(--chart-2))', 'hsl(var(--chart-3))', 'hsl(var(--chart-4))', 'hsl(var(--chart-5))'];

  return (
    <div className="space-y-6">
      {/* Header with Greeting, Date and Add Expense Button */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="flex flex-col gap-2">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground">
              Hi, {getUserName()} 👋
            </h1>
            <p className="text-base md:text-lg text-muted-foreground mt-2">{getCurrentDate()}</p>
          </div>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button 
              className="bg-primary hover:bg-primary/90 shadow-lg self-start"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Expense
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="text-xl">
                Add New Expense
              </DialogTitle>
            </DialogHeader>
            <ExpenseForm
              onSubmit={handleSubmit}
              isLoading={createMutation.isPending}
            />
          </DialogContent>
        </Dialog>
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
              value={`$${monthlyTotal.toFixed(2)}`}
              icon={DollarSign}
              // trend={{ value: "8.2%", positive: false }}
            />
            <StatCard
              title="Total Expenses"
              value={`$${totalExpenses.toFixed(2)}`}
              icon={TrendingDown}
            />
            <StatCard
              title="This Month"
              value={monthlyExpenses.length.toString()}
              icon={Calendar}
            />
            <StatCard
              title="Average"
              value={`$${avgExpense.toFixed(2)}`}
              icon={TrendingUp}
            />
          </>
        )}
      </div>

      {/* Charts Section */}
      <div className="grid gap-4 md:gap-6 grid-cols-1 lg:grid-cols-2">
        {/* Spending Trend Chart */}
        <Card className="shadow-soft border">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-foreground">Spending Trend (Last 6 Months)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={monthlyTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Line type="monotone" dataKey="amount" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ fill: 'hsl(var(--primary))' }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Recent Transactions */}
        <Card className="shadow-soft border">
          <CardHeader className="border-b border-border bg-muted/30">
            <CardTitle className="text-lg font-semibold text-foreground">Recent Transactions</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {lastTransactions.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No transactions yet</p>
              </div>
            ) : (
              <div className="space-y-2">
                <ExpenseList
                  expenses={lastTransactions}
                  onEdit={() => {}}
                  onDelete={() => {}}
                />
              </div>
            )}
          </CardContent>
        </Card>
      
      </div>

      {/* Transactions Section - Vertical Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Category Breakdown Chart */}

      <Card className="shadow-soft border">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-foreground">Spending by Category</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ category, percent }) => `${category}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="hsl(var(--primary))"
                  dataKey="value"
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--card))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        

        {/* Imported Transactions */}
        <Card className="shadow-soft border">
          <CardHeader className="border-b border-border bg-muted/30">
            <CardTitle className="text-lg font-semibold text-foreground">Imported Transactions</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {lastImported.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No imported transactions</p>
              </div>
            ) : (
              <div className="space-y-2">
                <ImportedExpenseList
                  expenses={lastImported}
                  onImport={() => {}}
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DashboardAnalytics;

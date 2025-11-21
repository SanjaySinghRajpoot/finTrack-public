import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ExpenseForm } from "@/components/ExpenseForm";
import { TransactionDetailsModal } from "@/components/TransactionDetailsModal";
import { FileUploadModal } from "@/components/FileUploadModal";
import { ImageCaptureModal } from "@/components/ImageCaptureModal";
import { AttachmentViewerModal } from "@/components/AttachmentViewerModal";
import { TableSkeleton } from "@/components/ui/table-skeleton";
import { Plus, Upload, Camera, Pencil, Trash2, ChevronLeft, ChevronRight, Search, Filter, FileText, Download, Receipt, Check, X } from "lucide-react";
import { toast } from "sonner";
import { api, Expense, CreateExpenseRequest, ImportedExpense } from "@/lib/api";
import { getCategoryConfig } from "@/lib/categories";
import { format } from "date-fns";

const ITEMS_PER_PAGE = 10;

const Transactions = () => {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isCaptureModalOpen, setIsCaptureModalOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<Expense | ImportedExpense | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [selectedAttachment, setSelectedAttachment] = useState<{
    s3Url: string;
    filename: string;
    mimeType: string;
  } | null>(null);

  // Table state
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [viewType, setViewType] = useState<"expenses" | "imported">("expenses");

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
      queryClient.invalidateQueries({ queryKey: ["importedExpenses"] });
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

  const handleTransactionClick = (transaction: Expense | ImportedExpense) => {
    setSelectedTransaction(transaction);
    setIsDetailsModalOpen(true);
  };

  const handleViewAttachment = (expense: ImportedExpense | Expense) => {
    // Handle both ImportedExpense and Expense with processed_data
    let attachment = null;
    
    if ('attachment' in expense) {
      // It's an ImportedExpense
      attachment = expense.attachment;
    } else if ('processed_data' in expense && expense.processed_data && expense.processed_data.length > 0) {
      // It's an Expense with processed_data array - get first item
      attachment = expense.processed_data[0]?.attachment;
    }
    
    if (!attachment?.s3_url) return;
    
    setSelectedAttachment({
      s3Url: attachment.s3_url,
      filename: attachment.filename || "document",
      mimeType: attachment.mime_type || "application/octet-stream",
    });
  };

  // Filter and pagination logic
  const filteredData = useMemo(() => {
    if (viewType === "expenses") {
      let filtered = [...expenses];

      // Search filter
      if (searchQuery) {
        const searchText = searchQuery.toLowerCase();
        filtered = filtered.filter((item) =>
          item.description.toLowerCase().includes(searchText) ||
          item.category.toLowerCase().includes(searchText)
        );
      }

      // Category filter
      if (categoryFilter !== "all") {
        filtered = filtered.filter((item) => item.category === categoryFilter);
      }

      return filtered;
    } else {
      let filtered = [...importedExpenses];

      // Search filter
      if (searchQuery) {
        const searchText = searchQuery.toLowerCase();
        filtered = filtered.filter((item) =>
          item.title.toLowerCase().includes(searchText) ||
          (item.category?.toLowerCase().includes(searchText)) ||
          (item.vendor_name?.toLowerCase().includes(searchText))
        );
      }

      // Category filter
      if (categoryFilter !== "all") {
        filtered = filtered.filter((item) => item.category === categoryFilter);
      }

      return filtered;
    }
  }, [viewType, expenses, importedExpenses, searchQuery, categoryFilter]);

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set<string>();
    if (viewType === "expenses") {
      expenses.forEach((item) => cats.add(item.category));
    } else {
      importedExpenses.forEach((item) => {
        if (item.category) cats.add(item.category);
      });
    }
    return Array.from(cats).sort();
  }, [viewType, expenses, importedExpenses]);

  // Pagination
  const totalPages = Math.ceil(filteredData.length / ITEMS_PER_PAGE);
  const paginatedData = filteredData.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  // Reset to page 1 when filters change
  useMemo(() => {
    setCurrentPage(1);
  }, [searchQuery, categoryFilter, viewType]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-primary">
            All Transactions
          </h1>
          <p className="text-sm md:text-base text-muted-foreground mt-1">Manage all your expenses and imports</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Capture Invoice Button */}
          <Button 
            className="bg-primary hover:bg-primary/90 shadow-lg"
            onClick={() => setIsCaptureModalOpen(true)}
          >
            <Camera className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Capture</span>
          </Button>
          
          {/* Upload Invoice Button */}
          <Button 
            className="bg-primary hover:bg-primary/90 shadow-lg"
            onClick={() => setIsUploadModalOpen(true)}
          >
            <Upload className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Upload Invoice</span>
          </Button>
          
          {/* Add Expense Button */}
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button 
                className="bg-primary hover:bg-primary/90 shadow-lg"
                onClick={() => setEditingExpense(null)}
              >
                <Plus className="h-4 w-4 mr-2" />
                <span className="hidden sm:inline">Add Expense</span>
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
        <CardHeader className="pb-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            {/* View Type Toggle */}
            <div className="flex items-center gap-2 bg-muted p-1 rounded-lg w-fit">
              <Button
                variant={viewType === "expenses" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewType("expenses")}
                className="h-9"
              >
                <Receipt className="h-4 w-4 mr-2" />
                My Expenses ({expenses.length})
              </Button>
              <Button
                variant={viewType === "imported" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewType("imported")}
                className="h-9"
              >
                <FileText className="h-4 w-4 mr-2" />
                Imported ({importedExpenses.length})
              </Button>
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search transactions..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                <SelectTrigger className="w-full sm:w-[180px]">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categories.map((cat) => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6">
              <TableSkeleton rows={10} />
            </div>
          ) : filteredData.length === 0 ? (
            <div className="text-center py-12 md:py-16">
              <div className="inline-flex items-center justify-center w-12 h-12 md:w-16 md:h-16 rounded-full bg-primary/10 mb-4">
                <Receipt className="h-6 w-6 md:h-8 md:w-8 text-primary" />
              </div>
              <p className="text-base md:text-lg font-medium text-foreground">
                {searchQuery || categoryFilter !== "all" 
                  ? "No transactions found" 
                  : `No ${viewType === "expenses" ? "expenses" : "imported transactions"} yet`}
              </p>
              <p className="text-xs md:text-sm text-muted-foreground mt-1">
                {searchQuery || categoryFilter !== "all"
                  ? "Try adjusting your filters"
                  : viewType === "expenses" 
                    ? "Add your first expense to get started"
                    : "Import expenses to see them here"}
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="w-[60px] font-semibold text-foreground">#</TableHead>
                      <TableHead className="w-[300px] font-semibold text-foreground">Description</TableHead>
                      <TableHead className="w-[120px] font-semibold text-foreground">Date</TableHead>
                      <TableHead className="w-[140px] text-right font-semibold text-foreground">Amount</TableHead>
                      <TableHead className="w-[140px] font-semibold text-foreground">Category</TableHead>
                      <TableHead className="w-[140px] font-semibold text-foreground">Vendor</TableHead>
                      <TableHead className="w-[120px] font-semibold text-foreground">Doc Type</TableHead>
                      <TableHead className="w-[130px] font-semibold text-foreground">Doc Number</TableHead>
                      <TableHead className="w-[120px] font-semibold text-foreground">Payment</TableHead>
                      <TableHead className="w-[130px] text-right font-semibold text-foreground">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedData.map((item, index) => {
                      const isExpense = 'description' in item;
                      // Get first item from processed_data array
                      const processedData = isExpense && (item as Expense).processed_data && (item as Expense).processed_data!.length > 0 
                        ? (item as Expense).processed_data![0] 
                        : null;
                      const categoryConfig = getCategoryConfig(
                        isExpense ? item.category : (item.category || "Other")
                      );
                      const Icon = categoryConfig.icon;
                      const serialNumber = index + 1 + (currentPage - 1) * ITEMS_PER_PAGE;

                      return (
                        <TableRow 
                          key={isExpense ? item.uuid : item.id}
                          className="cursor-pointer hover:bg-muted/30 transition-colors"
                          onClick={() => handleTransactionClick(item)}
                        >
                          <TableCell className="w-[60px] text-muted-foreground font-medium">
                            {serialNumber}
                          </TableCell>
                          <TableCell className="w-[300px]">
                            <div className="max-w-[300px]">
                              <p className="font-semibold text-foreground text-sm leading-relaxed overflow-hidden text-ellipsis whitespace-nowrap" title={isExpense ? item.description : item.title}>
                                {isExpense 
                                  ? (item.description.length > 50 ? item.description.substring(0, 50) + '...' : item.description)
                                  : (item.title.length > 50 ? item.title.substring(0, 50) + '...' : item.title)
                                }
                              </p>
                              {!isExpense && item.description && (
                                <p className="text-xs text-muted-foreground mt-1 leading-relaxed overflow-hidden text-ellipsis whitespace-nowrap" title={item.description}>
                                  {item.description.length > 50 ? item.description.substring(0, 70) + '...' : item.description}
                                </p>
                              )}
                              {isExpense && processedData?.description && (
                                <p className="text-xs text-muted-foreground mt-1 leading-relaxed overflow-hidden text-ellipsis whitespace-nowrap" title={processedData.description}>
                                  {processedData.description.length > 50 ? processedData.description.substring(0, 70) + '...' : processedData.description}
                                </p>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="w-[120px] text-sm text-muted-foreground font-medium">
                            {format(
                              new Date(isExpense ? item.created_at : item.created_at),
                              "MMM dd, yyyy"
                            )}
                          </TableCell>
                          <TableCell className="w-[140px] text-right">
                            <div className="flex flex-col items-end">
                              <span className="font-bold text-foreground text-base tabular-nums">
                                {item.amount.toFixed(2)}
                              </span>
                              <span className="text-xs text-muted-foreground font-medium">
                                {item.currency}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="w-[140px]">
                            <div className="flex items-center gap-2">
                              <div
                                className="h-8 w-8 rounded-md flex items-center justify-center shrink-0"
                                style={{ backgroundColor: categoryConfig.bgColor }}
                              >
                                <Icon className="h-4 w-4" style={{ color: categoryConfig.color }} />
                              </div>
                              <span className="text-sm font-medium text-foreground overflow-hidden text-ellipsis whitespace-nowrap" title={isExpense ? item.category : (item.category || "N/A")}>
                                {isExpense ? item.category : (item.category || "N/A")}
                              </span>
                            </div>
                          </TableCell>
                          
                          {/* Vendor Column */}
                          <TableCell className="w-[140px]">
                            {(() => {
                              const vendorName = isExpense ? processedData?.vendor_name : (item as ImportedExpense).vendor_name;
                              return vendorName ? (
                                <span className="text-sm font-medium text-foreground overflow-hidden text-ellipsis whitespace-nowrap block" title={vendorName}>
                                  {vendorName.length > 30 ? vendorName.substring(0, 30) + '...' : vendorName}
                                </span>
                              ) : (
                                <span className="text-sm text-muted-foreground">—</span>
                              );
                            })()}
                          </TableCell>

                          {/* Document Type Column */}
                          <TableCell className="w-[120px]">
                            {(() => {
                              const docType = isExpense ? processedData?.document_type : (item as ImportedExpense).document_type;
                              return docType ? (
                                <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 max-w-full overflow-hidden text-ellipsis whitespace-nowrap" title={docType}>
                                  {docType.length > 15 ? docType.substring(0, 15) + '...' : docType}
                                </span>
                              ) : (
                                <span className="text-sm text-muted-foreground">—</span>
                              );
                            })()}
                          </TableCell>

                          {/* Document Number Column */}
                          <TableCell className="w-[130px]">
                            {(() => {
                              const docNumber = isExpense ? processedData?.document_number : (item as ImportedExpense).document_number;
                              return docNumber ? (
                                <span className="text-sm font-mono font-medium text-foreground overflow-hidden text-ellipsis whitespace-nowrap block" title={docNumber}>
                                  {docNumber.length > 20 ? docNumber.substring(0, 20) + '...' : docNumber}
                                </span>
                              ) : (
                                <span className="text-sm text-muted-foreground">—</span>
                              );
                            })()}
                          </TableCell>

                          {/* Payment Method Column */}
                          <TableCell className="w-[120px]">
                            {(() => {
                              const paymentMethod = isExpense ? processedData?.payment_method : (item as ImportedExpense).payment_method;
                              return paymentMethod ? (
                                <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 max-w-full overflow-hidden text-ellipsis whitespace-nowrap" title={paymentMethod}>
                                  {paymentMethod.length > 15 ? paymentMethod.substring(0, 15) + '...' : paymentMethod}
                                </span>
                              ) : (
                                <span className="text-sm text-muted-foreground">—</span>
                              );
                            })()}
                          </TableCell>

                          {/* Actions Column */}
                          <TableCell className="w-[130px] text-right">
                            <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                              {viewType === "expenses" ? (
                                <>
                                  {/* Show attachment viewer for expenses with processed data */}
                                  {processedData?.attachment?.s3_url && (
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleViewAttachment(item as Expense);
                                      }}
                                      className="h-8 w-8 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 transition-colors"
                                      title="View attachment"
                                    >
                                      <FileText className="h-4 w-4" />
                                    </Button>
                                  )}
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleEdit(item as Expense);
                                    }}
                                    className="h-8 w-8 hover:bg-primary/10 text-primary transition-colors"
                                    title="Edit"
                                  >
                                    <Pencil className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      deleteMutation.mutate((item as Expense).id);
                                    }}
                                    className="h-8 w-8 hover:bg-destructive/10 text-destructive transition-colors"
                                    title="Delete"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </>
                              ) : (
                                <>
                                  {(item as ImportedExpense).attachment?.s3_url && (
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleViewAttachment(item as ImportedExpense);
                                      }}
                                      className="h-8 w-8 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 transition-colors"
                                      title="View attachment"
                                    >
                                      <FileText className="h-4 w-4" />
                                    </Button>
                                  )}
                                  <Button
                                    size="sm"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleImport(item as ImportedExpense);
                                    }}
                                    className="bg-gradient-to-r from-success to-success/80 hover:opacity-90 h-8 font-medium transition-opacity"
                                  >
                                    <Download className="h-3.5 w-3.5 mr-1" />
                                    Import
                                  </Button>
                                </>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1} to{" "}
                    {Math.min(currentPage * ITEMS_PER_PAGE, filteredData.length)} of{" "}
                    {filteredData.length} transactions
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <div className="flex items-center gap-1">
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
                        // Show first, last, current, and adjacent pages
                        if (
                          page === 1 ||
                          page === totalPages ||
                          (page >= currentPage - 1 && page <= currentPage + 1)
                        ) {
                          return (
                            <Button
                              key={page}
                              variant={currentPage === page ? "default" : "outline"}
                              size="sm"
                              onClick={() => setCurrentPage(page)}
                              className="w-9"
                            >
                              {page}
                            </Button>
                          );
                        } else if (page === currentPage - 2 || page === currentPage + 2) {
                          return <span key={page} className="px-1">...</span>;
                        }
                        return null;
                      })}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* File Upload Modal */}
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />

      {/* Image Capture Modal */}
      <ImageCaptureModal
        isOpen={isCaptureModalOpen}
        onClose={() => setIsCaptureModalOpen(false)}
      />

      {/* Attachment Viewer Modal */}
      <AttachmentViewerModal
        isOpen={!!selectedAttachment}
        onClose={() => setSelectedAttachment(null)}
        s3Url={selectedAttachment?.s3Url || null}
        filename={selectedAttachment?.filename}
        mimeType={selectedAttachment?.mimeType}
      />

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

export default Transactions;
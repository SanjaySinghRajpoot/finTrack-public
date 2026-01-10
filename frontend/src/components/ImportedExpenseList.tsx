import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, ExternalLink, FileText, ChevronLeft, ChevronRight } from "lucide-react";
import { ImportedExpense, api } from "@/lib/api";
import { getCategoryConfig } from "@/lib/categories";
import { useState, useMemo } from "react";
import { AttachmentViewerModal } from "@/components/AttachmentViewerModal";

interface ImportedExpenseListProps {
  expenses: ImportedExpense[];
  onImport: (expense: ImportedExpense) => void;
  onTransactionClick?: (expense: ImportedExpense) => void;
}

const ITEMS_PER_PAGE = 10;

export function ImportedExpenseList({ expenses, onImport, onTransactionClick }: ImportedExpenseListProps) {
  const [selectedAttachment, setSelectedAttachment] = useState<{
    s3Url: string;
    filename: string;
    mimeType: string;
  } | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  // Pagination logic
  const totalPages = Math.ceil(expenses.length / ITEMS_PER_PAGE);
  const paginatedExpenses = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    return expenses.slice(startIndex, endIndex);
  }, [expenses, currentPage]);

  // Reset to page 1 when expenses change
  useMemo(() => {
    setCurrentPage(1);
  }, [expenses.length]);

  const handleViewAttachment = (expense: ImportedExpense) => {
    if (!expense.attachment?.s3_url) return;
    
    setSelectedAttachment({
      s3Url: expense.attachment.s3_url,
      filename: expense.attachment.filename || "document",
      mimeType: expense.attachment.mime_type || "application/octet-stream",
    });
  };

  if (expenses.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No imported expenses available.</p>
      </div>
    );
  }

  return (
    <>
      <AttachmentViewerModal
        isOpen={!!selectedAttachment}
        onClose={() => setSelectedAttachment(null)}
        s3Url={selectedAttachment?.s3Url || null}
        filename={selectedAttachment?.filename}
        mimeType={selectedAttachment?.mimeType}
      />

      <div className="space-y-2">
        {paginatedExpenses.map((expense, index) => {
          const categoryConfig = getCategoryConfig(expense.category || "Other");
          const Icon = categoryConfig.icon;
          const hasAttachment = expense.attachment?.s3_url;

          return (
            <Card key={index} className="shadow-sm hover:shadow-md transition-smooth border border-border/50 bg-card">
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
                    <div className="flex items-baseline gap-2 mb-1">
                      <h3 
                        className="font-medium text-sm text-foreground truncate max-w-[250px]" 
                        title={expense.title || expense.vendor_name || 'Untitled'}
                      >
                        {expense.title || expense.vendor_name || 'Untitled'}
                      </h3>
                      {expense.category && (
                        <span className="text-xs px-2 py-0.5 rounded-md bg-accent/10 text-accent-foreground shrink-0">
                          {expense.category}
                        </span>
                      )}
                    </div>
                    {expense.description && (
                      <p 
                        className="text-xs text-muted-foreground line-clamp-1 mb-1" 
                        title={expense.description}
                      >
                        {expense.description}
                      </p>
                    )}
                    <div className="flex items-center gap-2 flex-wrap">
                      {expense.vendor_name && (
                        <Badge 
                          variant="secondary" 
                          className="text-xs h-5 px-2 max-w-[150px] truncate"
                          title={expense.vendor_name}
                        >
                          {expense.vendor_name}
                        </Badge>
                      )}
                      {expense.document_type && (
                        <Badge 
                          variant="outline" 
                          className="text-xs h-5 px-2"
                        >
                          {expense.document_type}
                        </Badge>
                      )}
                      {expense.is_paid !== undefined && (
                        <Badge 
                          variant={expense.is_paid ? "default" : "destructive"}
                          className="text-xs h-5 px-2"
                        >
                          {expense.is_paid ? "Paid" : "Unpaid"}
                        </Badge>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <div className="text-right">
                      <p className="text-base font-bold text-foreground whitespace-nowrap">
                        {expense.currency} {expense.amount.toFixed(2)}
                      </p>
                    </div>
                    
                    {hasAttachment && (
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleViewAttachment(expense);
                        }}
                        size="sm"
                        variant="outline"
                        className="h-8 w-8 p-0"
                        title="View attachment"
                      >
                        <FileText className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        onImport(expense);
                      }}
                      size="sm"
                      className="bg-gradient-to-r from-success to-success/80 hover:opacity-90 h-8"
                    >
                      <Download className="h-3.5 w-3.5 mr-1" />
                      Import
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t">
          <p className="text-sm text-muted-foreground">
            Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1} to{" "}
            {Math.min(currentPage * ITEMS_PER_PAGE, expenses.length)} of{" "}
            {expenses.length} imported expenses
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
  );
}
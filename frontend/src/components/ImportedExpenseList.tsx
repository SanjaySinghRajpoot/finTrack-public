import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, ExternalLink, FileText } from "lucide-react";
import { ImportedExpense, api } from "@/lib/api";
import { getCategoryConfig } from "@/lib/categories";
import { useState } from "react";
import { AttachmentViewerModal } from "@/components/AttachmentViewerModal";

interface ImportedExpenseListProps {
  expenses: ImportedExpense[];
  onImport: (expense: ImportedExpense) => void;
  onTransactionClick?: (expense: ImportedExpense) => void;
}

export function ImportedExpenseList({ expenses, onImport, onTransactionClick }: ImportedExpenseListProps) {
  const [selectedAttachment, setSelectedAttachment] = useState<{
    s3Url: string;
    filename: string;
    mimeType: string;
  } | null>(null);

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
        {expenses.map((expense, index) => {
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
                      <h3 className="font-medium text-sm text-foreground truncate">{expense.title}</h3>
                      {expense.category && (
                        <span className="text-xs px-2 py-0.5 rounded-md bg-accent/10 text-accent-foreground shrink-0">
                          {expense.category}
                        </span>
                      )}
                    </div>
                    {expense.description && (
                      <p className="text-xs text-muted-foreground line-clamp-1 mb-1">
                        {expense.description}
                      </p>
                    )}
                    <div className="flex items-center gap-2 flex-wrap">
                      {expense.vendor_name && (
                        <Badge variant="secondary" className="text-xs h-5 px-2">
                          {expense.vendor_name}
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
                      <p className="text-base font-bold text-foreground">
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
    </>
  );
}
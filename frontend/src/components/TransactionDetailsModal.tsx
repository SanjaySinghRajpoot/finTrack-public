import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Calendar, Banknote, Tag, FileText, Building, CreditCard, CheckCircle, XCircle, Clock, Package, Percent, ShoppingCart } from "lucide-react";
import { Expense, ImportedExpense } from "@/lib/api";
import { getCategoryConfig } from "@/lib/categories";
import { format } from "date-fns";

interface TransactionDetailsModalProps {
  transaction: Expense | ImportedExpense | null;
  isOpen: boolean;
  onClose: () => void;
}

const isImportedExpense = (transaction: Expense | ImportedExpense): transaction is ImportedExpense => {
  return 'vendor_name' in transaction;
};

export function TransactionDetailsModal({ transaction, isOpen, onClose }: TransactionDetailsModalProps) {
  if (!transaction) return null;

  const categoryConfig = getCategoryConfig(transaction.category || "Other");
  const Icon = categoryConfig.icon;
  const isImported = isImportedExpense(transaction);
  
  // Get processed data from expense if it exists
  const processedData = !isImported && 'processed_data' in transaction && transaction.processed_data && transaction.processed_data.length > 0 
    ? transaction.processed_data[0] 
    : null;
  
  // Get processed items - either from imported expense or from processed_data
  const processedItems = isImported ? transaction.processed_items : (processedData?.processed_items || []);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader className="space-y-4">
          <div className="flex items-center gap-3">
            <div
              className="h-12 w-12 rounded-xl flex items-center justify-center"
              style={{ backgroundColor: categoryConfig.bgColor }}
            >
              <Icon className="h-6 w-6" style={{ color: categoryConfig.color }} />
            </div>
            <div className="flex-1">
              <DialogTitle className="text-xl font-semibold text-foreground">
                {isImported ? transaction.title : transaction.description}
              </DialogTitle>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="secondary" className="text-xs">
                  {isImported ? "Imported" : "Manual"}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {transaction.category || "Other"}
                </Badge>
              </div>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6">
          {/* Amount Section */}
          <Card className="border-l-4 border-l-primary bg-primary/5">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Banknote className="h-5 w-5 text-primary" />
                  <span className="text-sm font-medium text-muted-foreground">Amount</span>
                </div>
                <span className="text-2xl font-bold text-primary">
                  {transaction.currency} {transaction.amount.toFixed(2)}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Transaction Details */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground">Transaction Details</h3>
            
            <div className="grid gap-4">
              {/* Date */}
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground min-w-[80px]">Date:</span>
                <span className="text-sm font-medium text-foreground">
                  {format(new Date(transaction.created_at), "EEEE, MMMM dd, yyyy 'at' HH:mm")}
                </span>
              </div>

              {/* Category */}
              <div className="flex items-center gap-3">
                <Tag className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground min-w-[80px]">Category:</span>
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4" style={{ color: categoryConfig.color }} />
                  <span className="text-sm font-medium text-foreground">
                    {transaction.category || "Other"}
                  </span>
                </div>
              </div>

              {/* Currency */}
              <div className="flex items-center gap-3">
                <CreditCard className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground min-w-[80px]">Currency:</span>
                <span className="text-sm font-medium text-foreground">{transaction.currency}</span>
              </div>

              {/* Description */}
              {(isImported ? transaction.description : transaction.description) && (
                <div className="flex items-start gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground mt-0.5" />
                  <span className="text-sm text-muted-foreground min-w-[80px]">Description:</span>
                  <span className="text-sm text-foreground leading-relaxed">
                    {isImported ? transaction.description : transaction.description}
                  </span>
                </div>
              )}

              {/* Imported Transaction Specific Fields */}
              {isImported && (
                <>
                  {transaction.vendor_name && (
                    <div className="flex items-center gap-3">
                      <Building className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground min-w-[80px]">Vendor:</span>
                      <span className="text-sm font-medium text-foreground">{transaction.vendor_name}</span>
                    </div>
                  )}

                  {transaction.is_paid !== undefined && (
                    <div className="flex items-center gap-3">
                      {transaction.is_paid ? (
                        <CheckCircle className="h-4 w-4 text-success" />
                      ) : (
                        <XCircle className="h-4 w-4 text-destructive" />
                      )}
                      <span className="text-sm text-muted-foreground min-w-[80px]">Status:</span>
                      <Badge variant={transaction.is_paid ? "default" : "destructive"} className="text-xs">
                        {transaction.is_paid ? "Paid" : "Unpaid"}
                      </Badge>
                    </div>
                  )}
                </>
              )}

              {/* Manual Transaction Specific Fields */}
              {!isImported && (
                <div className="flex items-center gap-3">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground min-w-[80px]">ID:</span>
                  <span className="text-sm font-mono text-foreground">{transaction.uuid}</span>
                </div>
              )}
            </div>
          </div>

          {/* Items Section - Only for Imported Expenses with processed_items */}
          {processedItems && processedItems.length > 0 && (
            <>
              <Separator />
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <ShoppingCart className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-semibold text-foreground">Items</h3>
                  <Badge variant="secondary" className="ml-auto text-xs">
                    {processedItems.length} item{processedItems.length !== 1 ? 's' : ''}
                  </Badge>
                </div>
                
                <div className="space-y-3">
                  {processedItems.map((item, index) => (
                    <Card key={item.id} className="border border-border/50 bg-card/50">
                      <CardContent className="p-4">
                        <div className="space-y-3">
                          {/* Item Header */}
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <Package className="h-4 w-4 text-primary shrink-0" />
                                <h4 className="font-medium text-sm text-foreground truncate">
                                  {item.item_name}
                                </h4>
                              </div>
                              {item.item_code && (
                                <p className="text-xs text-muted-foreground mt-1 ml-6">
                                  Code: {item.item_code}
                                </p>
                              )}
                              {item.category && (
                                <Badge variant="outline" className="text-xs mt-2 ml-6">
                                  {item.category}
                                </Badge>
                              )}
                            </div>
                            <div className="text-right shrink-0">
                              <p className="text-base font-bold text-foreground">
                                {item.currency} {item.total_amount.toFixed(2)}
                              </p>
                            </div>
                          </div>

                          {/* Item Details Grid */}
                          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs bg-muted/30 rounded-lg p-3">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Quantity:</span>
                              <span className="font-medium text-foreground">
                                {item.quantity} {item.unit || 'unit'}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Rate:</span>
                              <span className="font-medium text-foreground">
                                {item.currency} {item.rate.toFixed(2)}
                              </span>
                            </div>
                            {item.discount > 0 && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Discount:</span>
                                <span className="font-medium text-success">
                                  - {item.currency} {item.discount.toFixed(2)}
                                </span>
                              </div>
                            )}
                            {item.tax_percent > 0 && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Tax:</span>
                                <span className="font-medium text-foreground">
                                  {item.tax_percent.toFixed(2)}%
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Calculation breakdown if there's discount or tax */}
                          {(item.discount > 0 || item.tax_percent > 0) && (
                            <div className="text-xs space-y-1 pt-2 border-t border-border/50">
                              <div className="flex justify-between text-muted-foreground">
                                <span>Subtotal:</span>
                                <span>{item.currency} {(item.quantity * item.rate).toFixed(2)}</span>
                              </div>
                              {item.discount > 0 && (
                                <div className="flex justify-between text-success">
                                  <span>Discount:</span>
                                  <span>- {item.currency} {item.discount.toFixed(2)}</span>
                                </div>
                              )}
                              {item.tax_percent > 0 && (
                                <div className="flex justify-between text-muted-foreground">
                                  <span>Tax ({item.tax_percent}%):</span>
                                  <span>
                                    + {item.currency} {(((item.quantity * item.rate - item.discount) * item.tax_percent) / 100).toFixed(2)}
                                  </span>
                                </div>
                              )}
                              <div className="flex justify-between font-semibold text-foreground pt-1 border-t border-border/50">
                                <span>Total:</span>
                                <span>{item.currency} {item.total_amount.toFixed(2)}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Additional Information */}
          <Separator />
          
          <div className="text-xs text-muted-foreground space-y-1">
            <p>Transaction ID: {isImported ? transaction.id : transaction.uuid}</p>
            <p>Created: {format(new Date(transaction.created_at), "PPpp")}</p>
            {/* {!isImported && transaction.updated_at && (
              <p>Updated: {format(new Date(transaction.updated_at), "PPpp")}</p>
            )} */}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
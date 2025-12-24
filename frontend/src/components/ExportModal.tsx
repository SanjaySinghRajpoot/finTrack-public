import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Download, FileSpreadsheet, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { Expense, ImportedExpense, CustomFieldDefinition } from "@/lib/api";
import { format } from "date-fns";

interface ExportColumn {
  id: string;
  label: string;
  selected: boolean;
  getValue: (item: Expense | ImportedExpense, customFields?: CustomFieldDefinition[]) => string;
}

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: (Expense | ImportedExpense)[];
  viewType: "expenses" | "imported";
  customFields: CustomFieldDefinition[];
}

// Helper to check if item is an Expense
const isExpense = (item: Expense | ImportedExpense): item is Expense => {
  return 'description' in item && 'uuid' in item;
};

// Helper to get processed data from expense
const getProcessedData = (item: Expense | ImportedExpense) => {
  if (isExpense(item)) {
    return item.processed_data?.[0] || null;
  }
  return null;
};

// Helper to get custom field value
const getCustomFieldValue = (item: Expense | ImportedExpense, fieldName: string): string => {
  let customFieldsData: Record<string, any> | undefined;

  if (isExpense(item)) {
    const processedData = item.processed_data?.[0];
    customFieldsData = processedData?.meta_data?.custom_fields;
  } else {
    customFieldsData = (item as ImportedExpense).meta_data?.custom_fields;
  }

  const value = customFieldsData?.[fieldName];
  
  if (value === null || value === undefined) {
    return "";
  }
  
  if (typeof value === 'boolean') {
    return value ? "Yes" : "No";
  }
  
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  
  return String(value);
};

// Define base columns
const getBaseColumns = (): ExportColumn[] => [
  {
    id: "serial",
    label: "Serial No.",
    selected: true,
    getValue: () => "", // Will be set dynamically during export
  },
  {
    id: "description",
    label: "Description",
    selected: true,
    getValue: (item) => {
      if (isExpense(item)) {
        return item.description || getProcessedData(item)?.vendor_name || "";
      }
      return (item as ImportedExpense).title || (item as ImportedExpense).vendor_name || "";
    },
  },
  {
    id: "date",
    label: "Date",
    selected: true,
    getValue: (item) => format(new Date(item.created_at), "yyyy-MM-dd"),
  },
  {
    id: "amount",
    label: "Amount",
    selected: true,
    getValue: (item) => item.amount.toFixed(2),
  },
  {
    id: "currency",
    label: "Currency",
    selected: true,
    getValue: (item) => item.currency,
  },
  {
    id: "category",
    label: "Category",
    selected: true,
    getValue: (item) => {
      if (isExpense(item)) {
        return item.category;
      }
      return (item as ImportedExpense).category || "";
    },
  },
  {
    id: "vendor",
    label: "Vendor",
    selected: true,
    getValue: (item) => {
      if (isExpense(item)) {
        return getProcessedData(item)?.vendor_name || "";
      }
      return (item as ImportedExpense).vendor_name || "";
    },
  },
  {
    id: "documentType",
    label: "Document Type",
    selected: true,
    getValue: (item) => {
      if (isExpense(item)) {
        return getProcessedData(item)?.document_type || "";
      }
      return (item as ImportedExpense).document_type || "";
    },
  },
  {
    id: "documentNumber",
    label: "Document Number",
    selected: true,
    getValue: (item) => {
      if (isExpense(item)) {
        return getProcessedData(item)?.document_number || "";
      }
      return (item as ImportedExpense).document_number || "";
    },
  },
  {
    id: "paymentMethod",
    label: "Payment Method",
    selected: true,
    getValue: (item) => {
      if (isExpense(item)) {
        return getProcessedData(item)?.payment_method || "";
      }
      return (item as ImportedExpense).payment_method || "";
    },
  },
];

export function ExportModal({ isOpen, onClose, data, viewType, customFields }: ExportModalProps) {
  const [filename, setFilename] = useState(() => {
    const date = format(new Date(), "yyyy-MM-dd");
    return `${viewType === "expenses" ? "expenses" : "imported_transactions"}_${date}`;
  });
  const [rowCount, setRowCount] = useState<string>("all");
  const [customRowCount, setCustomRowCount] = useState<string>("");
  const [columns, setColumns] = useState<ExportColumn[]>(() => getBaseColumns());
  const [isExporting, setIsExporting] = useState(false);
  const [exportComplete, setExportComplete] = useState(false);

  // Build columns including custom fields
  const allColumns = useMemo(() => {
    const customFieldColumns: ExportColumn[] = customFields.map((field) => ({
      id: `custom_${field.name}`,
      label: field.label,
      selected: true,
      getValue: (item: Expense | ImportedExpense) => getCustomFieldValue(item, field.name),
    }));

    return [...columns, ...customFieldColumns];
  }, [columns, customFields]);

  // Calculate actual row count to export
  const actualRowCount = useMemo(() => {
    if (rowCount === "all") return data.length;
    if (rowCount === "custom") {
      const custom = parseInt(customRowCount, 10);
      return isNaN(custom) || custom <= 0 ? data.length : Math.min(custom, data.length);
    }
    return Math.min(parseInt(rowCount, 10), data.length);
  }, [rowCount, customRowCount, data.length]);

  const toggleColumn = (columnId: string) => {
    // For base columns
    setColumns((prev) =>
      prev.map((col) =>
        col.id === columnId ? { ...col, selected: !col.selected } : col
      )
    );
  };

  const toggleAllColumns = (selected: boolean) => {
    setColumns((prev) => prev.map((col) => ({ ...col, selected })));
  };

  const selectedColumnsCount = allColumns.filter((col) => col.selected).length;
  const allColumnsSelected = selectedColumnsCount === allColumns.length;
  const someColumnsSelected = selectedColumnsCount > 0 && selectedColumnsCount < allColumns.length;

  // Generate CSV content
  const generateCSV = (): string => {
    const selectedCols = allColumns.filter((col) => col.selected);
    const dataToExport = data.slice(0, actualRowCount);

    // Header row
    const headers = selectedCols.map((col) => `"${col.label}"`).join(",");

    // Data rows
    const rows = dataToExport.map((item, index) => {
      return selectedCols
        .map((col) => {
          let value: string;
          if (col.id === "serial") {
            value = String(index + 1);
          } else {
            value = col.getValue(item, customFields);
          }
          // Escape quotes and wrap in quotes
          return `"${value.replace(/"/g, '""')}"`;
        })
        .join(",");
    });

    return [headers, ...rows].join("\n");
  };

  // Handle export
  const handleExport = () => {
    if (selectedColumnsCount === 0) {
      toast.error("Please select at least one column to export");
      return;
    }

    if (actualRowCount === 0) {
      toast.error("No data to export");
      return;
    }

    setIsExporting(true);

    try {
      const csv = generateCSV();
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      
      const link = document.createElement("a");
      link.href = url;
      link.download = `${filename || "export"}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setExportComplete(true);
      toast.success(`Successfully exported ${actualRowCount} rows to ${filename}.csv`);

      // Auto close after a brief delay
      setTimeout(() => {
        handleClose();
      }, 1500);
    } catch (error) {
      console.error("Export error:", error);
      toast.error("Failed to export data");
    } finally {
      setIsExporting(false);
    }
  };

  const handleClose = () => {
    setExportComplete(false);
    setRowCount("all");
    setCustomRowCount("");
    setColumns(getBaseColumns());
    onClose();
  };

  // Reset filename when viewType changes
  useMemo(() => {
    const date = format(new Date(), "yyyy-MM-dd");
    setFilename(`${viewType === "expenses" ? "expenses" : "imported_transactions"}_${date}`);
  }, [viewType]);

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[550px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-primary" />
            Export Transactions
          </DialogTitle>
          <DialogDescription>
            Export {viewType === "expenses" ? "expenses" : "imported transactions"} to CSV format
          </DialogDescription>
        </DialogHeader>

        {exportComplete ? (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Export Successful!</h3>
            <p className="text-sm text-muted-foreground">
              Your file has been downloaded.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Filename */}
            <div className="space-y-2">
              <Label htmlFor="filename">File Name</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="filename"
                  value={filename}
                  onChange={(e) => setFilename(e.target.value)}
                  placeholder="Enter filename"
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground">.csv</span>
              </div>
            </div>

            {/* Row Count */}
            <div className="space-y-2">
              <Label>Number of Rows to Export</Label>
              <div className="flex flex-col gap-3">
                <Select value={rowCount} onValueChange={setRowCount}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select rows to export" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All ({data.length} rows)</SelectItem>
                    <SelectItem value="10">First 10 rows</SelectItem>
                    <SelectItem value="25">First 25 rows</SelectItem>
                    <SelectItem value="50">First 50 rows</SelectItem>
                    <SelectItem value="100">First 100 rows</SelectItem>
                    <SelectItem value="custom">Custom</SelectItem>
                  </SelectContent>
                </Select>
                
                {rowCount === "custom" && (
                  <Input
                    type="number"
                    min="1"
                    max={data.length}
                    value={customRowCount}
                    onChange={(e) => setCustomRowCount(e.target.value)}
                    placeholder={`Enter number (max ${data.length})`}
                  />
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                Will export {actualRowCount} of {data.length} total rows
              </p>
            </div>

            {/* Column Selection */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Columns to Export</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => toggleAllColumns(!allColumnsSelected)}
                  className="text-xs h-7"
                >
                  {allColumnsSelected ? "Deselect All" : "Select All"}
                </Button>
              </div>
              
              <div className="border rounded-lg p-4 max-h-[250px] overflow-y-auto">
                <div className="grid grid-cols-2 gap-3">
                  {/* Base columns */}
                  {columns.map((column) => (
                    <div key={column.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={column.id}
                        checked={column.selected}
                        onCheckedChange={() => toggleColumn(column.id)}
                      />
                      <label
                        htmlFor={column.id}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {column.label}
                      </label>
                    </div>
                  ))}
                  
                  {/* Custom field columns */}
                  {customFields.map((field) => {
                    const colId = `custom_${field.name}`;
                    const isSelected = allColumns.find((c) => c.id === colId)?.selected ?? true;
                    return (
                      <div key={colId} className="flex items-center space-x-2">
                        <Checkbox
                          id={colId}
                          checked={isSelected}
                          onCheckedChange={() => {
                            // Custom fields are always included but we can track separately if needed
                          }}
                          disabled
                        />
                        <label
                          htmlFor={colId}
                          className="text-sm font-medium leading-none text-muted-foreground cursor-not-allowed"
                        >
                          {field.label} (custom)
                        </label>
                      </div>
                    );
                  })}
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {selectedColumnsCount} of {allColumns.length} columns selected
              </p>
            </div>

            {/* Buttons */}
            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleExport}
                disabled={isExporting || selectedColumnsCount === 0 || actualRowCount === 0}
                className="flex-1 bg-primary hover:bg-primary/90"
              >
                {isExporting ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Exporting...
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Download className="h-4 w-4" />
                    Export CSV
                  </div>
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Plus,
  Trash2,
  Edit,
  Save,
  Loader2,
  Database,
  Lock,
  Unlock,
  Info,
  AlertCircle,
} from "lucide-react";
import { api, CustomFieldDefinition, FullSchemaResponse } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";

const FIELD_TYPES = [
  { value: "string", label: "Text" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
  { value: "boolean", label: "Yes/No" },
  { value: "select", label: "Dropdown" },
];

const getFieldTypeBadgeColor = (type: string) => {
  switch (type) {
    case "string":
      return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
    case "number":
      return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    case "date":
      return "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400";
    case "boolean":
      return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    case "select":
      return "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400";
    case "array":
      return "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400";
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400";
  }
};

interface CustomFieldFormData {
  name: string;
  label: string;
  type: string;
  required: boolean;
  description: string;
  options: string;
  order: number;
}

const emptyFieldForm: CustomFieldFormData = {
  name: "",
  label: "",
  type: "string",
  required: false,
  description: "",
  options: "",
  order: 0,
};

interface CustomFieldsProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CustomFields({ isOpen, onClose }: CustomFieldsProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingField, setEditingField] = useState<CustomFieldDefinition | null>(null);
  const [fieldForm, setFieldForm] = useState<CustomFieldFormData>(emptyFieldForm);
  const [deleteFieldName, setDeleteFieldName] = useState<string | null>(null);
  const [showResetDialog, setShowResetDialog] = useState(false);

  // Fetch schema data
  const { data: schema, isLoading, error } = useQuery({
    queryKey: ["documentSchema"],
    queryFn: api.getDocumentSchema,
    retry: false,
    enabled: isOpen,
  });

  // Save custom schema mutation
  const saveMutation = useMutation({
    mutationFn: api.saveCustomSchema,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documentSchema"] });
      toast({
        title: "Schema Saved",
        description: "Your custom fields have been saved successfully.",
      });
      setIsAddDialogOpen(false);
      setEditingField(null);
      setFieldForm(emptyFieldForm);
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save custom schema",
      });
    },
  });

  // Delete custom schema mutation
  const deleteMutation = useMutation({
    mutationFn: api.deleteCustomSchema,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documentSchema"] });
      toast({
        title: "Schema Reset",
        description: "Custom fields have been removed. Using default schema only.",
      });
      setShowResetDialog(false);
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to reset schema",
      });
    },
  });

  const handleOpenAddDialog = () => {
    setFieldForm({
      ...emptyFieldForm,
      order: (schema?.custom_fields?.length || 0) + 1,
    });
    setEditingField(null);
    setIsAddDialogOpen(true);
  };

  const handleEditField = (field: CustomFieldDefinition) => {
    setFieldForm({
      name: field.name,
      label: field.label,
      type: field.type,
      required: field.required,
      description: field.description || "",
      options: field.options?.join(", ") || "",
      order: field.order || 0,
    });
    setEditingField(field);
    setIsAddDialogOpen(true);
  };

  const handleSaveField = () => {
    // Validate form
    if (!fieldForm.name.trim() || !fieldForm.label.trim()) {
      toast({
        variant: "destructive",
        title: "Validation Error",
        description: "Field name and label are required.",
      });
      return;
    }

    // Validate name format (snake_case)
    const nameRegex = /^[a-z][a-z0-9_]*$/;
    if (!nameRegex.test(fieldForm.name)) {
      toast({
        variant: "destructive",
        title: "Validation Error",
        description: "Field name must be lowercase with underscores (e.g., my_field_name).",
      });
      return;
    }

    // Check for duplicate names
    const existingNames = [
      ...(schema?.default_fields?.map(f => f.name) || []),
      ...(schema?.custom_fields?.filter(f => f.name !== editingField?.name).map(f => f.name) || []),
    ];
    if (existingNames.includes(fieldForm.name)) {
      toast({
        variant: "destructive",
        title: "Validation Error",
        description: "A field with this name already exists.",
      });
      return;
    }

    // Build new field
    const newField: CustomFieldDefinition = {
      name: fieldForm.name.trim(),
      label: fieldForm.label.trim(),
      type: fieldForm.type,
      required: fieldForm.required,
      description: fieldForm.description.trim() || undefined,
      options: fieldForm.type === "select" && fieldForm.options.trim()
        ? fieldForm.options.split(",").map(o => o.trim()).filter(Boolean)
        : undefined,
      order: fieldForm.order,
    };

    // Update fields list
    let updatedFields: CustomFieldDefinition[];
    if (editingField) {
      updatedFields = (schema?.custom_fields || []).map(f =>
        f.name === editingField.name ? newField : f
      );
    } else {
      updatedFields = [...(schema?.custom_fields || []), newField];
    }

    // Save to backend
    saveMutation.mutate({
      fields: updatedFields,
      schema_name: schema?.schema_name || "Default Schema",
      description: schema?.description || undefined,
      is_active: true,
    });
  };

  const handleDeleteField = (fieldName: string) => {
    const updatedFields = (schema?.custom_fields || []).filter(f => f.name !== fieldName);
    
    if (updatedFields.length === 0) {
      // If no custom fields left, delete the entire custom schema
      deleteMutation.mutate();
    } else {
      saveMutation.mutate({
        fields: updatedFields,
        schema_name: schema?.schema_name || "Default Schema",
        description: schema?.description || undefined,
        is_active: true,
      });
    }
    setDeleteFieldName(null);
  };

  return (
    <>
      {/* Main Schema Modal */}
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="max-w-4xl max-h-[90vh] p-0">
          <DialogHeader className="p-6 pb-4 border-b bg-gradient-to-r from-primary/5 to-accent/5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-primary/15 shrink-0">
                  <Database className="h-6 w-6 text-primary/80" />
                </div>
                <div className="flex items-center gap-2">
                  <DialogTitle className="text-xl">Document Schema</DialogTitle>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="h-5 w-5 rounded-full flex items-center justify-center text-muted-foreground hover:text-foreground cursor-help transition-colors">
                          <Info className="h-4 w-4" />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="max-w-[280px]">
                        <p className="font-medium mb-1">How Custom Fields Work</p>
                        <p className="text-xs text-muted-foreground">
                          Custom fields extend the default document schema. When documents are processed, 
                          the AI will attempt to extract values for your custom fields in addition to the 
                          standard fields like amount, vendor, date, etc.
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {schema?.has_custom_schema && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowResetDialog(true)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Reset
                  </Button>
                )}
                <Button onClick={handleOpenAddDialog} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Field
                </Button>
              </div>
            </div>
          </DialogHeader>

          <ScrollArea className="max-h-[calc(90vh-120px)]">
            <div className="p-6 space-y-6">
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : error ? (
                <div className="flex items-center gap-2 text-destructive p-4 rounded-lg bg-destructive/10 border border-destructive/20">
                  <AlertCircle className="h-5 w-5" />
                  <span>Failed to load schema settings</span>
                </div>
              ) : (
                <>
                  {/* Default Fields Section */}
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                      <Lock className="h-4 w-4 text-muted-foreground" />
                      Default Fields (Read-only)
                    </h3>
                    <div className="border rounded-lg overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-muted/50">
                            <TableHead className="w-[180px]">Field Name</TableHead>
                            <TableHead className="w-[180px]">Label</TableHead>
                            <TableHead className="w-[100px]">Type</TableHead>
                            <TableHead className="w-[80px]">Required</TableHead>
                            <TableHead>Description</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {schema?.default_fields?.map((field) => (
                            <TableRow key={field.name} className="hover:bg-muted/30">
                              <TableCell className="font-mono text-sm">{field.name}</TableCell>
                              <TableCell>{field.label}</TableCell>
                              <TableCell>
                                <Badge className={getFieldTypeBadgeColor(field.type)} variant="secondary">
                                  {field.type}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                {field.required ? (
                                  <Badge variant="default" className="bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                                    Yes
                                  </Badge>
                                ) : (
                                  <Badge variant="outline">No</Badge>
                                )}
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {field.description || "—"}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>

                  {/* Custom Fields Section */}
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                      <Unlock className="h-4 w-4 text-primary" />
                      Custom Fields
                      {schema?.custom_fields && schema.custom_fields.length > 0 && (
                        <Badge variant="secondary" className="ml-2">
                          {schema.custom_fields.length} field{schema.custom_fields.length !== 1 ? "s" : ""}
                        </Badge>
                      )}
                    </h3>
                    
                    {!schema?.custom_fields || schema.custom_fields.length === 0 ? (
                      <div className="border rounded-lg p-8 text-center bg-muted/20">
                        <Database className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                        <p className="text-muted-foreground mb-4">
                          No custom fields defined yet. Add fields to extract additional information from your documents.
                        </p>
                        <Button onClick={handleOpenAddDialog} variant="outline">
                          <Plus className="h-4 w-4 mr-2" />
                          Add Your First Custom Field
                        </Button>
                      </div>
                    ) : (
                      <div className="border rounded-lg overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/50">
                              <TableHead className="w-[180px]">Field Name</TableHead>
                              <TableHead className="w-[180px]">Label</TableHead>
                              <TableHead className="w-[100px]">Type</TableHead>
                              <TableHead className="w-[80px]">Required</TableHead>
                              <TableHead>Description</TableHead>
                              <TableHead className="w-[100px] text-right">Actions</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {schema.custom_fields.map((field) => (
                              <TableRow key={field.name} className="hover:bg-muted/30">
                                <TableCell className="font-mono text-sm">{field.name}</TableCell>
                                <TableCell>{field.label}</TableCell>
                                <TableCell>
                                  <Badge className={getFieldTypeBadgeColor(field.type)} variant="secondary">
                                    {field.type}
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  {field.required ? (
                                    <Badge variant="default" className="bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                                      Yes
                                    </Badge>
                                  ) : (
                                    <Badge variant="outline">No</Badge>
                                  )}
                                </TableCell>
                                <TableCell className="text-sm text-muted-foreground">
                                  {field.description || "—"}
                                </TableCell>
                                <TableCell className="text-right">
                                  <div className="flex items-center justify-end gap-1">
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() => handleEditField(field)}
                                      className="h-8 w-8"
                                    >
                                      <Edit className="h-4 w-4" />
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() => setDeleteFieldName(field.name)}
                                      className="h-8 w-8 text-destructive hover:text-destructive"
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  </div>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* Add/Edit Field Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingField ? "Edit Custom Field" : "Add Custom Field"}
            </DialogTitle>
            <DialogDescription>
              Define a new field to extract from your documents.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Field Name *</Label>
              <Input
                id="name"
                placeholder="e.g., project_code"
                value={fieldForm.name}
                onChange={(e) => setFieldForm({ ...fieldForm, name: e.target.value.toLowerCase().replace(/\s/g, "_") })}
                disabled={!!editingField}
              />
              <p className="text-xs text-muted-foreground">
                Lowercase letters, numbers, and underscores only
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="label">Display Label *</Label>
              <Input
                id="label"
                placeholder="e.g., Project Code"
                value={fieldForm.label}
                onChange={(e) => setFieldForm({ ...fieldForm, label: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="type">Field Type</Label>
              <Select
                value={fieldForm.type}
                onValueChange={(value) => setFieldForm({ ...fieldForm, type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FIELD_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {fieldForm.type === "select" && (
              <div className="space-y-2">
                <Label htmlFor="options">Dropdown Options</Label>
                <Input
                  id="options"
                  placeholder="Option 1, Option 2, Option 3"
                  value={fieldForm.options}
                  onChange={(e) => setFieldForm({ ...fieldForm, options: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Separate options with commas
                </p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Help text for this field..."
                value={fieldForm.description}
                onChange={(e) => setFieldForm({ ...fieldForm, description: e.target.value })}
                rows={2}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="required" className="cursor-pointer">
                Required Field
              </Label>
              <Switch
                id="required"
                checked={fieldForm.required}
                onCheckedChange={(checked) => setFieldForm({ ...fieldForm, required: checked })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveField} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Field
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Field Confirmation */}
      <AlertDialog open={!!deleteFieldName} onOpenChange={(open) => !open && setDeleteFieldName(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Custom Field?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the field "{deleteFieldName}"? 
              This action cannot be undone and existing data for this field will not be affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteFieldName && handleDeleteField(deleteFieldName)}
              className="bg-destructive hover:bg-destructive/90"
            >
              Delete Field
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reset Schema Confirmation */}
      <AlertDialog open={showResetDialog} onOpenChange={setShowResetDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reset Custom Schema?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove all custom fields and reset to the default schema only.
              Existing extracted data will not be affected, but new documents will only
              extract default fields.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteMutation.mutate()}
              className="bg-destructive hover:bg-destructive/90"
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Resetting...
                </>
              ) : (
                "Reset Schema"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export default CustomFields;

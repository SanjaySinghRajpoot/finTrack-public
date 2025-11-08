import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { CheckCircle, Upload, FileText, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

const uploadSchema = z.object({
  file: z.any().refine((file) => file instanceof File, "Please select a file"),
  document_type: z.string().min(1, "Document type is required"),
  upload_notes: z.string().optional(),
});

type UploadFormValues = z.infer<typeof uploadSchema>;

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FileUploadModal({ isOpen, onClose }: FileUploadModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadComplete, setUploadComplete] = useState(false);
  const queryClient = useQueryClient();

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      document_type: "INVOICE",
      upload_notes: "",
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (data: { file: File; document_type: string; upload_notes?: string }) => {
      // Simulate progress for user feedback
      setUploadProgress(20);
      const result = await api.uploadFile(data.file, data.document_type, data.upload_notes);
      setUploadProgress(100);
      return result;
    },
    onSuccess: (data) => {
      setUploadComplete(true);
      queryClient.invalidateQueries({ queryKey: ["importedExpenses"] });
      toast.success("Invoice uploaded and processed successfully!");
      
      // Auto-close after 2 seconds
      setTimeout(() => {
        handleClose();
      }, 2000);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to upload file");
      setUploadProgress(0);
    },
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    
    if (file) {
      // Validate file type
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        toast.error("Only PDF files are supported");
        setSelectedFile(null);
        event.target.value = '';
        return;
      }
      
      // Validate file size (10MB limit)
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (file.size > maxSize) {
        toast.error("File size must be less than 10MB");
        setSelectedFile(null);
        event.target.value = '';
        return;
      }
      
      form.setValue("file", file);
    }
  };

  const handleSubmit = (values: UploadFormValues) => {
    if (!selectedFile) {
      toast.error("Please select a file");
      return;
    }

    setUploadProgress(10);
    uploadMutation.mutate({
      file: selectedFile,
      document_type: values.document_type,
      upload_notes: values.upload_notes || undefined,
    });
  };

  const handleClose = () => {
    if (uploadMutation.isPending) return; // Prevent closing during upload
    
    // Reset form and state
    form.reset();
    setSelectedFile(null);
    setUploadProgress(0);
    setUploadComplete(false);
    onClose();
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-xl flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Upload Invoice
          </DialogTitle>
        </DialogHeader>

        {uploadComplete ? (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Upload Successful!</h3>
            <p className="text-sm text-muted-foreground">
              Your invoice has been processed and will appear in the imported expenses.
            </p>
          </div>
        ) : (
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            {/* File Upload */}
            <div className="space-y-2">
              <Label htmlFor="file">PDF File</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="file"
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  disabled={uploadMutation.isPending}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={uploadMutation.isPending}
                  onClick={() => document.getElementById('file')?.click()}
                >
                  <Upload className="h-4 w-4" />
                </Button>
              </div>
              {selectedFile && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <FileText className="h-4 w-4" />
                  <span>{selectedFile.name}</span>
                  <span>({formatFileSize(selectedFile.size)})</span>
                </div>
              )}
              {form.formState.errors.file && (
                <p className="text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {form.formState.errors.file.message}
                </p>
              )}
            </div>

            {/* Document Type */}
            <div className="space-y-2">
              <Label htmlFor="document_type">Document Type</Label>
              <Select
                value={form.watch("document_type")}
                onValueChange={(value) => form.setValue("document_type", value)}
                disabled={uploadMutation.isPending}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select document type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="INVOICE">Invoice</SelectItem>
                  <SelectItem value="RECEIPT">Receipt</SelectItem>
                  <SelectItem value="BILL">Bill</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Upload Notes */}
            <div className="space-y-2">
              <Label htmlFor="upload_notes">Notes (Optional)</Label>
              <Textarea
                id="upload_notes"
                placeholder="Add any notes about this document..."
                className="resize-none"
                disabled={uploadMutation.isPending}
                {...form.register("upload_notes")}
              />
            </div>

            {/* Upload Progress */}
            {uploadMutation.isPending && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Uploading and processing...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="w-full" />
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={uploadMutation.isPending}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!selectedFile || uploadMutation.isPending}
                className="flex-1 bg-primary hover:bg-primary/90"
              >
                {uploadMutation.isPending ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Processing...
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Upload className="h-4 w-4" />
                    Upload & Process
                  </div>
                )}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
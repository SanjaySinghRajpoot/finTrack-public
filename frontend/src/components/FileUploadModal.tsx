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
import { generateFileHash, uploadToS3, validateFile, formatFileSize } from "@/lib/fileUtils";

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

interface UploadStage {
  stage: 'idle' | 'hashing' | 'presigned' | 'uploading' | 'metadata' | 'complete' | 'error';
  message: string;
}

export function FileUploadModal({ isOpen, onClose }: FileUploadModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState<UploadStage>({ stage: 'idle', message: '' });
  const [isDuplicate, setIsDuplicate] = useState(false);
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
      const { file, document_type, upload_notes } = data;

      console.log('🔵 [Upload] Starting file upload process');
      console.log('📄 File details:', { name: file.name, size: file.size, type: file.type });

      // Stage 1: Generate file hash
      setUploadStage({ stage: 'hashing', message: 'Generating file hash...' });
      setUploadProgress(10);
      console.log('🔐 [Stage 1] Generating file hash...');
      const fileHash = await generateFileHash(file);
      console.log('✅ File hash generated:', fileHash.substring(0, 16) + '...');

      // Stage 2: Request presigned URL
      setUploadStage({ stage: 'presigned', message: 'Requesting upload URL...' });
      setUploadProgress(20);
      console.log('🔑 [Stage 2] Requesting presigned URL from backend...');
      
      const presignedResponse = await api.getPresignedUrls({
        files: [{
          filename: file.name,
          content_type: file.type,
          file_hash: fileHash,
          file_size: file.size,
        }],
      });

      console.log('📨 Presigned URL response:', presignedResponse);
      const fileData = presignedResponse.data[0];
      console.log('📋 File data:', { 
        filename: fileData.filename, 
        remark: fileData.remark,
        hasPresignedUrl: !!fileData.presigned_url,
        s3_key: fileData.s3_key 
      });

      // Check if file is duplicate
      if (fileData.remark === 'duplicate') {
        console.warn('⚠️  Duplicate file detected');
        setIsDuplicate(true);
        throw new Error('This file has already been uploaded. Duplicates are not allowed.');
      }

      if (!fileData.presigned_url || !fileData.s3_key) {
        console.error('❌ Missing presigned URL or S3 key in response');
        throw new Error('Failed to get presigned URL from server');
      }

      console.log('✅ Presigned URL received successfully');

      // Stage 3: Upload to S3
      setUploadStage({ stage: 'uploading', message: 'Uploading to S3...' });
      console.log('☁️  [Stage 3] Uploading file to S3...');
      console.log('🔗 S3 Key:', fileData.s3_key);
      console.log('📝 Content-Type for upload:', file.type);
      
      try {
        await uploadToS3(
          fileData.presigned_url,
          file,
          file.type,
          (progress) => {
            // Map S3 upload progress to 20-80%
            setUploadProgress(20 + (progress * 0.6));
          }
        );
        console.log('✅ S3 upload completed successfully');
      } catch (s3Error) {
        console.error('❌ S3 upload failed:', s3Error);
        throw s3Error;
      }

      // Stage 4: Submit metadata to backend
      setUploadStage({ stage: 'metadata', message: 'Processing file...' });
      setUploadProgress(85);
      console.log('📊 [Stage 4] Submitting file metadata to backend...');
      
      const metadataResponse = await api.submitFileMetadata({
        files: [{
          filename: file.name,
          file_hash: fileHash,
          s3_key: fileData.s3_key,
          file_size: file.size,
          content_type: file.type,
          document_type: document_type,
          upload_notes: upload_notes,
        }],
      });

      console.log('✅ Metadata submitted successfully:', metadataResponse);
      setUploadProgress(100);
      return metadataResponse;
    },
    onSuccess: (data) => {
      console.log('🎉 Upload process completed successfully!');
      setUploadStage({ stage: 'complete', message: 'Upload complete!' });
      queryClient.invalidateQueries({ queryKey: ["importedExpenses"] });
      
      const fileStatus = data.data[0]?.status;
      console.log('📌 File status:', fileStatus);
      
      if (fileStatus === 'queued_for_processing') {
        toast.success("File uploaded successfully! Processing will begin shortly.");
      } else if (fileStatus === 'existing') {
        toast.info("File already exists in the system.");
      } else {
        toast.success("File uploaded and queued for processing!");
      }
      
      // Auto-close after 2 seconds
      setTimeout(() => {
        handleClose();
      }, 2000);
    },
    onError: (error: Error) => {
      console.error('❌ Upload error:', error);
      console.error('Error stack:', error.stack);
      setUploadStage({ stage: 'error', message: error.message });
      
      if (isDuplicate) {
        toast.error(error.message);
      } else {
        toast.error(error.message || "Failed to upload file");
      }
      
      setUploadProgress(0);
      setIsDuplicate(false);
    },
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    setIsDuplicate(false);
    
    if (file) {
      const validation = validateFile(file);
      
      if (!validation.valid) {
        toast.error(validation.error);
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

    setUploadProgress(5);
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
    setUploadStage({ stage: 'idle', message: '' });
    setIsDuplicate(false);
    onClose();
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

        {uploadStage.stage === 'complete' ? (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Upload Successful!</h3>
            <p className="text-sm text-muted-foreground">
              Your file has been uploaded and queued for processing.
            </p>
          </div>
        ) : (
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            {/* File Upload */}
            <div className="space-y-2">
              <Label htmlFor="file">PDF or Image File</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="file"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.webp"
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
                  <span>{uploadStage.message}</span>
                  <span>{Math.round(uploadProgress)}%</span>
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
                    {uploadStage.message.split('...')[0]}...
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
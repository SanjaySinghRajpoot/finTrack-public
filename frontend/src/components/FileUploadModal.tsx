import { useState, useRef } from "react";
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
import { CheckCircle, Upload, FileText, AlertCircle, FolderOpen, File, Info } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  generateFileHash,
  uploadToS3,
  validateFile,
} from "@/lib/fileUtils";
import { Alert, AlertDescription } from "@/components/ui/alert";

/* ---------------------------- Schema ---------------------------- */

// Use a file-like check that doesn't rely on File constructor being available
const isFileLike = (val: unknown): val is File => {
  return (
    val !== null &&
    typeof val === "object" &&
    "name" in val &&
    "size" in val &&
    "type" in val
  );
};

const uploadSchema = z.object({
  files: z.array(z.custom<File>(isFileLike, "Invalid file")).min(1, "Please select at least one file"),
  document_type: z.string().min(1, "Document type is required"),
  upload_notes: z.string().optional(),
});

type UploadFormValues = z.infer<typeof uploadSchema>;

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface UploadStage {
  stage:
    | "idle"
    | "hashing"
    | "presigned"
    | "uploading"
    | "metadata"
    | "complete"
    | "error";
  message: string;
}

/* ---------------------------- Component ---------------------------- */

export function FileUploadModal({ isOpen, onClose }: FileUploadModalProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState<UploadStage>({
    stage: "idle",
    message: "",
  });
  const [uploadMode, setUploadMode] = useState<"files" | "folder">("files");
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const queryClient = useQueryClient();

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      document_type: "INVOICE",
      upload_notes: "",
    },
  });

  /* ---------------------------- Upload Mutation ---------------------------- */

  const uploadMutation = useMutation({
    mutationFn: async (values: UploadFormValues) => {
      const { files, document_type, upload_notes } = values;

      /* ---------- Stage 1: Hashing ---------- */
      setUploadStage({ stage: "hashing", message: "Hashing files..." });
      setUploadProgress(5);

      const filesPayload = await Promise.all(
        files.map(async (file) => ({
          file,
          filename: file.name,
          content_type: file.type,
          file_size: file.size,
          file_hash: await generateFileHash(file),
          relative_path: file.webkitRelativePath || file.name,
        }))
      );

      /* ---------- Stage 2: Presigned URLs ---------- */
      setUploadStage({
        stage: "presigned",
        message: "Checking duplicates...",
      });
      setUploadProgress(15);

      const presignedResponse = await api.getPresignedUrls({
        files: filesPayload.map((f) => ({
          filename: f.filename,
          content_type: f.content_type,
          file_size: f.file_size,
          file_hash: f.file_hash,
          relative_path: f.relative_path,
        })),
      });

      /* ---------- Split uploadable vs duplicate ---------- */
      const uploadable = presignedResponse.data
        .map((res, index) => ({
          presigned: res,
          original: filesPayload[index],
        }))
        .filter(({ presigned }) => presigned.remark === "success");

      const duplicates = presignedResponse.data.filter(
        (res) => res.remark === "duplicate"
      );

      if (duplicates.length > 0) {
        toast.warning(`${duplicates.length} duplicate file(s) skipped`);
      }

      if (uploadable.length === 0) {
        throw new Error("All selected files are duplicates.");
      }

      /* ---------- Stage 3: Upload to S3 ---------- */
      setUploadStage({ stage: "uploading", message: "Uploading files..." });

      const totalFiles = uploadable.length;
      let completedFiles = 0;

      await Promise.all(
        uploadable.map(async ({ presigned, original }) => {
          await uploadToS3(
            presigned.presigned_url!,
            original.file,
            original.content_type,
            (progress) => {
              const base = 20;
              const perFile = 60 / totalFiles;
              setUploadProgress(
                base + completedFiles * perFile + progress * perFile
              );
            }
          );

          completedFiles += 1;
        })
      );

      /* ---------- Stage 4: Metadata ---------- */
      setUploadStage({ stage: "metadata", message: "Processing files..." });
      setUploadProgress(90);

      const metadataResponse = await api.submitFileMetadata({
        files: uploadable.map(({ presigned, original }) => ({
          filename: original.filename,
          file_hash: original.file_hash,
          s3_key: presigned.s3_key!,
          file_size: original.file_size,
          content_type: original.content_type,
          document_type,
          upload_notes,
          relative_path: original.relative_path,
        })),
      });

      setUploadProgress(100);
      return metadataResponse;
    },

    onSuccess: () => {
      setUploadStage({ stage: "complete", message: "Upload complete!" });
      queryClient.invalidateQueries({ queryKey: ["importedExpenses"] });

      toast.success("Files uploaded successfully and queued for processing.");

      setTimeout(handleClose, 2000);
    },

    onError: (error: Error) => {
      setUploadStage({ stage: "error", message: error.message });
      setUploadProgress(0);
      toast.error(error.message || "Upload failed");
    },
  });

  /* ---------------------------- Handlers ---------------------------- */

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    for (const file of files) {
      const validation = validateFile(file);
      if (!validation.valid) {
        toast.error(`${file.name}: ${validation.error}`);
        return;
      }
    }

    setSelectedFiles(files);
    form.setValue("files", files);
  };

  const handleClose = () => {
    if (uploadMutation.isPending) return;
    form.reset();
    setSelectedFiles([]);
    setUploadProgress(0);
    setUploadStage({ stage: "idle", message: "" });
    setUploadMode("files");
    onClose();
  };

  /* ---------------------------- UI ---------------------------- */

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-xl flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            Upload Documents
          </DialogTitle>
        </DialogHeader>

        {uploadStage.stage === "complete" ? (
          <div className="text-center py-8">
            <CheckCircle className="h-10 w-10 text-green-600 mx-auto mb-4" />
            <p className="font-medium">Upload successful!</p>
          </div>
        ) : (
          <form
            onSubmit={form.handleSubmit((v) => uploadMutation.mutate(v))}
            className="space-y-4"
          >
            {/* Info Alert */}
            <Alert className="bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900">
              <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <AlertDescription className="text-sm text-blue-800 dark:text-blue-300">
                Once processed, files appear in the <strong>Files</strong> page for tracking. Extracted data shows in the <strong>Imported</strong> section of All Transactions where you can verify and import to your expenses.
              </AlertDescription>
            </Alert>

            {/* Upload Mode Toggle */}
            <div className="space-y-3">
              <Label>Upload Type</Label>
              <div className="flex items-center gap-2 bg-muted p-1 rounded-lg">
                <Button
                  type="button"
                  variant={uploadMode === "files" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => {
                    setUploadMode("files");
                    setSelectedFiles([]);
                    form.setValue("files", []);
                  }}
                  disabled={uploadMutation.isPending}
                  className="flex-1 h-9"
                >
                  <File className="h-4 w-4 mr-2" />
                  Files
                </Button>
                <Button
                  type="button"
                  variant={uploadMode === "folder" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => {
                    setUploadMode("folder");
                    setSelectedFiles([]);
                    form.setValue("files", []);
                  }}
                  disabled={uploadMutation.isPending}
                  className="flex-1 h-9"
                >
                  <FolderOpen className="h-4 w-4 mr-2" />
                  Folder
                </Button>
              </div>
            </div>

            {/* File Picker */}
            <div className="space-y-2">
              <Label>{uploadMode === "files" ? "Select Files" : "Select Folder"}</Label>
              
              {/* File Input (for individual files) */}
              {uploadMode === "files" && (
                <Input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.jpg,.jpeg,.png,.webp"
                  onChange={handleFileChange}
                  disabled={uploadMutation.isPending}
                />
              )}
              
              {/* Folder Input */}
              {uploadMode === "folder" && (
                <Input
                  ref={folderInputRef}
                  type="file"
                  multiple
                  // @ts-ignore - webkitdirectory is not in the types but works in browsers
                  webkitdirectory=""
                  directory=""
                  accept=".pdf,.jpg,.jpeg,.png,.webp"
                  onChange={handleFileChange}
                  disabled={uploadMutation.isPending}
                />
              )}

              {selectedFiles.length > 0 && (
                <p className="text-sm text-muted-foreground">
                  {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
                </p>
              )}

              {form.formState.errors.files && (
                <p className="text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {form.formState.errors.files.message}
                </p>
              )}
            </div>

            {/* Document Type */}
            <div className="space-y-2">
              <Label>Document Type</Label>
              <Select
                value={form.watch("document_type")}
                onValueChange={(v) => form.setValue("document_type", v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="INVOICE">Invoice</SelectItem>
                  <SelectItem value="RECEIPT">Receipt</SelectItem>
                  <SelectItem value="BILL">Bill</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Notes */}
            <Textarea
              placeholder="Notes (optional)"
              {...form.register("upload_notes")}
            />

            {/* Progress */}
            {uploadMutation.isPending && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>{uploadStage.message}</span>
                  <span>{Math.round(uploadProgress)}%</span>
                </div>
                <Progress value={uploadProgress} />
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
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
                disabled={!selectedFiles.length || uploadMutation.isPending}
                className="flex-1"
              >
                <Upload className="h-4 w-4 mr-2" />
                Upload & Process
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

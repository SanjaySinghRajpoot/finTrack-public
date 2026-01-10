import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { 
  FileText, 
  Clock, 
  AlertCircle, 
  CheckCircle2, 
  Loader2,
  Calendar,
  Hash,
  HardDrive,
  Tag,
  User,
  FileType,
  Eye,
  X,
  AlertTriangle,
} from "lucide-react";
import { format } from "date-fns";
import { StagingDocument } from "@/lib/api";

interface DocumentDetailsModalProps {
  document: StagingDocument | null;
  isOpen: boolean;
  onClose: () => void;
  onViewFile?: () => void;
}

const getStatusConfig = (status: string) => {
  switch (status.toLowerCase()) {
    case 'pending':
      return {
        icon: Clock,
        label: 'Pending',
        className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
        borderColor: 'border-yellow-200 dark:border-yellow-800',
      };
    case 'in_progress':
      return {
        icon: Loader2,
        label: 'Processing',
        className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
        borderColor: 'border-blue-200 dark:border-blue-800',
      };
    case 'completed':
      return {
        icon: CheckCircle2,
        label: 'Completed',
        className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
        borderColor: 'border-green-200 dark:border-green-800',
      };
    case 'failed':
      return {
        icon: AlertCircle,
        label: 'Failed',
        className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
        borderColor: 'border-red-200 dark:border-red-800',
      };
    default:
      return {
        icon: Clock,
        label: status,
        className: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
        borderColor: 'border-gray-200 dark:border-gray-800',
      };
  }
};

const formatFileSize = (bytes: number | null): string => {
  if (!bytes) return 'N/A';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

const InfoRow = ({ icon: Icon, label, value, className = "" }: { 
  icon: React.ElementType; 
  label: string; 
  value: string | React.ReactNode;
  className?: string;
}) => (
  <div className={`flex items-start gap-3 ${className}`}>
    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-muted shrink-0">
      <Icon className="h-4 w-4 text-muted-foreground" />
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
      <p className="text-sm font-medium text-foreground break-words">{value}</p>
    </div>
  </div>
);

export function DocumentDetailsModal({ 
  document, 
  isOpen, 
  onClose,
  onViewFile 
}: DocumentDetailsModalProps) {
  if (!document) return null;

  const statusConfig = getStatusConfig(document.processing_status);
  const StatusIcon = statusConfig.icon;
  const canViewFile = !!document.s3_key;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Document Details
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* File Name & Status Header */}
          <div className={`p-4 rounded-lg border-2 ${statusConfig.borderColor} ${statusConfig.className} bg-opacity-50`}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold mb-1 break-words">{document.filename}</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline" className={statusConfig.className}>
                    <StatusIcon className="h-3 w-3 mr-1" />
                    {statusConfig.label}
                  </Badge>
                  {document.document_type && (
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400">
                      <Tag className="h-3 w-3 mr-1" />
                      {document.document_type}
                    </Badge>
                  )}
                  <Badge variant="outline" className="capitalize">
                    {document.source_type}
                  </Badge>
                </div>
              </div>
              {canViewFile && onViewFile && (
                <Button 
                  size="sm" 
                  onClick={onViewFile}
                  className="shrink-0"
                >
                  <Eye className="h-4 w-4 mr-2" />
                  View File
                </Button>
              )}
            </div>
          </div>

          {/* Error Message (if failed) */}
          {document.processing_status === 'failed' && document.error_message && (
            <div className="p-4 rounded-lg border-2 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-red-900 dark:text-red-100 mb-1">
                    Processing Failed
                  </p>
                  <p className="text-sm text-red-700 dark:text-red-300 break-words">
                    {document.error_message}
                  </p>
                  {document.meta_data?.error_type && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                      Error Type: {document.meta_data.error_type}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Basic Information */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Basic Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoRow 
                icon={Hash} 
                label="Document ID" 
                value={`#${document.id}`}
              />
              <InfoRow 
                icon={HardDrive} 
                label="File Size" 
                value={formatFileSize(document.file_size)}
              />
              <InfoRow 
                icon={FileType} 
                label="MIME Type" 
                value={document.mime_type || 'N/A'}
              />
              <InfoRow 
                icon={Tag} 
                label="File Hash" 
                value={
                  document.file_hash ? (
                    <span className="font-mono text-xs">{document.file_hash.substring(0, 16)}...</span>
                  ) : 'N/A'
                }
              />
            </div>
          </div>

          <Separator />

          {/* Processing Information */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Processing Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoRow 
                icon={Loader2} 
                label="Processing Attempts" 
                value={`${document.processing_attempts} / ${document.max_attempts}`}
              />
              <InfoRow 
                icon={Tag} 
                label="Priority" 
                value={document.priority}
              />
              {document.meta_data?.processing_method && (
                <InfoRow 
                  icon={FileText} 
                  label="Processing Method" 
                  value={document.meta_data.processing_method}
                />
              )}
              {document.meta_data?.batch_size && (
                <InfoRow 
                  icon={Hash} 
                  label="Batch Size" 
                  value={document.meta_data.batch_size}
                />
              )}
            </div>
          </div>

          <Separator />

          {/* Timestamps */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Timeline</h3>
            <div className="space-y-3">
              {document.created_at && (
                <InfoRow 
                  icon={Calendar} 
                  label="Queued At" 
                  value={format(new Date(document.created_at), "PPpp")}
                />
              )}
              {document.processing_started_at && (
                <InfoRow 
                  icon={Clock} 
                  label="Processing Started" 
                  value={format(new Date(document.processing_started_at), "PPpp")}
                />
              )}
              {document.processing_completed_at && (
                <InfoRow 
                  icon={CheckCircle2} 
                  label="Processing Completed" 
                  value={format(new Date(document.processing_completed_at), "PPpp")}
                />
              )}
              {document.updated_at && (
                <InfoRow 
                  icon={Clock} 
                  label="Last Updated" 
                  value={format(new Date(document.updated_at), "PPpp")}
                />
              )}
            </div>
          </div>

          {/* Upload Notes */}
          {document.upload_notes && (
            <>
              <Separator />
              <div>
                <h3 className="text-sm font-semibold mb-3">Upload Notes</h3>
                <div className="p-3 rounded-lg bg-muted">
                  <p className="text-sm text-foreground break-words">{document.upload_notes}</p>
                </div>
              </div>
            </>
          )}

          {/* Source Information */}
          {document.source && (
            <>
              <Separator />
              <div>
                <h3 className="text-sm font-semibold mb-3">Source Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <InfoRow 
                    icon={Hash} 
                    label="Source ID" 
                    value={document.source.id}
                  />
                  <InfoRow 
                    icon={Tag} 
                    label="Source Type" 
                    value={document.source.type}
                  />
                  {document.source.external_id && (
                    <InfoRow 
                      icon={FileText} 
                      label="External ID" 
                      value={document.source.external_id}
                    />
                  )}
                  {document.source.created_at && (
                    <InfoRow 
                      icon={Calendar} 
                      label="Source Created" 
                      value={format(new Date(document.source.created_at), "PPpp")}
                    />
                  )}
                </div>
              </div>
            </>
          )}

          {/* Metadata (if exists) */}
          {document.meta_data && Object.keys(document.meta_data).length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="text-sm font-semibold mb-3">Additional Metadata</h3>
                <div className="p-3 rounded-lg bg-muted">
                  <pre className="text-xs text-foreground whitespace-pre-wrap break-words">
                    {JSON.stringify(document.meta_data, null, 2)}
                  </pre>
                </div>
              </div>
            </>
          )}
        </div>

      </DialogContent>
    </Dialog>
  );
}

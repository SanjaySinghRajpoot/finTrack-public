import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TableSkeleton } from "@/components/ui/table-skeleton";
import { AttachmentViewerModal } from "@/components/AttachmentViewerModal";
import { 
  FileText, 
  Clock, 
  AlertCircle, 
  CheckCircle2, 
  Loader2, 
  ChevronLeft, 
  ChevronRight, 
  RefreshCw,
  Filter,
  FolderOpen,
  Eye,
} from "lucide-react";
import { api, StagingDocument } from "@/lib/api";
import { format, formatDistanceToNow } from "date-fns";

const STAGING_ITEMS_PER_PAGE = 10;

// Helper function to get status badge config
const getStatusConfig = (status: string) => {
  switch (status.toLowerCase()) {
    case 'pending':
      return {
        icon: Clock,
        label: 'Pending',
        className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
        animate: false,
      };
    case 'in_progress':
      return {
        icon: Loader2,
        label: 'Processing',
        className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
        animate: true,
      };
    case 'completed':
      return {
        icon: CheckCircle2,
        label: 'Completed',
        className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
        animate: false,
      };
    case 'failed':
      return {
        icon: AlertCircle,
        label: 'Failed',
        className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
        animate: false,
      };
    default:
      return {
        icon: Clock,
        label: status,
        className: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
        animate: false,
      };
  }
};

// Helper function to format file size
const formatFileSize = (bytes: number | null): string => {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const Files = () => {
  const [stagingPage, setStagingPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedAttachment, setSelectedAttachment] = useState<{
    s3Url: string;
    filename: string;
    mimeType: string;
  } | null>(null);

  // Fetch staging documents
  const { data: stagingData, isLoading: isStagingLoading, refetch: refetchStaging } = useQuery({
    queryKey: ["stagingDocuments", stagingPage, statusFilter],
    queryFn: () => api.getStagingDocuments(
      STAGING_ITEMS_PER_PAGE, 
      stagingPage * STAGING_ITEMS_PER_PAGE,
      statusFilter !== "all" ? statusFilter : undefined
    ),
    retry: false,
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  });

  const stagingDocuments = stagingData?.data || [];
  const stagingPagination = stagingData?.pagination;
  const hasPendingDocuments = stagingDocuments.some(
    doc => doc.processing_status === 'pending' || doc.processing_status === 'in_progress'
  );

  // Reset page when filter changes
  const handleFilterChange = (value: string) => {
    setStatusFilter(value);
    setStagingPage(0);
  };

  // Handle viewing a file
  const handleViewFile = (doc: StagingDocument) => {
    if (!doc.s3_key) return;
    
    setSelectedAttachment({
      s3Url: doc.s3_key,
      filename: doc.filename,
      mimeType: doc.mime_type || "application/octet-stream",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-primary flex items-center gap-2">
            Files
          </h1>
          <p className="text-sm md:text-base text-muted-foreground mt-1">
            View and track all your uploaded documents being processed
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchStaging()}
            className="h-9"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Staging Documents Card */}
      <Card className="shadow-soft border">
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
                <Clock className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
                  Document Processing Queue
                  {hasPendingDocuments && (
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-500"></span>
                    </span>
                  )}
                </CardTitle>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {stagingPagination?.total || 0} document{(stagingPagination?.total || 0) !== 1 ? 's' : ''} total
                </p>
              </div>
            </div>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={handleFilterChange}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="in_progress">Processing</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isStagingLoading ? (
            <div className="p-6">
              <TableSkeleton rows={5} />
            </div>
          ) : stagingDocuments.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
                <FolderOpen className="h-8 w-8 text-muted-foreground" />
              </div>
              <p className="text-lg font-medium text-foreground">
                {statusFilter !== "all" ? "No documents found" : "No documents in queue"}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {statusFilter !== "all" 
                  ? "Try changing the status filter" 
                  : "Upload documents to see them here"}
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="w-[50px] font-semibold text-foreground">#</TableHead>
                      <TableHead className="w-[280px] font-semibold text-foreground">Filename</TableHead>
                      <TableHead className="w-[100px] font-semibold text-foreground">Type</TableHead>
                      <TableHead className="w-[100px] font-semibold text-foreground">Source</TableHead>
                      <TableHead className="w-[80px] font-semibold text-foreground">Size</TableHead>
                      <TableHead className="w-[130px] font-semibold text-foreground">Status</TableHead>
                      <TableHead className="w-[100px] font-semibold text-foreground">Attempts</TableHead>
                      <TableHead className="w-[150px] font-semibold text-foreground">Queued</TableHead>
                      <TableHead className="w-[80px] font-semibold text-foreground text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {stagingDocuments.map((doc, index) => {
                      const statusConfig = getStatusConfig(doc.processing_status);
                      const StatusIcon = statusConfig.icon;
                      const serialNumber = index + 1 + stagingPage * STAGING_ITEMS_PER_PAGE;
                      const canView = !!doc.s3_key;

                      return (
                        <TableRow 
                          key={doc.id}
                          className="hover:bg-muted/30 transition-colors"
                        >
                          <TableCell className="text-muted-foreground font-medium">
                            {serialNumber}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <FileText className="h-4 w-4 text-primary shrink-0" />
                              <div className="min-w-0">
                                <p className="font-medium text-sm text-foreground truncate" title={doc.filename}>
                                  {doc.filename.length > 40 ? doc.filename.substring(0, 40) + '...' : doc.filename}
                                </p>
                                {doc.upload_notes && (
                                  <p className="text-xs text-muted-foreground truncate" title={doc.upload_notes}>
                                    {doc.upload_notes.length > 50 ? doc.upload_notes.substring(0, 50) + '...' : doc.upload_notes}
                                  </p>
                                )}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            {doc.document_type ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                                {doc.document_type}
                              </span>
                            ) : (
                              <span className="text-sm text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 capitalize">
                              {doc.source_type}
                            </span>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {formatFileSize(doc.file_size)}
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-col gap-1">
                              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium w-fit ${statusConfig.className}`}>
                                <StatusIcon className={`h-3 w-3 ${statusConfig.animate ? 'animate-spin' : ''}`} />
                                {statusConfig.label}
                              </span>
                              {doc.error_message && doc.processing_status === 'failed' && (
                                <p className="text-xs text-red-500 truncate max-w-[120px]" title={doc.error_message}>
                                  {doc.error_message}
                                </p>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <span className="text-sm text-muted-foreground">
                              {doc.processing_attempts} / {doc.max_attempts}
                            </span>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {doc.created_at ? (
                              <span title={format(new Date(doc.created_at), "MMM dd, yyyy HH:mm")}>
                                {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
                              </span>
                            ) : (
                              '—'
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            {canView ? (
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleViewFile(doc)}
                                className="h-8 w-8 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 transition-colors"
                                title="View file"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                            ) : (
                              <span className="text-sm text-muted-foreground">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {stagingPagination && stagingPagination.total > STAGING_ITEMS_PER_PAGE && (
                <div className="flex items-center justify-between px-6 py-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Showing {stagingPage * STAGING_ITEMS_PER_PAGE + 1} to{" "}
                    {Math.min((stagingPage + 1) * STAGING_ITEMS_PER_PAGE, stagingPagination.total)} of{" "}
                    {stagingPagination.total} documents
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setStagingPage((p) => Math.max(0, p - 1))}
                      disabled={stagingPage === 0}
                      className="h-8"
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <span className="text-sm text-muted-foreground px-2">
                      Page {stagingPage + 1} of {Math.ceil(stagingPagination.total / STAGING_ITEMS_PER_PAGE)}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setStagingPage((p) => p + 1)}
                      disabled={!stagingPagination.has_more}
                      className="h-8"
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

      {/* Attachment Viewer Modal */}
      <AttachmentViewerModal
        isOpen={!!selectedAttachment}
        onClose={() => setSelectedAttachment(null)}
        s3Url={selectedAttachment?.s3Url || null}
        filename={selectedAttachment?.filename}
        mimeType={selectedAttachment?.mimeType}
      />
    </div>
  );
};

export default Files;

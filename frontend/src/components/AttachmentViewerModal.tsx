import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Download, ExternalLink, FileText, Image as ImageIcon, FileIcon, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface AttachmentViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  s3Url: string | null;
  filename?: string;
  mimeType?: string;
}

export function AttachmentViewerModal({
  isOpen,
  onClose,
  s3Url,
  filename = "document",
  mimeType = "application/octet-stream",
}: AttachmentViewerModalProps) {
  const [signedUrl, setSignedUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && s3Url) {
      fetchSignedUrl();
    } else {
      // Reset state when modal closes
      setSignedUrl(null);
      setError(null);
    }
  }, [isOpen, s3Url]);

  const fetchSignedUrl = async () => {
    if (!s3Url) return;

    setLoading(true);
    setError(null);
    try {
      const response = await api.getAttachmentSignedUrl(s3Url);
      setSignedUrl(response.url);
    } catch (err) {
      console.error("Failed to fetch attachment:", err);
      setError("Failed to load attachment. Please try again.");
      toast.error("Failed to load attachment");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!signedUrl) return;
    
    const link = document.createElement("a");
    link.href = signedUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("Download started");
  };

  const handleOpenInNewTab = () => {
    if (!signedUrl) return;
    window.open(signedUrl, "_blank");
  };

  const isImage = mimeType.startsWith("image/");
  const isPdf = mimeType === "application/pdf" || filename.toLowerCase().endsWith(".pdf");
  const isText = mimeType.startsWith("text/");

  const renderPreview = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
          <p className="text-sm text-muted-foreground">Loading attachment...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center py-20">
          <FileIcon className="h-12 w-12 text-destructive mb-4" />
          <p className="text-sm text-destructive mb-4">{error}</p>
          <Button onClick={fetchSignedUrl} variant="outline" size="sm">
            Try Again
          </Button>
        </div>
      );
    }

    if (!signedUrl) {
      return null;
    }

    // Image preview
    if (isImage) {
      return (
        <div className="flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden">
          <img
            src={signedUrl}
            alt={filename}
            className="max-w-full max-h-[70vh] object-contain"
            onError={() => setError("Failed to load image")}
          />
        </div>
      );
    }

    // PDF preview
    if (isPdf) {
      return (
        <div className="w-full h-[70vh] bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden">
          <iframe
            src={signedUrl}
            className="w-full h-full border-0"
            title={filename}
            onError={() => setError("Failed to load PDF")}
          />
        </div>
      );
    }

    // Text preview
    if (isText) {
      return (
        <div className="w-full max-h-[70vh] overflow-auto bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
          <iframe
            src={signedUrl}
            className="w-full min-h-[60vh] border-0"
            title={filename}
            onError={() => setError("Failed to load text file")}
          />
        </div>
      );
    }

    // Fallback for other file types
    return (
      <div className="flex flex-col items-center justify-center py-20 bg-gray-50 dark:bg-gray-900 rounded-lg">
        <FileText className="h-16 w-16 text-muted-foreground mb-4" />
        <p className="text-sm text-muted-foreground mb-2">
          Preview not available for this file type
        </p>
        <p className="text-xs text-muted-foreground mb-6">
          {mimeType}
        </p>
        <div className="flex gap-2">
          <Button onClick={handleDownload} variant="default" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
          <Button onClick={handleOpenInNewTab} variant="outline" size="sm">
            <ExternalLink className="h-4 w-4 mr-2" />
            Open in New Tab
          </Button>
        </div>
      </div>
    );
  };

  const getFileIcon = () => {
    if (isImage) return <ImageIcon className="h-5 w-5" />;
    if (isPdf) return <FileText className="h-5 w-5" />;
    return <FileIcon className="h-5 w-5" />;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[95vh] overflow-y-auto p-0">
        <DialogHeader className="px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                {getFileIcon()}
              </div>
              <div>
                <DialogTitle className="text-lg">{filename}</DialogTitle>
                <p className="text-xs text-muted-foreground mt-1">{mimeType}</p>
              </div>
            </div>
            <div className="flex gap-2">
              {signedUrl && (isImage || isPdf || isText) && (
                <>
                  <Button
                    onClick={handleDownload}
                    variant="outline"
                    size="sm"
                    className="h-9"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                  <Button
                    onClick={handleOpenInNewTab}
                    variant="outline"
                    size="sm"
                    className="h-9"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Open
                  </Button>
                </>
              )}
            </div>
          </div>
        </DialogHeader>

        <div className="px-6 py-4">
          {renderPreview()}
        </div>
      </DialogContent>
    </Dialog>
  );
}

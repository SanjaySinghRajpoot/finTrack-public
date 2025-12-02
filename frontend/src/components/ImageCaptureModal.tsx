import { useState, useRef, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
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
import { CheckCircle, Camera, RotateCcw, Upload, AlertCircle, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

const captureSchema = z.object({
  document_type: z.string().min(1, "Document type is required"),
  upload_notes: z.string().optional(),
});

type CaptureFormValues = z.infer<typeof captureSchema>;

interface ImageCaptureModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ImageCaptureModal({ isOpen, onClose }: ImageCaptureModalProps) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadComplete, setUploadComplete] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isVideoReady, setIsVideoReady] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const queryClient = useQueryClient();

  const form = useForm<CaptureFormValues>({
    resolver: zodResolver(captureSchema),
    defaultValues: {
      document_type: "INVOICE",
      upload_notes: "",
    },
  });

  // Start camera
  const startCamera = async () => {
    try {
      setCameraError(null);
      setIsVideoReady(false);
      
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment", // Use back camera on mobile
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });
      
      console.log("Media stream obtained", mediaStream);
      setStream(mediaStream);
      setIsCameraActive(true);
    } catch (error) {
      console.error("Camera access error:", error);
      setCameraError("Unable to access camera. Please check permissions.");
      toast.error("Failed to access camera");
      setIsCameraActive(false);
    }
  };

  // Stop camera
  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
      setIsCameraActive(false);
      setIsVideoReady(false);
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  // Capture image from video
  const captureImage = () => {
    if (!videoRef.current || !canvasRef.current) {
      console.error("Video or canvas ref not available");
      toast.error("Camera not ready. Please try again.");
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    // Check if video is ready
    if (!isVideoReady || video.readyState !== video.HAVE_ENOUGH_DATA) {
      console.error("Video not ready", { isVideoReady, readyState: video.readyState });
      toast.error("Camera not ready. Please wait a moment and try again.");
      return;
    }
    
    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    if (canvas.width === 0 || canvas.height === 0) {
      console.error("Invalid video dimensions", { width: canvas.width, height: canvas.height });
      toast.error("Camera not ready. Please try again.");
      return;
    }
    
    const context = canvas.getContext("2d");
    if (!context) {
      console.error("Could not get canvas context");
      return;
    }

    // Draw the video frame to canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert canvas to blob and data URL
    canvas.toBlob((blob) => {
      if (!blob) {
        console.error("Failed to create blob");
        toast.error("Failed to capture image. Please try again.");
        return;
      }
      
      // Create image URL from canvas
      const imageUrl = canvas.toDataURL("image/jpeg", 0.9);
      setCapturedImage(imageUrl);
      
      // Create a File object from blob
      const file = new File([blob], `capture-${Date.now()}.jpg`, {
        type: "image/jpeg",
      });
      setImageFile(file);
      
      console.log("Image captured successfully", { size: blob.size, fileName: file.name });
      
      // Stop camera after capture
      stopCamera();
    }, "image/jpeg", 0.9);
  };

  // Retake image
  const retakeImage = () => {
    setCapturedImage(null);
    setImageFile(null);
    startCamera();
  };

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (data: { file: File; document_type: string; upload_notes?: string }) => {
      setUploadProgress(20);
      const result = await api.uploadFile(data.file, data.document_type, data.upload_notes);
      setUploadProgress(100);
      return result;
    },
    onSuccess: () => {
      setUploadComplete(true);
      queryClient.invalidateQueries({ queryKey: ["importedExpenses"] });
      toast.success("Image uploaded and processed successfully!");
      
      setTimeout(() => {
        handleClose();
      }, 2000);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to upload image");
      setUploadProgress(0);
    },
  });

  // Submit captured image
  const handleSubmit = (values: CaptureFormValues) => {
    if (!imageFile) {
      toast.error("Please capture an image first");
      return;
    }

    setUploadProgress(10);
    uploadMutation.mutate({
      file: imageFile,
      document_type: values.document_type,
      upload_notes: values.upload_notes || undefined,
    });
  };

  // Cleanup on modal close
  const handleClose = () => {
    if (uploadMutation.isPending) return;
    
    // Always stop the camera first
    stopCamera();
    
    // Then reset all state
    form.reset();
    setCapturedImage(null);
    setImageFile(null);
    setUploadProgress(0);
    setUploadComplete(false);
    setCameraError(null);
    setIsCameraActive(false);
    setIsVideoReady(false);
    
    // Call the parent's onClose
    onClose();
  };

  // Start camera automatically when modal opens
  useEffect(() => {
    if (isOpen && !capturedImage && !uploadComplete && !isCameraActive) {
      startCamera();
    }
    
    // Cleanup when modal closes or component unmounts
    return () => {
      stopCamera();
    };
  }, [isOpen, capturedImage, uploadComplete]);

  // Handle video ready state and stream attachment
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // If we have a stream, attach it to the video element
    if (stream) {
      console.log("Attaching stream to video element");
      video.srcObject = stream;
      
      const handleLoadedMetadata = () => {
        console.log("Video metadata loaded", {
          videoWidth: video.videoWidth,
          videoHeight: video.videoHeight,
        });
        setIsVideoReady(true);
      };

      const handleCanPlay = () => {
        console.log("Video can play");
        setIsVideoReady(true);
      };

      const handleError = (e: Event) => {
        console.error("Video error:", e);
        setCameraError("Error loading video stream");
        setIsVideoReady(false);
      };

      video.addEventListener("loadedmetadata", handleLoadedMetadata);
      video.addEventListener("canplay", handleCanPlay);
      video.addEventListener("error", handleError);

      // Start playing the video
      video.play().catch(err => {
        console.error("Error playing video:", err);
        // Try setting ready anyway after a delay
        setTimeout(() => setIsVideoReady(true), 500);
      });

      return () => {
        video.removeEventListener("loadedmetadata", handleLoadedMetadata);
        video.removeEventListener("canplay", handleCanPlay);
        video.removeEventListener("error", handleError);
      };
    } else {
      // No stream, clear the video element
      video.srcObject = null;
    }
  }, [stream]);

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl flex items-center gap-2">
            <Camera className="h-5 w-5 text-primary" />
            Capture Invoice
          </DialogTitle>
        </DialogHeader>

        {uploadComplete ? (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Upload Successful!</h3>
            <p className="text-sm text-muted-foreground">
              Your image has been processed and will appear in the imported expenses.
            </p>
          </div>
        ) : (
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            {/* Camera Preview or Captured Image */}
            <div className="relative bg-gray-100 rounded-lg overflow-hidden aspect-video">
              {cameraError ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
                  <AlertCircle className="h-12 w-12 text-red-500 mb-3" />
                  <p className="text-sm text-red-600 mb-4">{cameraError}</p>
                  <Button onClick={startCamera} variant="outline" size="sm">
                    Try Again
                  </Button>
                </div>
              ) : capturedImage ? (
                <img
                  src={capturedImage}
                  alt="Captured"
                  className="w-full h-full object-contain"
                />
              ) : isCameraActive ? (
                <>
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                  {!isVideoReady && (
                    <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50">
                      <div className="text-center">
                        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-white border-r-transparent mb-2"></div>
                        <p className="text-sm text-white">Loading camera...</p>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <Camera className="h-16 w-16 text-gray-400 mb-4" />
                  <p className="text-sm text-gray-500 mb-4">Click Start Camera to begin</p>
                  <Button onClick={startCamera} variant="default">
                    <Camera className="h-4 w-4 mr-2" />
                    Start Camera
                  </Button>
                </div>
              )}
              
              {/* Hidden canvas for capturing */}
              <canvas ref={canvasRef} className="hidden" />
            </div>

            {/* Camera Controls */}
            {isCameraActive && !capturedImage && (
              <div className="flex justify-center gap-3">
                <Button
                  type="button"
                  onClick={captureImage}
                  size="lg"
                  className="bg-primary hover:bg-primary/90"
                  disabled={!isVideoReady}
                >
                  <Camera className="h-5 w-5 mr-2" />
                  Capture
                </Button>
                <Button
                  type="button"
                  onClick={stopCamera}
                  variant="outline"
                  size="lg"
                >
                  <X className="h-5 w-5 mr-2" />
                  Cancel
                </Button>
              </div>
            )}

            {/* Image Preview Controls */}
            {capturedImage && !uploadMutation.isPending && (
              <>
                {/* Document Type */}
                <div className="space-y-2">
                  <Label htmlFor="document_type">Document Type</Label>
                  <Select
                    value={form.watch("document_type")}
                    onValueChange={(value) => form.setValue("document_type", value)}
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
                    rows={3}
                    {...form.register("upload_notes")}
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-2">
                  <Button
                    type="button"
                    onClick={retakeImage}
                    variant="outline"
                    className="flex-1"
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Retake
                  </Button>
                  <Button
                    type="submit"
                    className="flex-1 bg-primary hover:bg-primary/90"
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Submit
                  </Button>
                </div>
              </>
            )}

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
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

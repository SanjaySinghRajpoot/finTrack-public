import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Mail, Link2, Unlink, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
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

interface GmailIntegrationProps {
  isConnected: boolean;
  onStatusChange?: () => void;
}

const GmailIntegration = ({ isConnected: initialIsConnected, onStatusChange }: GmailIntegrationProps) => {
  const [isConnected, setIsConnected] = useState(initialIsConnected);
  const [isLinking, setIsLinking] = useState(false);
  const [isDelinking, setIsDelinking] = useState(false);
  const [showDelinkDialog, setShowDelinkDialog] = useState(false);
  const { toast } = useToast();

  const handleLink = async () => {
    setIsLinking(true);
    try {
      const { auth_url } = await api.linkIntegration("gmail");
      
      // Redirect to OAuth URL
      window.location.href = auth_url;
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Connection Failed",
        description: error instanceof Error ? error.message : "Failed to connect Gmail",
      });
      setIsLinking(false);
    }
  };

  const handleDelink = async () => {
    setIsDelinking(true);
    setShowDelinkDialog(false);
    
    try {
      await api.delinkIntegration("gmail");
      
      setIsConnected(false);
      toast({
        title: "Gmail Disconnected",
        description: "Your Gmail account has been successfully disconnected",
      });
      
      // Notify parent component
      onStatusChange?.();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Disconnection Failed",
        description: error instanceof Error ? error.message : "Failed to disconnect Gmail",
      });
    } finally {
      setIsDelinking(false);
    }
  };

  return (
    <>
      <Card className="shadow-sm border-border">
        <CardHeader className="border-b bg-gradient-to-r from-primary/5 to-accent/5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-primary/15 shrink-0">
                <Mail className="h-6 w-6 text-primary" />
              </div>
              <div>
                <CardTitle className="text-lg">Gmail Integration</CardTitle>
                <CardDescription>
                  Connect your Gmail to automatically import expenses from emails
                </CardDescription>
              </div>
            </div>
            <div>
              {isConnected ? (
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle2 className="h-5 w-5" />
                  <span className="text-sm font-medium">Connected</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <AlertCircle className="h-5 w-5" />
                  <span className="text-sm font-medium">Not Connected</span>
                </div>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {isConnected
                ? "Your Gmail account is connected and ready to import expense emails automatically."
                : "Connect your Gmail account to start importing expense-related emails automatically."}
            </p>

            <div className="flex gap-3">
              {!isConnected ? (
                <Button
                  onClick={handleLink}
                  disabled={isLinking}
                  className="w-full sm:w-auto"
                >
                  {isLinking ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Connecting...
                    </>
                  ) : (
                    <>
                      <Link2 className="mr-2 h-4 w-4" />
                      Connect Gmail
                    </>
                  )}
                </Button>
              ) : (
                <Button
                  onClick={() => setShowDelinkDialog(true)}
                  disabled={isDelinking}
                  variant="destructive"
                  className="w-full sm:w-auto"
                >
                  {isDelinking ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Disconnecting...
                    </>
                  ) : (
                    <>
                      <Unlink className="mr-2 h-4 w-4" />
                      Disconnect Gmail
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delink Confirmation Dialog */}
      <AlertDialog open={showDelinkDialog} onOpenChange={setShowDelinkDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Disconnect Gmail?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to disconnect your Gmail account? This will stop automatic
              email imports. You can reconnect at any time.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelink} className="bg-destructive hover:bg-destructive/90">
              Disconnect
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default GmailIntegration;

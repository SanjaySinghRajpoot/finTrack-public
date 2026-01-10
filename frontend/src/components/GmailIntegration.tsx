import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Mail, Link2, Unlink, Loader2, CheckCircle2, AlertCircle, Shield, Lock, Eye, FileText, Database, ArrowRight } from "lucide-react";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";

interface GmailIntegrationProps {
  isConnected: boolean;
  onStatusChange?: () => void;
}

const GmailIntegration = ({ isConnected: initialIsConnected, onStatusChange }: GmailIntegrationProps) => {
  const [isConnected, setIsConnected] = useState(initialIsConnected);
  const [isLinking, setIsLinking] = useState(false);
  const [isDelinking, setIsDelinking] = useState(false);
  const [showDelinkDialog, setShowDelinkDialog] = useState(false);
  const [showConnectDialog, setShowConnectDialog] = useState(false);
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

  const handleConnectClick = () => {
    console.log("Connect button clicked, setting showConnectDialog to true");
    setShowConnectDialog(true);
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
            {/* Privacy Information Alert */}
            {!isConnected && (
              <Alert className="bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800">
                <div className="flex gap-3">
                  <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
                  <div className="space-y-2">
                    <AlertDescription className="text-sm text-blue-900 dark:text-blue-100 font-medium">
                      Your Privacy Matters
                    </AlertDescription>
                    <AlertDescription className="text-xs text-blue-800 dark:text-blue-200 space-y-1">
                      <p>• We only access emails containing invoices, bills, and receipts</p>
                      <p>• Read-only access - we never modify or delete your emails</p>
                      <p>• No access to personal emails, contacts, or other data</p>
                      <p>• You can disconnect anytime without affecting your Gmail</p>
                    </AlertDescription>
                  </div>
                </div>
              </Alert>
            )}

            <p className="text-sm text-muted-foreground">
              {isConnected
                ? "Your Gmail account is connected and ready to import expense emails automatically."
                : "Connect your Gmail account to start importing expense-related emails automatically."}
            </p>

            <div className="flex gap-3">
              {!isConnected ? (
                <Button
                  onClick={handleConnectClick}
                  disabled={isLinking}
                  className="w-full sm:w-auto"
                >
                  <Link2 className="mr-2 h-4 w-4" />
                  Connect Gmail
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

      {/* Connect Gmail Information Dialog */}
      <Dialog open={showConnectDialog} onOpenChange={setShowConnectDialog}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto z-50">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-3 rounded-xl bg-primary/15">
                <Mail className="h-6 w-6 text-primary" />
              </div>
              <div>
                <DialogTitle className="text-xl">Connect Your Gmail Account</DialogTitle>
                <DialogDescription className="text-base mt-1">
                  Review what access we need and how we'll use your data
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* What We'll Access */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Eye className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-foreground">What We'll Access</h3>
              </div>
              <div className="space-y-2 pl-7">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                  <FileText className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Email Content</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      We'll only read emails that contain keywords like "invoice", "receipt", "bill", or "payment confirmation"
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                  <Database className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Email Metadata</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Subject lines, sender information, and dates to identify relevant expense emails
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            {/* What We Won't Access */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Lock className="h-5 w-5 text-green-600" />
                <h3 className="font-semibold text-foreground">What We Won't Access</h3>
              </div>
              <div className="space-y-2 pl-7">
                <Alert className="bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800">
                  <AlertDescription className="text-xs text-green-900 dark:text-green-100 space-y-1">
                    <p>✓ Personal emails (newsletters, conversations, etc.)</p>
                    <p>✓ Your contacts or contact list</p>
                    <p>✓ Calendar events or appointments</p>
                    <p>✓ Google Drive files or documents</p>
                    <p>✓ Any other Google services data</p>
                  </AlertDescription>
                </Alert>
              </div>
            </div>

            <Separator />

            {/* How We Use Your Data */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-blue-600" />
                <h3 className="font-semibold text-foreground">How We Use Your Data</h3>
              </div>
              <div className="space-y-2 pl-7">
                <div className="text-sm text-muted-foreground space-y-2">
                  <p className="flex items-start gap-2">
                    <span className="text-primary font-bold mt-0.5">1.</span>
                    <span>Extract expense information (amounts, vendors, dates) from matching emails</span>
                  </p>
                  <p className="flex items-start gap-2">
                    <span className="text-primary font-bold mt-0.5">2.</span>
                    <span>Automatically categorize and import expenses into your FinTrack account</span>
                  </p>
                  <p className="flex items-start gap-2">
                    <span className="text-primary font-bold mt-0.5">3.</span>
                    <span>Store processed expense data securely in your account</span>
                  </p>
                </div>
              </div>
            </div>

            <Separator />

            {/* Security & Privacy */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-purple-600" />
                <h3 className="font-semibold text-foreground">Security & Privacy Guarantee</h3>
              </div>
              <div className="space-y-2 pl-7">
                <Alert className="bg-purple-50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800">
                  <AlertDescription className="text-xs text-purple-900 dark:text-purple-100 space-y-1">
                    <p>🔒 Read-only access - we never modify or delete your emails</p>
                    <p>🔒 Industry-standard encryption for all data transmission</p>
                    <p>🔒 We never share your data with third parties</p>
                    <p>🔒 Disconnect anytime without affecting your Gmail account</p>
                    <p>🔒 Full compliance with Google's security standards</p>
                  </AlertDescription>
                </Alert>
              </div>
            </div>

            {/* Important Note */}
            <Alert className="bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800">
              <AlertCircle className="h-4 w-4 text-amber-600" />
              <AlertDescription className="text-xs text-amber-900 dark:text-amber-100">
                <strong>Next Step:</strong> You'll be redirected to Google's secure login page to authorize this connection. 
                FinTrack will never see or store your Gmail password.
              </AlertDescription>
            </Alert>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setShowConnectDialog(false)}
              disabled={isLinking}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                setShowConnectDialog(false);
                handleLink();
              }}
              disabled={isLinking}
              className="bg-primary hover:bg-primary/90"
            >
              {isLinking ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  Continue to Google
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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

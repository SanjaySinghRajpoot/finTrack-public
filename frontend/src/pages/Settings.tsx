import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Settings as SettingsIcon, Mail, MessageSquare, CheckCircle2, AlertCircle, Calendar, Activity } from "lucide-react";
import { api, Integration } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";
import { useToast } from "@/hooks/use-toast";

const Settings = () => {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await api.getUserSettings();
        setIntegrations(data);
      } catch (error) {
        toast({
          variant: "destructive",
          title: "Error",
          description: "Failed to load settings",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, [toast]);

  const getIntegrationIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "gmail":
        return <Mail className="h-6 w-6 text-primary" />;
      case "slack":
        return <MessageSquare className="h-6 w-6 text-primary" />;
      default:
        return <Activity className="h-6 w-6 text-primary" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      connected: "default",
      disconnected: "destructive",
      pending: "secondary",
    };
    
    return (
      <Badge variant={variants[status.toLowerCase()] || "outline"} className="capitalize">
        {status}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            Settings
          </h1>
          <p className="text-muted-foreground mt-1">Manage your preferences and integrations</p>
        </div>
        <div className="grid gap-4 md:gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="shadow-soft border-border animate-pulse">
              <CardContent className="p-6">
                <div className="h-20 bg-muted rounded"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          Settings
        </h1>
        <p className="text-muted-foreground mt-1">Manage your preferences and integrations</p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <SettingsIcon className="h-5 w-5 text-primary" />
          <h2 className="text-xl font-semibold text-foreground">Connected Integrations</h2>
        </div>

        {integrations.length === 0 ? (
          <Card className="shadow-soft border-border">
            <CardContent className="p-8 md:p-12">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 md:w-20 md:h-20 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 mb-4">
                  <SettingsIcon className="h-8 w-8 md:h-10 md:w-10 text-primary" />
                </div>
                <p className="text-lg font-medium text-foreground">No Integrations Found</p>
                <p className="text-sm text-muted-foreground mt-2 max-w-md mx-auto">
                  Connect your accounts to start tracking expenses automatically.
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:gap-6 grid-cols-1 lg:grid-cols-2">
            {integrations.map((integration) => (
              <Card 
                key={integration.integration_id} 
                className="shadow-soft hover:shadow-elevated transition-smooth border-border bg-card overflow-hidden"
              >
                <CardHeader className="border-b bg-gradient-to-r from-muted/30 to-transparent pb-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-xl bg-primary/10 shrink-0">
                        {getIntegrationIcon(integration.integration_type)}
                      </div>
                      <div>
                        <CardTitle className="text-lg capitalize">
                          {integration.integration_type}
                        </CardTitle>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          ID: {integration.integration_id.slice(0, 8)}...
                        </p>
                      </div>
                    </div>
                    {getStatusBadge(integration.status)}
                  </div>
                </CardHeader>
                <CardContent className="p-4 md:p-6 space-y-4">
                  {integration.error_message && (
                    <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                      <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                      <p className="text-sm text-destructive">{integration.error_message}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Calendar className="h-3.5 w-3.5" />
                        <span>Last Synced</span>
                      </div>
                      <p className="text-foreground font-medium pl-5">
                        {integration.last_synced_at 
                          ? format(new Date(integration.last_synced_at), "MMM dd, yyyy HH:mm")
                          : "Never"}
                      </p>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Calendar className="h-3.5 w-3.5" />
                        <span>Next Sync</span>
                      </div>
                      <p className="text-foreground font-medium pl-5">
                        {integration.next_sync_at 
                          ? format(new Date(integration.next_sync_at), "MMM dd, yyyy HH:mm")
                          : "Not scheduled"}
                      </p>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Activity className="h-3.5 w-3.5" />
                        <span>Sync Interval</span>
                      </div>
                      <p className="text-foreground font-medium pl-5">
                        {integration.sync_interval_minutes} minutes
                      </p>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Total Syncs</span>
                      </div>
                      <p className="text-foreground font-medium pl-5">
                        {integration.total_syncs}
                      </p>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-border space-y-2 text-xs text-muted-foreground">
                    <div className="flex justify-between">
                      <span>Created:</span>
                      <span>{format(new Date(integration.created_at), "MMM dd, yyyy")}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Updated:</span>
                      <span>{format(new Date(integration.updated_at), "MMM dd, yyyy")}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;

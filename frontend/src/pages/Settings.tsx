import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Settings as SettingsIcon, Mail, MessageSquare, CheckCircle2, AlertCircle, Calendar, Activity, CreditCard, Zap, Users, Clock, Shield, Star, ExternalLink, Info } from "lucide-react";
import { api, UserSettings, Integration } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { format } from "date-fns";
import { useToast } from "@/hooks/use-toast";

const Settings = () => {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await api.getUserSettings();
        setSettings(data);
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

  const getSubscriptionStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      active: "default",
      trial: "secondary",
      expired: "destructive",
      cancelled: "outline",
    };
    
    return (
      <Badge variant={variants[status.toLowerCase()] || "outline"} className="capitalize">
        {status === "trial" ? "Free Trial" : status}
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
          {[1, 2, 3, 4].map((i) => (
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

  if (!settings) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            Settings
          </h1>
          <p className="text-muted-foreground mt-1">Unable to load settings</p>
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

      {/* Subscription & Credits Overview */}
      <div className="grid gap-4 md:gap-6 grid-cols-1 lg:grid-cols-2">
        {/* Combined Subscription & Credits Card */}
        <Card className="shadow-sm border-border bg-gradient-to-br from-primary/3 to-accent/3 opacity-90">
          <CardHeader className="border-b bg-gradient-to-r from-primary/5 to-accent/5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-primary/15 shrink-0">
                  <CreditCard className="h-6 w-6 text-primary/80" />
                </div>
                <div>
                  <CardTitle className="text-lg">Subscription & Credits</CardTitle>
                  <p className="text-sm text-muted-foreground">Plan details and usage</p>
                </div>
              </div>
              {getSubscriptionStatusBadge(settings.subscription.subscription_status)}
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Subscription Details */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Star className="h-4 w-4 text-primary" />
                <span>Plan Information</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                <div className="space-y-1">
                  <span className="text-muted-foreground">Current Plan</span>
                  <p className="text-foreground font-semibold text-base">
                    {settings.subscription.plan_name}
                  </p>
                </div>
                <div className="space-y-1">
                  <span className="text-muted-foreground">Expires On</span>
                  <p className="text-foreground font-semibold">
                    {format(new Date(settings.subscription.expires_at), "MMM dd, yyyy")}
                  </p>
                </div>
                <div className="space-y-1">
                  <span className="text-muted-foreground">Auto Renewal</span>
                  <p className="text-foreground font-semibold">
                    {settings.subscription.auto_renewal ? (
                      <span className="text-green-600 flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Enabled
                      </span>
                    ) : (
                      <span className="text-amber-600 flex items-center gap-1">
                        <AlertCircle className="h-3.5 w-3.5" />
                        Disabled
                      </span>
                    )}
                  </p>
                </div>
                <div className="space-y-1">
                  <span className="text-muted-foreground">Status</span>
                  <p className="text-foreground font-semibold capitalize">
                    {settings.subscription.subscription_status === "trial" ? "Free Trial" : settings.subscription.subscription_status}
                  </p>
                </div>
              </div>
            </div>

            {/* Credits Section */}
            <div className="space-y-4 pt-4 border-t border-border">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Zap className="h-4 w-4 text-accent" />
                <span>Credit Usage</span>
              </div>
              
              {/* Credit Progress Bar */}
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Monthly Usage</span>
                  <span className="text-sm font-semibold text-foreground">
                    {settings.credits.credits_used} / {settings.credits.total_allocated} used
                  </span>
                </div>
                <Progress 
                  value={settings.credits.usage_percentage} 
                  className="h-2.5"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{settings.credits.usage_percentage.toFixed(1)}% consumed</span>
                  <span>{settings.credits.current_balance} credits remaining</span>
                </div>
              </div>

              {/* Credit Stats Grid */}
              <div className="grid grid-cols-3 gap-4 pt-3">
                <div className="text-center p-3 rounded-lg bg-primary/5">
                  <p className="text-xl font-bold text-primary">{settings.credits.total_allocated}</p>
                  <p className="text-xs text-muted-foreground">Allocated</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-accent/10">
                  <p className="text-xl font-bold text-accent">{settings.credits.current_balance}</p>
                  <p className="text-xs text-muted-foreground">Available</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted/50">
                  <p className="text-xl font-bold text-muted-foreground">{settings.credits.credits_used}</p>
                  <p className="text-xs text-muted-foreground">Used</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Integrations Section */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <SettingsIcon className="h-5 w-5 text-primary" />
          <h2 className="text-xl font-semibold text-foreground">Connected Integrations</h2>
        </div>

        {settings.integrations.length === 0 ? (
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
            {settings.integrations.map((integration) => (
              <Dialog key={integration.integration_id}>
                <DialogTrigger asChild>
                  <Card className="shadow-lg hover:shadow-xl transition-all duration-300 border-border bg-gradient-to-br from-primary/5 to-accent/10 dark:from-primary/10 dark:to-accent/5 cursor-pointer group hover:scale-[1.02] hover:border-primary/30">
                    <CardHeader className="border-b bg-gradient-to-r from-primary/8 to-accent/15 dark:from-primary/15 dark:to-accent/10 group-hover:from-primary/12 group-hover:to-accent/20 transition-all duration-300">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="p-2.5 rounded-xl bg-primary/15 group-hover:bg-primary/25 transition-all duration-300 shrink-0">
                            {getIntegrationIcon(integration.integration_type)}
                          </div>
                          <div>
                            <CardTitle className="text-lg group-hover:text-primary transition-colors">
                              {integration.integration_name}
                            </CardTitle>
                            <p className="text-sm text-muted-foreground">{integration.provider} • {integration.category}</p>
                          </div>
                        </div>
                        <div className="flex flex-col gap-1 items-end">
                          {getStatusBadge(integration.status)}
                          {integration.can_use_integration ? (
                            <div className="flex items-center gap-1 text-xs text-green-600">
                              <CheckCircle2 className="h-3 w-3" />
                              Available
                            </div>
                          ) : (
                            <div className="flex items-center gap-1 text-xs text-destructive">
                              <AlertCircle className="h-3 w-3" />
                              Unavailable
                            </div>
                          )}
                          <div className="flex items-center gap-1 text-xs text-primary group-hover:text-primary/80 transition-colors">
                            <ExternalLink className="h-3 w-3" />
                            View Details
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="p-6 space-y-4">
                      {integration.error_message && (
                        <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                          <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                          <p className="text-sm text-destructive">{integration.error_message}</p>
                        </div>
                      )}

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Clock className="h-3.5 w-3.5" />
                            <span>Last Sync</span>
                          </div>
                          <p className="text-foreground font-medium pl-5">
                            {integration.last_synced_at 
                              ? format(new Date(integration.last_synced_at), "MMM dd, yyyy")
                              : "Never"}
                          </p>
                        </div>

                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            <span>Total Syncs</span>
                          </div>
                          <p className="text-foreground font-medium pl-5">
                            {integration.total_syncs} completed
                          </p>
                        </div>
                      </div>

                      {integration.features.length > 0 && (
                        <div className="pt-2 border-t border-border">
                          <div className="flex flex-wrap gap-2">
                            {integration.features.map((feature) => (
                              <div 
                                key={feature.feature_key}
                                className="flex items-center gap-1 px-2 py-1 rounded bg-muted/50 text-xs"
                              >
                                {feature.can_use ? (
                                  <CheckCircle2 className="h-3 w-3 text-green-500" />
                                ) : (
                                  <AlertCircle className="h-3 w-3 text-destructive" />
                                )}
                                <span className="text-foreground font-medium">{feature.display_name}</span>
                                <Badge variant="outline" className="text-xs px-1 py-0">
                                  {feature.credit_cost}
                                </Badge>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </DialogTrigger>

                {/* Detailed Modal */}
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-2 rounded-lg bg-primary/15">
                        {getIntegrationIcon(integration.integration_type)}
                      </div>
                      <div>
                        <DialogTitle className="text-xl">{integration.integration_name}</DialogTitle>
                        <DialogDescription className="text-base mt-1">
                          {integration.description}
                        </DialogDescription>
                      </div>
                    </div>
                  </DialogHeader>

                  <div className="space-y-6">
                    {/* Status and Basic Info */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-3">
                        <h4 className="font-semibold text-foreground border-b pb-1">Connection Status</h4>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Status:</span>
                            {getStatusBadge(integration.status)}
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Availability:</span>
                            {integration.can_use_integration ? (
                              <Badge variant="default" className="text-xs">
                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                Available
                              </Badge>
                            ) : (
                              <Badge variant="destructive" className="text-xs">
                                <AlertCircle className="h-3 w-3 mr-1" />
                                Unavailable
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Provider:</span>
                            <Badge variant="outline">{integration.provider}</Badge>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Category:</span>
                            <Badge variant="outline" className="capitalize">{integration.category}</Badge>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <h4 className="font-semibold text-foreground border-b pb-1">Sync Information</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Last Synced:</span>
                            <span className="font-medium">
                              {integration.last_synced_at 
                                ? format(new Date(integration.last_synced_at), "MMM dd, yyyy 'at' HH:mm")
                                : "Never synced"}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Next Sync:</span>
                            <span className="font-medium">
                              {integration.next_sync_at 
                                ? format(new Date(integration.next_sync_at), "MMM dd, yyyy 'at' HH:mm")
                                : "Not scheduled"}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Sync Interval:</span>
                            <span className="font-medium">Every {Math.round(integration.sync_interval_minutes / 60)} hours</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Total Syncs:</span>
                            <span className="font-medium">{integration.total_syncs} completed</span>
                          </div>
                          {integration.last_sync_duration && (
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Last Duration:</span>
                              <span className="font-medium">{integration.last_sync_duration}ms</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Error Message */}
                    {integration.error_message && (
                      <div className="space-y-2">
                        <h4 className="font-semibold text-destructive border-b border-destructive/20 pb-1">Error Details</h4>
                        <div className="flex items-start gap-2 p-4 rounded-lg bg-destructive/10 border border-destructive/20">
                          <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                          <p className="text-sm text-destructive">{integration.error_message}</p>
                        </div>
                      </div>
                    )}

                    {/* Features Section */}
                    {integration.features.length > 0 && (
                      <div className="space-y-3">
                        <h4 className="font-semibold text-foreground border-b pb-1">
                          Available Features ({integration.features.length})
                        </h4>
                        <div className="space-y-3">
                          {integration.features.map((feature) => (
                            <div 
                              key={feature.feature_key}
                              className="flex items-start gap-3 p-4 rounded-lg border bg-muted/20"
                            >
                              <div className="shrink-0 mt-1">
                                {feature.can_use ? (
                                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                                ) : (
                                  <AlertCircle className="h-5 w-5 text-destructive" />
                                )}
                              </div>
                              <div className="flex-1 space-y-2">
                                <div className="flex items-center justify-between">
                                  <h5 className="font-medium text-foreground">{feature.display_name}</h5>
                                  <Badge variant="outline">
                                    {feature.credit_cost} credit{feature.credit_cost !== 1 ? 's' : ''}
                                  </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground">{feature.description}</p>
                                <div className="flex items-center gap-4 text-xs">
                                  <span className="text-muted-foreground">Category: <span className="font-medium capitalize">{feature.category}</span></span>
                                  <span className="text-muted-foreground">Status: <span className="font-medium">{feature.usage_reason}</span></span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Connection Details */}
                    <div className="space-y-3 pt-4 border-t">
                      <h4 className="font-semibold text-foreground border-b pb-1">Connection Details</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Integration ID:</span>
                          <p className="font-mono text-xs mt-1 p-2 bg-muted rounded">
                            {integration.integration_id}
                          </p>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Created:</span>
                            <span className="font-medium">
                              {format(new Date(integration.created_at), "MMM dd, yyyy 'at' HH:mm")}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Last Updated:</span>
                            <span className="font-medium">
                              {format(new Date(integration.updated_at), "MMM dd, yyyy 'at' HH:mm")}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            ))}
          </div>
        )}
      </div>

      {/* 
      TODO: Commented out Integration Overview section - can be restored if needed
      
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          <h2 className="text-xl font-semibold text-foreground">Integration Overview</h2>
        </div>
        
        <Card className="shadow-sm border-border bg-gradient-to-br from-muted/20 to-muted/10 opacity-90">
          <CardHeader className="border-b bg-gradient-to-r from-muted/30 to-muted/20">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-muted/30 shrink-0">
                <Activity className="h-6 w-6 text-muted-foreground" />
              </div>
              <div>
                <CardTitle className="text-lg">Integration Overview</CardTitle>
                <p className="text-sm text-muted-foreground">Connected services summary</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            // Integration overview content would go here
          </CardContent>
        </Card>
      </div>
      */}
    </div>
  );
};

export default Settings;

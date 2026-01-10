import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { User, Mail, Edit, Save, X, Calendar, MapPin, Globe, Image as ImageIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { api, UpdateUserDetailsPayload } from "@/lib/api";
import { useState } from "react";
import { useAnalytics, EVENTS } from "@/lib/analytics";
import { Badge } from "@/components/ui/badge";

const Profile = () => {
  const { toast } = useToast();
  const { trackEvent } = useAnalytics();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<UpdateUserDetailsPayload>({});

  const { data: user, isLoading, error } = useQuery({
    queryKey: ["user"],
    queryFn: api.getUser,
    retry: false,
    refetchOnMount: true,
    staleTime: 0,
  });

  const updateUserMutation = useMutation({
    mutationFn: api.updateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user"] });
      setIsEditing(false);
      setFormData({});
      
      trackEvent('profile_update_success', {
        source: 'profile_page',
        fields_updated: Object.keys(formData).filter(key => formData[key as keyof UpdateUserDetailsPayload]),
      });
      
      toast({
        title: "Profile Updated",
        description: "Your profile has been successfully updated.",
      });
    },
    onError: (error: any) => {
      trackEvent('profile_update_failed', {
        source: 'profile_page',
        error_message: error.message,
        fields_attempted: Object.keys(formData).filter(key => formData[key as keyof UpdateUserDetailsPayload]),
      });
      
      toast({
        title: "Update Failed",
        description: error.message || "Failed to update profile. Please try again.",
        variant: "destructive",
      });
    },
  });

  const getInitials = () => {
    if (!user) return "U";
    return `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase() || user.email[0].toUpperCase();
  };

  const getFullName = () => {
    if (!user) return "User";
    return `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email.split("@")[0];
  };

  const handleEdit = () => {
    if (user) {
      setFormData({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        profile_image: user.profile_image || "",
        country: user.country || "",
        locale: user.locale || "",
      });
    }
    
    trackEvent('profile_edit_initiated', {
      source: 'profile_page',
      has_first_name: !!user?.first_name,
      has_last_name: !!user?.last_name,
      has_profile_image: !!user?.profile_image,
      has_country: !!user?.country,
      has_locale: !!user?.locale,
    });
    
    setIsEditing(true);
  };

  const handleCancel = () => {
    trackEvent('profile_edit_cancelled', {
      source: 'profile_page',
      had_changes: Object.keys(formData).length > 0,
    });
    
    setIsEditing(false);
    setFormData({});
  };

  const handleSave = () => {
    const payload: UpdateUserDetailsPayload = {};
    
    if (formData.first_name && formData.first_name.trim()) {
      payload.first_name = formData.first_name.trim();
    }
    if (formData.last_name && formData.last_name.trim()) {
      payload.last_name = formData.last_name.trim();
    }
    if (formData.profile_image && formData.profile_image.trim()) {
      payload.profile_image = formData.profile_image.trim();
    }
    if (formData.country && formData.country.trim()) {
      payload.country = formData.country.trim();
    }
    if (formData.locale && formData.locale.trim()) {
      payload.locale = formData.locale.trim();
    }

    trackEvent('profile_update_attempted', {
      source: 'profile_page',
      fields_to_update: Object.keys(payload),
      field_count: Object.keys(payload).length,
    });

    updateUserMutation.mutate(payload);
  };

  const handleInputChange = (field: keyof UpdateUserDetailsPayload, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-destructive mb-2">Failed to load profile data</p>
          <p className="text-sm text-muted-foreground">Please try refreshing the page</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          Profile Settings
        </h1>
        <p className="text-muted-foreground mt-1">Manage your account information and preferences</p>
      </div>

      {/* Single Consolidated Profile Card */}
      <div className="max-w-4xl">
        <Card className="shadow-sm border-border bg-gradient-to-br from-primary/3 to-accent/3 opacity-90">
          <CardHeader className="border-b bg-gradient-to-r from-primary/5 to-accent/5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-primary/15 shrink-0">
                  <User className="h-6 w-6 text-primary/80" />
                </div>
                <div>
                  <CardTitle className="text-lg">Account Information</CardTitle>
                  <CardDescription>Manage your profile and preferences</CardDescription>
                </div>
              </div>
              <div className="flex gap-2">
                {!isEditing ? (
                  <Button 
                    onClick={handleEdit}
                    className="bg-primary hover:bg-primary/90 shadow-md"
                    size="sm"
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit Profile
                  </Button>
                ) : (
                  <>
                    <Button 
                      onClick={handleSave}
                      disabled={updateUserMutation.isPending}
                      className="bg-green-600 hover:bg-green-700 shadow-md"
                      size="sm"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {updateUserMutation.isPending ? "Saving..." : "Save"}
                    </Button>
                    <Button 
                      onClick={handleCancel}
                      variant="outline"
                      disabled={updateUserMutation.isPending}
                      size="sm"
                    >
                      <X className="h-4 w-4 mr-2" />
                      Cancel
                    </Button>
                  </>
                )}
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="p-6 space-y-6">
            {/* Profile Header Section */}
            <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 pb-6 border-b">
              <Avatar className="h-20 w-20 border-4 border-primary/20 shadow-lg">
                {(isEditing ? formData.profile_image : user?.profile_image) ? (
                  <AvatarImage
                    src={isEditing ? formData.profile_image : user?.profile_image || ""}
                    alt="User avatar"
                    className="object-cover"
                  />
                ) : (
                  <AvatarFallback className="bg-primary text-primary-foreground text-xl font-bold">
                    {getInitials()}
                  </AvatarFallback>
                )}
              </Avatar>
              <div className="text-center sm:text-left flex-1">
                <h2 className="text-xl font-bold text-foreground">{getFullName()}</h2>
                <p className="text-sm text-muted-foreground flex items-center justify-center sm:justify-start gap-2 mt-1">
                  <Mail className="h-3.5 w-3.5" />
                  {user?.email}
                </p>
                <div className="flex items-center gap-2 justify-center sm:justify-start mt-2">
                  <Badge variant="outline" className="text-xs">
                    ID: {user?.id}
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    Active
                  </Badge>
                </div>
              </div>
            </div>

            {/* Personal Information Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <User className="h-4 w-4 text-primary" />
                <span>Personal Information</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">First Name</Label>
                  <Input 
                    value={isEditing ? formData.first_name || "" : user?.first_name || "Not set"} 
                    onChange={(e) => handleInputChange("first_name", e.target.value)}
                    disabled={!isEditing} 
                    className={isEditing ? "bg-background h-9 text-sm" : "bg-muted/50 h-9 text-sm"}
                    placeholder={isEditing ? "Enter first name" : ""}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Last Name</Label>
                  <Input 
                    value={isEditing ? formData.last_name || "" : user?.last_name || "Not set"} 
                    onChange={(e) => handleInputChange("last_name", e.target.value)}
                    disabled={!isEditing} 
                    className={isEditing ? "bg-background h-9 text-sm" : "bg-muted/50 h-9 text-sm"}
                    placeholder={isEditing ? "Enter last name" : ""}
                  />
                </div>
                
                <div className="space-y-2 sm:col-span-2">
                  <Label className="text-xs text-muted-foreground">Email Address</Label>
                  <Input 
                    value={user?.email || ""} 
                    disabled 
                    className="bg-muted/50 h-9 text-sm"
                  />
                  <p className="text-xs text-muted-foreground">Email cannot be changed</p>
                </div>
              </div>
            </div>

            {/* Location & Preferences Section */}
            <div className="space-y-4 pt-4 border-t">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Globe className="h-4 w-4 text-primary" />
                <span>Location & Preferences</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Country</Label>
                  <Input 
                    value={isEditing ? formData.country || "" : user?.country || "Not set"} 
                    onChange={(e) => handleInputChange("country", e.target.value)}
                    disabled={!isEditing} 
                    className={isEditing ? "bg-background h-9 text-sm" : "bg-muted/50 h-9 text-sm"}
                    placeholder={isEditing ? "Enter country" : ""}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Locale</Label>
                  <Input 
                    value={isEditing ? formData.locale || "" : user?.locale || "Not set"} 
                    onChange={(e) => handleInputChange("locale", e.target.value)}
                    disabled={!isEditing} 
                    className={isEditing ? "bg-background h-9 text-sm" : "bg-muted/50 h-9 text-sm"}
                    placeholder={isEditing ? "e.g., en-US" : ""}
                  />
                </div>

                {isEditing && (
                  <div className="space-y-2 sm:col-span-2">
                    <Label className="text-xs text-muted-foreground flex items-center gap-1">
                      <ImageIcon className="h-3 w-3" />
                      Profile Image URL
                    </Label>
                    <Input 
                      value={formData.profile_image || ""} 
                      onChange={(e) => handleInputChange("profile_image", e.target.value)}
                      className="bg-background h-9 text-sm"
                      placeholder="https://example.com/avatar.jpg"
                    />
                    <p className="text-xs text-muted-foreground">Enter a valid image URL for your profile picture</p>
                  </div>
                )}
              </div>
            </div>

            {/* Account Details Section */}
            <div className="space-y-4 pt-4 border-t">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Calendar className="h-4 w-4 text-primary" />
                <span>Account Details</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Account Created</Label>
                  <p className="text-sm font-medium text-foreground">
                    {user ? new Date(user.created_at).toLocaleDateString('en-US', { 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric'
                    }) : ""}
                  </p>
                </div>
                
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Last Updated</Label>
                  <p className="text-sm font-medium text-foreground">
                    {user?.updated_at ? new Date(user.updated_at).toLocaleDateString('en-US', { 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric'
                    }) : "Never"}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Profile;

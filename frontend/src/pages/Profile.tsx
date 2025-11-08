import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { User, Mail, Edit, Save, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { api, UpdateUserDetailsPayload } from "@/lib/api";
import { useState } from "react";

const Profile = () => {
  const { toast } = useToast();
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
      toast({
        title: "Profile Updated",
        description: "Your profile has been successfully updated.",
      });
    },
    onError: (error: any) => {
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
    setIsEditing(true);
  };

  const handleCancel = () => {
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
      <div>
        <h1 className="text-2xl md:text-4xl font-bold text-primary">Profile Settings</h1>
        <p className="text-sm md:text-base text-muted-foreground mt-1">Manage your account</p>
      </div>

      <Card className="shadow-soft border bg-card">
        <CardContent className="p-6 md:p-8">
          <div className="flex flex-col sm:flex-row items-center gap-6 md:gap-8">
            <Avatar className="h-24 w-24 md:h-32 md:w-32 border-4 border-primary/20 shadow-lg">
            {(isEditing ? formData.profile_image : user?.profile_image) ? (
              <AvatarImage
                src={isEditing ? formData.profile_image : user?.profile_image || ""}
                alt="User avatar"
                className="object-cover"
              />
            ) : (
              <AvatarFallback className="bg-primary text-primary-foreground text-2xl md:text-3xl font-bold">
                {getInitials()}
              </AvatarFallback>
            )}
            </Avatar>
            <div className="flex-1 text-center sm:text-left space-y-2">
              <h2 className="text-2xl md:text-3xl font-bold text-foreground">{getFullName()}</h2>
              <p className="text-base md:text-lg text-muted-foreground flex items-center justify-center sm:justify-start gap-2">
                <Mail className="h-4 w-4" />
                {user?.email}
              </p>
              <p className="text-sm text-muted-foreground">Member ID: {user?.id}</p>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              {!isEditing ? (
                <Button 
                  onClick={handleEdit}
                  className="bg-primary hover:bg-primary/90 w-full sm:w-auto shadow-md"
                >
                  <Edit className="h-4 w-4 mr-2" />
                  Edit Profile
                </Button>
              ) : (
                <>
                  <Button 
                    onClick={handleSave}
                    disabled={updateUserMutation.isPending}
                    className="bg-green-600 hover:bg-green-700 w-full sm:w-auto shadow-md"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {updateUserMutation.isPending ? "Saving..." : "Save"}
                  </Button>
                  <Button 
                    onClick={handleCancel}
                    variant="outline"
                    disabled={updateUserMutation.isPending}
                    className="w-full sm:w-auto"
                  >
                    <X className="h-4 w-4 mr-2" />
                    Cancel
                  </Button>
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-soft border bg-card">
        <CardHeader className="border-b bg-muted/30 pb-4">
          <CardTitle className="text-xl md:text-2xl font-semibold text-foreground">Account Information</CardTitle>
        </CardHeader>
        <CardContent className="p-6 md:p-8 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">First Name</Label>
              <Input 
                value={isEditing ? formData.first_name || "" : user?.first_name || "Not set"} 
                onChange={(e) => handleInputChange("first_name", e.target.value)}
                disabled={!isEditing} 
                className={isEditing ? "bg-background border-border text-foreground font-medium" : "bg-muted/50 border-border text-foreground font-medium"}
                placeholder={isEditing ? "Enter first name" : ""}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Last Name</Label>
              <Input 
                value={isEditing ? formData.last_name || "" : user?.last_name || "Not set"} 
                onChange={(e) => handleInputChange("last_name", e.target.value)}
                disabled={!isEditing} 
                className={isEditing ? "bg-background border-border text-foreground font-medium" : "bg-muted/50 border-border text-foreground font-medium"}
                placeholder={isEditing ? "Enter last name" : ""}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Email Address</Label>
              <Input 
                value={user?.email || ""} 
                disabled 
                className="bg-muted/50 border-border text-foreground font-medium"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Country</Label>
              <Input 
                value={isEditing ? formData.country || "" : user?.country || "Not set"} 
                onChange={(e) => handleInputChange("country", e.target.value)}
                disabled={!isEditing} 
                className={isEditing ? "bg-background border-border text-foreground font-medium" : "bg-muted/50 border-border text-foreground font-medium"}
                placeholder={isEditing ? "Enter country" : ""}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Locale</Label>
              <Input 
                value={isEditing ? formData.locale || "" : user?.locale || "Not set"} 
                onChange={(e) => handleInputChange("locale", e.target.value)}
                disabled={!isEditing} 
                className={isEditing ? "bg-background border-border text-foreground font-medium" : "bg-muted/50 border-border text-foreground font-medium"}
                placeholder={isEditing ? "Enter locale (e.g., en-US)" : ""}
              />
            </div>
            {isEditing && (
              <div className="space-y-2">
                <Label className="text-sm font-medium text-muted-foreground">Profile Image URL</Label>
                <Input 
                  value={formData.profile_image || ""} 
                  onChange={(e) => handleInputChange("profile_image", e.target.value)}
                  className="bg-background border-border text-foreground font-medium"
                  placeholder="Enter profile image URL"
                />
              </div>
            )}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Account Created</Label>
              <Input 
                value={user ? new Date(user.created_at).toLocaleDateString('en-US', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                }) : ""} 
                disabled 
                className="bg-muted/50 border-border text-foreground font-medium"
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Profile;

import { useQuery } from "@tanstack/react-query";
import { User, Mail } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

const Profile = () => {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ["user"],
    queryFn: api.getUser,
    retry: false,
    refetchOnMount: true,
    staleTime: 0,
  });

  if (error) {
    console.error("Error fetching user:", error);
  }

  const getInitials = () => {
    if (!user) return "U";
    return `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase() || user.email[0].toUpperCase();
  };

  const getFullName = () => {
    if (!user) return "User";
    console.log(user.profile_image)
    return `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email.split("@")[0];
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
            {user.profile_image != null ? (
              <AvatarImage
                src={user.profile_image}
                alt="User avatar"
                className="object-cover"
              />
            ) : null}
              {/* <AvatarFallback className="bg-primary text-primary-foreground text-2xl md:text-3xl font-bold">
                {getInitials()}
              </AvatarFallback> */}
            </Avatar>
            <div className="flex-1 text-center sm:text-left space-y-2">
              <h2 className="text-2xl md:text-3xl font-bold text-foreground">{getFullName()}</h2>
              <p className="text-base md:text-lg text-muted-foreground flex items-center justify-center sm:justify-start gap-2">
                <Mail className="h-4 w-4" />
                {user.email}
              </p>
              <p className="text-sm text-muted-foreground">Member ID: {user.id}</p>
            </div>
            <Button className="bg-primary hover:bg-primary/90 w-full sm:w-auto shadow-md">
              Edit Profile
            </Button>
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
                value={user.first_name || "Not set"} 
                disabled 
                className="bg-muted/50 border-border text-foreground font-medium"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Last Name</Label>
              <Input 
                value={user.last_name || "Not set"} 
                disabled 
                className="bg-muted/50 border-border text-foreground font-medium"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Email Address</Label>
              <Input 
                value={user.email} 
                disabled 
                className="bg-muted/50 border-border text-foreground font-medium"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Country</Label>
              <Input 
                value={user.country || "Not set"} 
                disabled 
                className="bg-muted/50 border-border text-foreground font-medium"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Locale</Label>
              <Input 
                value={user.locale || "Not set"} 
                disabled 
                className="bg-muted/50 border-border text-foreground font-medium"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-muted-foreground">Account Created</Label>
              <Input 
                value={new Date(user.created_at).toLocaleDateString('en-US', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })} 
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

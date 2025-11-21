import { Plane, Coffee, Home, ShoppingBag, Car, Utensils, Heart, Gamepad2, Briefcase, Smartphone, GraduationCap, Wallet } from "lucide-react";
import { LucideIcon } from "lucide-react";

export interface CategoryConfig {
  name: string;
  icon: LucideIcon;
  color: string;
  bgColor: string;
}

export const categories: Record<string, CategoryConfig> = {
  Travel: {
    name: "Travel",
    icon: Plane,
    color: "hsl(200 95% 38%)",
    bgColor: "hsl(200 95% 95%)",
  },
  Food: {
    name: "Food",
    icon: Utensils,
    color: "hsl(38 92% 50%)",
    bgColor: "hsl(38 92% 95%)",
  },
  Rent: {
    name: "Rent",
    icon: Home,
    color: "hsl(142 76% 36%)",
    bgColor: "hsl(142 76% 95%)",
  },
  Shopping: {
    name: "Shopping",
    icon: ShoppingBag,
    color: "hsl(280 70% 50%)",
    bgColor: "hsl(280 70% 95%)",
  },
  Transport: {
    name: "Transport",
    icon: Car,
    color: "hsl(15 80% 50%)",
    bgColor: "hsl(15 80% 95%)",
  },
  Groceries: {
    name: "Groceries",
    icon: Coffee,
    color: "hsl(30 90% 45%)",
    bgColor: "hsl(30 90% 95%)",
  },
  Healthcare: {
    name: "Healthcare",
    icon: Heart,
    color: "hsl(0 84% 60%)",
    bgColor: "hsl(0 84% 95%)",
  },
  Entertainment: {
    name: "Entertainment",
    icon: Gamepad2,
    color: "hsl(260 60% 55%)",
    bgColor: "hsl(260 60% 95%)",
  },
  Business: {
    name: "Business",
    icon: Briefcase,
    color: "hsl(220 80% 40%)",
    bgColor: "hsl(220 80% 95%)",
  },
  Technology: {
    name: "Technology",
    icon: Smartphone,
    color: "hsl(195 85% 45%)",
    bgColor: "hsl(195 85% 95%)",
  },
  Education: {
    name: "Education",
    icon: GraduationCap,
    color: "hsl(150 60% 45%)",
    bgColor: "hsl(150 60% 95%)",
  },
  Other: {
    name: "Other",
    icon: Wallet,
    color: "hsl(215 16% 47%)",
    bgColor: "hsl(215 16% 95%)",
  },
};

export const getCategoryConfig = (category: string): CategoryConfig => {
  return categories[category] || categories.Other;
};

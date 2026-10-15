import { SessionProvider } from "./components/session";
import { CropShell } from "./components/shell";
import type { Metadata } from "next";
import "./crop-planning.css";

export const metadata: Metadata = {
  title: "AgFarm | AI-Based Cultivation Risk Analysis & Crop Planning",
  description: "AI-based cultivation concentration risk analysis, alternative crop recommendation, and personalized cultivation planning system.",
};

export default function CropPlanningLayout({ children }: { children: React.ReactNode }) { return <SessionProvider><CropShell>{children}</CropShell></SessionProvider>; }

import { SessionProvider } from "../crop-planning/components/session";
import { AdminSessionProvider } from "../crop-planning/lib/admin-session";
import { CropShell } from "../crop-planning/components/shell";
import type { Metadata } from "next";
import "../crop-planning/crop-planning.css";

export const metadata: Metadata = {
  title: "AgroDecision AI | Waste Management & Transport Tracking",
  description:
    "Component 3: Barcode-Based Produce Tracking, Spoilage Risk Prediction & Circular Bioeconomy Waste Recovery",
};

export default function WasteManagementLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AdminSessionProvider>
        <CropShell>{children}</CropShell>
      </AdminSessionProvider>
    </SessionProvider>
  );
}

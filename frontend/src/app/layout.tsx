import type { Metadata } from "next";
import "./crop-planning/crop-planning.css";
import "./portal.css";

export const metadata: Metadata = {
  title: "AgroDecision AI | Data-Driven Farmer Decision System",
  description:
    "Data-Driven Farmer Decision System for Collaborative Crop Planning, Market Risk Reduction, Produce Tracking, and Climate Early Warning. AIMS Research Group, Faculty of Computing (IT).",
  keywords: [
    "Sri Lanka Smart Agriculture",
    "Crop Planning",
    "Market Risk Reduction",
    "Cultivation Concentration Risk",
    "AIMS Research",
    "Agri-Supply Chain",
    "Food Security",
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body style={{ margin: 0, padding: 0 }}>
        {children}
      </body>
    </html>
  );
}

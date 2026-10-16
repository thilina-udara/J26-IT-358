import type { Metadata } from "next";
import React from "react";
import "./market-profit.css";
import { Shell } from "./components/Shell";

export const metadata: Metadata = {
  title: "AgroDecision — Market Demand, Price Trends & Profit Risk",
  description:
    "Your Farming Partner — AI-driven Smart Farmer Decision Support for Sri Lankan agriculture",
};

export default function MarketProfitLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-800 antialiased">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}

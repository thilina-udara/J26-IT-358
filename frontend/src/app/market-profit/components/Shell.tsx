"use client";

import React, { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { FarmerProfileModal } from "./FarmerProfileModal";

export function Shell({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Left Sidebar with 4 main items */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onOpenProfile={() => setIsProfileOpen(true)}
      />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 lg:pl-72 transition-all duration-300">
        {/* Top Header */}
        <Header
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
          onOpenProfile={() => setIsProfileOpen(true)}
        />

        {/* Page Body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>

      {/* Farmer Profile Modal */}
      <FarmerProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
      />
    </div>
  );
}

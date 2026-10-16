"use client";

import React, { useState, createContext, useContext } from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { StartAnalysisModal } from "./StartAnalysisModal";

interface ShellContextType {
  openStartAnalysisModal: () => void;
}

const ShellContext = createContext<ShellContextType>({
  openStartAnalysisModal: () => {},
});

export function useShell() {
  return useContext(ShellContext);
}

export function Shell({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState(false);

  const openModal = () => setIsAnalysisModalOpen(true);
  const closeModal = () => setIsAnalysisModalOpen(false);

  return (
    <ShellContext.Provider value={{ openStartAnalysisModal: openModal }}>
      <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
        {/* Left Sidebar */}
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          onStartAnalysisClick={openModal}
        />

        {/* Main Content Area */}
        <div className="flex flex-col flex-1 lg:pl-72 transition-all duration-300">
          {/* Top Header */}
          <Header onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)} />

          {/* Page Body */}
          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
            {children}
          </main>
        </div>

        {/* Friendly Start Analysis Workflow Modal */}
        <StartAnalysisModal
          isOpen={isAnalysisModalOpen}
          onClose={closeModal}
        />
      </div>
    </ShellContext.Provider>
  );
}

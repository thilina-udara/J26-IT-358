import React from "react";
import { Check } from "lucide-react";

interface WizardProgressProps {
  currentStep: number;
}

const STEPS = [
  { step: 1, title: "Crop & Location", description: "Select variety & district" },
  { step: 2, title: "Harvest Details", description: "Yield & planned date" },
  { step: 3, title: "Selling Market", description: "Target economic centre" },
  { step: 4, title: "Cultivation Costs", description: "Farming expenditure" },
];

export function WizardProgress({ currentStep }: WizardProgressProps) {
  return (
    <div className="w-full bg-white rounded-2xl border border-slate-200/90 p-5 sm:p-6 shadow-xs mb-8">
      <div className="relative">
        {/* Step List */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {STEPS.map((s, idx) => {
            const isCompleted = s.step < currentStep;
            const isCurrent = s.step === currentStep;

            return (
              <div key={s.step} className="flex items-start gap-3">
                {/* Step Circle Indicator */}
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl font-bold text-sm transition-colors ${
                    isCompleted
                      ? "bg-[#15803d] text-white shadow-xs"
                      : isCurrent
                      ? "bg-[#15803d] text-white ring-4 ring-emerald-100 shadow-sm"
                      : "bg-slate-100 text-slate-400 border border-slate-200"
                  }`}
                >
                  {isCompleted ? (
                    <Check className="h-5 w-5 stroke-[2.5]" />
                  ) : (
                    <span>{s.step}</span>
                  )}
                </div>

                {/* Step Text Info */}
                <div className="min-w-0">
                  <div
                    className={`text-xs font-bold truncate ${
                      isCurrent
                        ? "text-[#166534]"
                        : isCompleted
                        ? "text-slate-800"
                        : "text-slate-400"
                    }`}
                  >
                    Step {s.step}
                  </div>
                  <div
                    className={`text-xs sm:text-sm font-semibold truncate ${
                      isCurrent
                        ? "text-slate-900"
                        : isCompleted
                        ? "text-slate-700"
                        : "text-slate-400"
                    }`}
                  >
                    {s.title}
                  </div>
                  <div className="hidden sm:block text-[11px] text-slate-400 truncate">
                    {s.description}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

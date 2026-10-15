"use client";
import * as React from "react";
import { cn } from "../../lib/utils";

// Native adapter for the existing onChange contract, keyboard support and mobile pickers.
// This supplements the shadcn primitives; it is not the Radix Select component.
const NativeSelect = React.forwardRef<HTMLSelectElement, React.ComponentProps<"select">>(
  ({ className, ...props }, ref) => <select ref={ref} className={cn("h-11 w-full rounded-md border border-input bg-card px-3 py-2 text-base shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-destructive md:text-sm", className)} {...props} />
);
NativeSelect.displayName = "NativeSelect";
export { NativeSelect };

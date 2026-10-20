export const ROOT = "/crop-planning";
export const PUBLIC_ROUTES = [ROOT, `${ROOT}/login`, `${ROOT}/register`, `${ROOT}/admin/login`] as const;
export const WORKSPACE_NAV = [
  { href: `${ROOT}/dashboard`, label: "Dashboard", icon: "dashboard" },
  { href: `${ROOT}/plans`, label: "My Farm Plans", icon: "plans" },
  { href: `${ROOT}/risk-analysis`, label: "Risk Analysis", icon: "analysis" },
  { href: `${ROOT}/suggested-crops`, label: "Suggested Crops", icon: "crops" },
  { href: `${ROOT}/cultivation-methods`, label: "Cultivation Planning", icon: "planning" },
  { href: "/waste-management", label: "Waste Management", icon: "waste" },
  { href: `${ROOT}/research-demo`, label: "Research Lab (2025-2026)", icon: "research" },
  { href: `${ROOT}/plans#profile`, label: "My Profile", icon: "profile" },
] as const;

export function isPublicRoute(path: string) {
  return PUBLIC_ROUTES.some((route) => route === path);
}

export function activeWorkspace(path: string, href: string) {
  if (href.endsWith("/dashboard")) return path === href || path === `${ROOT}/dashboard`;
  if (href === "/waste-management" || href.endsWith("/waste-management")) return path.startsWith("/waste-management") || path.includes("/transport-tracking");
  if (href.endsWith("/transport-tracking")) return path.includes("/transport-tracking");
  if (href.endsWith("/risk-analysis")) return path === href || path.endsWith("/analysis");
  if (href.endsWith("/suggested-crops")) return path === href || path.endsWith("/alternatives");
  if (href.endsWith("/cultivation-methods")) return path.includes("/cultivation-methods");
  if (href.endsWith("/cultivation-plan"))
    return path === href || (path.startsWith(`${ROOT}/plans`) && !path.endsWith("/analysis") && !path.endsWith("/alternatives"));
  if (href.endsWith("/research-demo")) return path.includes("/research-demo");
  if (href.endsWith("/plans"))
    return path === href || path === `${ROOT}/plans` || (path.startsWith(`${ROOT}/plans`) && !path.endsWith("/analysis") && !path.endsWith("/alternatives"));
  if (href.includes("#profile")) return path.includes("#profile");
  return path === href;
}

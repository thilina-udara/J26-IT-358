export const ROOT = "/crop-planning";
export const PUBLIC_ROUTES = [ROOT, `${ROOT}/login`, `${ROOT}/register`] as const;
export const WORKSPACE_NAV = [
  { href: `${ROOT}/dashboard`, label: "Dashboard", icon: "dashboard" },
  { href: `${ROOT}/plans`, label: "My Farm Plans", icon: "plans" },
  { href: `${ROOT}/risk-analysis`, label: "Risk Analysis", icon: "analysis" },
  { href: `${ROOT}/suggested-crops`, label: "Suggested Crops", icon: "crops" },
  { href: `${ROOT}/cultivation-methods`, label: "Cultivation Planning", icon: "planning" },
  { href: `${ROOT}/research-demo`, label: "Research Lab (2025-2026)", icon: "research" },
  { href: `${ROOT}/plans#profile`, label: "My Profile", icon: "profile" },
] as const;

export function isPublicRoute(path: string) {
  return PUBLIC_ROUTES.some((route) => route === path);
}

export function activeWorkspace(path: string, href: string) {
  if (href.endsWith("/dashboard")) return path === href || path === `${ROOT}/dashboard`;
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

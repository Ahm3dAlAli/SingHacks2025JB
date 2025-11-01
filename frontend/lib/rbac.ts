export type Role = "relationship_manager" | "compliance_manager" | "legal";

export const Permissions = {
  // Documentation review typically for Compliance and Legal
  reviewDocs: (role: Role) => role === "compliance_manager" || role === "legal",
  // Alert actions typically for Relationship Managers and Compliance
  actOnAlerts: (role: Role) => role === "relationship_manager" || role === "compliance_manager",
} as const;

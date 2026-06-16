// TS mirrors of the Florence-X API contract (florence_core Pydantic models).
// Kept hand-written and narrow to what the console renders.

export type RiskTier = "green" | "yellow" | "orange" | "red" | "red_blocked";

export type EdenaDecisionType =
  | "allow"
  | "allow_with_constraints"
  | "require_human"
  | "escalate"
  | "deny"
  | "throttle"
  | "contain"
  | "stop";

export type ReviewOutcome = "approve" | "edit" | "escalate" | "deny" | "stop";

export interface ReviewItem {
  workflow_run_id: string;
  workflow_id: string;
  status: string;
  action_id: string | null;
  action_type: string | null;
  intended_target: string | null;
  data_classification: string | null;
  reversible: boolean | null;
  external_boundary_crossed: boolean | null;
  blast_radius_estimate: string | null;
  decision_id: string | null;
  decision: EdenaDecisionType | null;
  risk_tier: RiskTier | null;
  required_human_role: string | null;
  rationale: string | null;
  constraints: string[];
  evidence_bundle_id: string | null;
  source_citations: string[];
}

export interface ReviewDecisionRequest {
  outcome: ReviewOutcome;
  reviewer_ref: string;
  reviewer_role?: string | null;
  note?: string | null;
  edited_payload_hash?: string | null;
}

export interface WorkflowRun {
  workflow_run_id: string;
  workflow_id: string;
  signal_id: string;
  status: string;
  current_step: string | null;
  evidence_bundle_id: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface EdenaDecision {
  decision_id: string;
  action_id: string;
  decision: EdenaDecisionType;
  risk_tier: RiskTier;
  required_human_role: string | null;
  constraints: string[];
  rationale: string;
  evidence_required: string[];
  policy_pack_version: string | null;
}

export interface HumanReviewRecord {
  review_id: string;
  action_id: string;
  decision_id: string;
  reviewer_role: string;
  reviewer_ref: string;
  outcome: ReviewOutcome;
  note: string | null;
  reviewed_at: string;
}

export interface ToolCallRecord {
  tool_id: string;
  action_id: string;
  proposed: boolean;
  executed: boolean;
  output_hash: string | null;
  error: string | null;
}

export interface EvidenceBundle {
  bundle_id: string;
  workflow_run_id: string;
  signal_id: string;
  context_hash: string | null;
  model_used: string | null;
  agent_versions: Record<string, string>;
  tool_calls: ToolCallRecord[];
  edena_decisions: EdenaDecision[];
  human_reviews: HumanReviewRecord[];
  final_action: string | null;
  source_citations: string[];
  incident_flags: string[];
  completed_at: string | null;
  created_at: string;
}

export interface Incident {
  incident_id: string;
  workflow_run_id: string | null;
  action_id: string | null;
  category: string;
  severity: string;
  summary: string;
  triggered_by: string;
  containment_applied: string[];
  resolved: boolean;
  created_at: string;
}

export interface AgentDefinition {
  agent_id: string;
  name: string;
  version: string;
  purpose: string;
  owner_role: string;
  institutional_approval_ref: string | null;
  allowed_tools: string[];
  prohibited_tasks: string[];
  edena_baseline_tier: RiskTier;
  active: boolean;
}

export interface ToolUsage {
  tool_id: string;
  authorized_agents: string[];
}

export interface CloudEvent {
  specversion: string;
  id: string;
  source: string;
  type: string;
  subject: string;
  time: string;
  data: Record<string, unknown>;
}

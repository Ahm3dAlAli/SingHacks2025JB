export interface Rule {
  rule_id: string;
  jurisdiction: string;
  regulator: string;
  rule_type: string;
  rule_text: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  is_active: boolean;
  rule_parameters?: Record<string, any>;
  effective_date?: string;
  tags?: string[];
}

export interface RulesResponse {
  data: Rule[];
  total: number;
  skip: number;
  limit: number;
}

export interface RuleFilters {
  jurisdiction?: string;
  regulator?: string;
  rule_type?: string;
  is_active?: boolean;
  search?: string;
}

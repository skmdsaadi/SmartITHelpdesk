export type User = { id: number; name: string; email: string; role: 'employee' | 'admin' }
export const categories = ['Email', 'Network', 'Hardware', 'Software', 'Printer', 'Access'] as const
export const priorities = ['Low', 'Normal', 'High'] as const
export const statuses = ['Open', 'In Progress', 'Resolved'] as const
export type Ticket = {
  id: number; title: string; description: string
  category: typeof categories[number]; priority: typeof priorities[number]; status: typeof statuses[number]
  created_by: number; creator: User; created_at: string; updated_at: string
  resolved_at: string | null; version: number; ai_assessment: AIResult | null
}
export type Comment = { id: number; body: string; author: User; created_at: string }
export type TicketEvent = { id: number; message: string; author: User; created_at: string }
export type Detail = Ticket & { comments: Comment[]; events: TicketEvent[] }
export type TicketPage = { items: Ticket[]; total: number; page: number; page_size: number }
export type Dashboard = { total: number; open: number; in_progress: number; resolved: number; high_priority: number; recent: Ticket[] }
export type Health = { status: string; version: string; components: { database: string }; registration_enabled: boolean }

export type AIResult = {
  suggested_category: typeof categories[number] | null
  model_score: number | null; needs_review: boolean; reason: string; message: string
  scores: { category: typeof categories[number]; score: number }[]
  margin: number | null; similarity: number | null; model_version: string | null
  scope: 'synthetic_english_demo'; selected_category?: typeof categories[number] | null
  recorded_at?: string | null
}
export type ModelMetrics = {
  count: number; accuracy: number; macro_f1: number; accepted: number
  coverage: number; accepted_accuracy: number | null; confusion_matrix: number[][]
}
export type ModelReport = {
  status: string; model_version: string; algorithm: string; examples: number; groups: number
  categories: string[]; threshold: number; majority_baseline_accuracy: number
  split_counts: Record<'train' | 'validation' | 'test', number>
  split_group_counts: Record<'train' | 'validation' | 'test', number>
  test: ModelMetrics; validation: ModelMetrics
  negative_controls: Record<'validation' | 'test', { count: number; accepted: number }>
  limitations: string[]
}

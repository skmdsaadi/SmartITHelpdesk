export type User = { id: number; name: string; email: string; role: 'employee' | 'admin' }
export const categories = ['Email', 'Network', 'Hardware', 'Software', 'Printer', 'Access'] as const
export const priorities = ['Low', 'Normal', 'High'] as const
export const statuses = ['Open', 'In Progress', 'Resolved'] as const
export type Ticket = {
  id: number; title: string; description: string
  category: typeof categories[number]; priority: typeof priorities[number]; status: typeof statuses[number]
  created_by: number; creator: User; created_at: string; updated_at: string
  resolved_at: string | null; version: number
}
export type Comment = { id: number; body: string; author: User; created_at: string }
export type TicketEvent = { id: number; message: string; author: User; created_at: string }
export type Detail = Ticket & { comments: Comment[]; events: TicketEvent[] }
export type TicketPage = { items: Ticket[]; total: number; page: number; page_size: number }
export type Dashboard = { total: number; open: number; in_progress: number; resolved: number; high_priority: number; recent: Ticket[] }
export type Health = { status: string; version: string; components: { database: string }; registration_enabled: boolean }

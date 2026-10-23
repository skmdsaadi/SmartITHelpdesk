import type { ReactNode } from 'react'
import type { Ticket } from './types'

export function Icon({ name = 'headset', size = 20 }: { name?: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    book: <><path d="M12 5v15M3 4h5a4 4 0 0 1 4 2 4 4 0 0 1 4-2h5v15h-5a4 4 0 0 0-4 2 4 4 0 0 0-4-2H3V4Z"/></>,
    chat: <><path d="M21 11a8 8 0 0 1-8 8H7l-4 3V5a3 3 0 0 1 3-3h7a8 8 0 0 1 8 9Z"/><path d="M7 8h9M7 12h6"/></>,
    upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"/></>,
    trash: <><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/></>,
    file: <><path d="M14 2H5v20h14V7l-5-5Zm0 0v5h5M8 12h8m-8 4h6"/></>,
    headset: <><path d="M4 13v-2a8 8 0 0 1 16 0v2M4 12H3v6h4v-6H4Zm16 0h1v6h-4v-6h3ZM20 18v1a2 2 0 0 1-2 2h-5" /></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    ticket: <><path d="M3 5h18v5a2 2 0 0 0 0 4v5H3v-5a2 2 0 0 0 0-4V5Z"/><path d="M15 5v3m0 3v2m0 3v3"/></>,
    sparkles: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/><path d="M20 2v4m-2-2h4"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
    arrow: <path d="m9 5 7 7-7 7"/>,
    back: <path d="m15 5-7 7 7 7"/>,
    logout: <><path d="M10 4H4v16h6m4-12 4 4-4 4m-5-4h12"/></>,
    check: <><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    search: <><circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/></>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/></>,
    shield: <><path d="m12 3 8 3v6c0 4-5 8-8 9-3-1-8-5-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] ?? paths.headset}</svg>
}
export function Alert({ children }: { children: ReactNode }) {
  return <div role="alert" className="alert">{children}</div>
}
export function Loading() { return <div className="loading" role="status"><span className="spinner"/>Loading your workspace…</div> }
export function Empty({ title, children }: { title: string; children: ReactNode }) {
  return <div className="empty"><div className="empty-icon"><Icon name="ticket" size={27}/></div><h3>{title}</h3><p>{children}</p></div>
}
export function Badge({ value }: { value: string }) {
  const color = ({Open: 'blue', 'In Progress': 'amber', Resolved: 'teal', High: 'rose', Normal: 'slate', Low: 'slate'} as Record<string, string>)[value] ?? 'slate'
  return <span className={'badge badge-' + color}><span/>{value}</span>
}
export function dateTime(value: string, short = false) {
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short',
    ...(short ? {} : { hour: '2-digit', minute: '2-digit' }), timeZone: 'Asia/Dhaka' }).format(new Date(value))
}
export function ticketCode(id: number) { return 'IT-' + String(id).padStart(5, '0') }
export function TicketTable({ items }: { items: Ticket[] }) {
  return <div className="ticket-table">
    <div className="ticket-table-head"><span>Ticket</span><span>Category</span><span>Priority</span><span>Status</span><span>Created</span><span/></div>
    {items.map(t => <a className="ticket-row" href={'#tickets/' + t.id} key={t.id}>
      <div className="ticket-title"><small>{ticketCode(t.id)}</small><strong>{t.title}</strong><span>{t.creator.name}</span></div>
      <span className="ticket-category">{t.category}</span><Badge value={t.priority}/><Badge value={t.status}/>
      <span className="ticket-date">{dateTime(t.created_at, true)}</span><Icon name="arrow" size={16}/>
    </a>)}
  </div>
}

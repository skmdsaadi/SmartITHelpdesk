import { useState } from 'react'
import type { FormEvent } from 'react'
import { api, errorText, useResource } from './api'
import { categories, priorities, statuses } from './types'
import type { Detail, Ticket, User } from './types'
import { Alert, Badge, dateTime, Icon, Loading, ticketCode } from './ui'

function AdminControls({ ticket, onSaved }: { ticket: Ticket; onSaved: () => void }) {
  const [status, setStatus] = useState(ticket.status)
  const [priority, setPriority] = useState(ticket.priority)
  const [category, setCategory] = useState(ticket.category)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      await api('/tickets/' + ticket.id, { method: 'PATCH', body: JSON.stringify({ status, priority, category, version: ticket.version }) })
      onSaved()
    } catch (reason) { setError(errorText(reason)) } finally { setBusy(false) }
  }
  return <section className="panel panel-pad"><h2>Manage ticket</h2><p className="muted control-note">Changes are recorded in the activity history.</p>
    {error && <Alert>{error}</Alert>}
    <form className="stack compact" onSubmit={submit}>
      <label>Status<select aria-label="Status" value={status} onChange={e => setStatus(e.target.value as Ticket['status'])} disabled={busy}>{statuses.map(v => <option key={v}>{v}</option>)}</select></label>
      <label>Priority<select aria-label="Priority" value={priority} onChange={e => setPriority(e.target.value as Ticket['priority'])} disabled={busy}>{priorities.map(v => <option key={v}>{v}</option>)}</select></label>
      <label>Category<select aria-label="Category" value={category} onChange={e => setCategory(e.target.value as Ticket['category'])} disabled={busy}>{categories.map(v => <option key={v}>{v}</option>)}</select></label>
      <button className="btn primary wide" disabled={busy || (status === ticket.status && priority === ticket.priority && category === ticket.category)}>{busy ? 'Saving…' : 'Save changes'}</button>
    </form>
  </section>
}
function ReplyForm({ id, onSaved }: { id: number; onSaved: () => void }) {
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      await api('/tickets/' + id + '/comments', { method: 'POST', body: JSON.stringify({ body }) })
      setBody(''); onSaved()
    } catch (reason) { setError(errorText(reason)) } finally { setBusy(false) }
  }
  return <form className="stack reply-form" onSubmit={submit}>
    {error && <Alert>{error}</Alert>}
    <label>Add a reply<textarea value={body} onChange={e => setBody(e.target.value)} rows={3} maxLength={5000} required placeholder="Share an update or ask a question…" disabled={busy}/></label>
    <div className="reply-bottom"><small>Visible to the requester and IT administrators.</small><button className="btn primary" disabled={busy || !body.trim()}>{busy ? 'Sending…' : 'Send reply'}<Icon name="arrow" size={15}/></button></div>
  </form>
}

export default function TicketDetail({ id, user }: { id: number; user: User }) {
  const { data: ticket, error, loading, refresh } = useResource<Detail>('/tickets/' + id)
  const [notice, setNotice] = useState('')
  function saved(message: string) { setNotice(message); refresh() }
  const activity = ticket ? [
    ...ticket.comments.map(c => ({ ...c, text: c.body, key: 'c' + c.id, isComment: true })),
    ...ticket.events.map(e => ({ ...e, text: e.message, key: 'e' + e.id, isComment: false })),
  ].sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at) || a.id - b.id) : []
  return <>
    <a className="back-link" href="#tickets"><Icon name="back" size={16}/>Back to tickets</a>
    {notice && <div className="success-note" role="status"><Icon name="check" size={18}/>{notice}</div>}
    {error && <Alert>{error} <button className="text-button" onClick={refresh}>Try again</button></Alert>}
    {loading && <Loading/>}
    {ticket && <>
      <div className="page-heading detail-heading"><div><span className="eyebrow">{ticketCode(ticket.id)}</span><h1>{ticket.title}</h1><div className="detail-tags"><Badge value={ticket.status}/><Badge value={ticket.priority}/><span>{ticket.category}</span></div></div><button className="btn secondary" onClick={refresh}><Icon name="refresh" size={17}/>Refresh</button></div>
      <div className="detail-layout"><div className="detail-main">
        <section className="panel panel-pad"><h2>Issue description</h2><p className="prose-text">{ticket.description}</p></section>
        <section className="panel"><div className="panel-heading"><div><h2>Conversation & activity</h2><p>Every update, in one place</p></div><span className="count-pill">{ticket.comments.length} replies</span></div>
          <div className="activity-list">{activity.map(item => item.isComment ?
            <article className="comment" key={item.key}><div className={'avatar small-avatar ' + (item.author.role === 'admin' ? 'admin-avatar' : '')}>{item.author.name.slice(0, 1).toUpperCase()}</div><div className="comment-content"><div className="comment-meta"><strong>{item.author.name}</strong>{item.author.role === 'admin' && <span className="role-label">IT team</span>}<time dateTime={item.created_at}>{dateTime(item.created_at)}</time></div><p>{item.text}</p></div></article> :
            <div className="activity-event" key={item.key}><span className="event-dot"/><div><p>{item.text}</p><small>{item.author.name} · {dateTime(item.created_at)}</small></div></div>
          )}</div>
          <ReplyForm id={ticket.id} onSaved={() => saved('Your reply has been added.')}/>
        </section>
      </div><aside className="detail-aside">
        {user.role === 'admin' && <AdminControls key={ticket.version} ticket={ticket} onSaved={() => saved('Ticket updated.')}/>}
        <section className="panel panel-pad"><h2>Ticket details</h2><dl className="ticket-facts">
          <div><dt>Requested by</dt><dd>{ticket.creator.name}<small>{ticket.creator.email}</small></dd></div>
          <div><dt>Created</dt><dd>{dateTime(ticket.created_at)}</dd></div>
          <div><dt>Last updated</dt><dd>{dateTime(ticket.updated_at)}</dd></div>
          {ticket.resolved_at && <div><dt>Resolved</dt><dd>{dateTime(ticket.resolved_at)}</dd></div>}
        </dl><p className="timezone-note">All times shown in Asia/Dhaka.</p></section>
      </aside></div>
    </>}
  </>
}

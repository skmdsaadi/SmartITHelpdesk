import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, errorText, useResource } from './api'
import { categories, priorities, statuses } from './types'
import type { Ticket, TicketPage, User } from './types'
import { Alert, Empty, Icon, Loading, TicketTable } from './ui'

export function Tickets({ user, query }: { user: User; query: string }) {
  const initial = new URLSearchParams(query)
  const [status, setStatus] = useState(initial.get('status') || '')
  const [priority, setPriority] = useState(initial.get('priority') || '')
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [page, setPage] = useState(1)
  useEffect(() => {
    const timer = window.setTimeout(() => { setDebounced(search); setPage(1) }, 300)
    return () => window.clearTimeout(timer)
  }, [search])
  const params = new URLSearchParams({ page: String(page), page_size: '10' })
  if (status) params.set('status', status)
  if (category) params.set('category', category)
  if (priority) params.set('priority', priority)
  if (debounced.trim()) params.set('search', debounced.trim())
  const { data, error, loading, refresh } = useResource<TicketPage>('/tickets?' + params.toString())
  function reset() { setStatus(''); setPriority(''); setCategory(''); setSearch(''); setPage(1) }
  return <>
    <div className="page-heading"><div><span className="eyebrow">Requests, organized</span><h1>{user.role === 'admin' ? 'All tickets' : 'My tickets'}</h1><p>Find a request, check its progress, or continue the conversation.</p></div><a className="btn primary" href="#create"><Icon name="plus" size={18}/>Create ticket</a></div>
    <section className="panel">
      <div className="filters">
        <label className="search-label"><span className="sr-only">Search tickets</span><Icon name="search" size={18}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search title or description" maxLength={160}/></label>
        <label><span className="sr-only">Filter status</span><select aria-label="Filter status" value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}><option value="">All statuses</option>{statuses.map(s => <option key={s}>{s}</option>)}</select></label>
        <label><span className="sr-only">Filter category</span><select aria-label="Filter category" value={category} onChange={e => { setCategory(e.target.value); setPage(1) }}><option value="">All categories</option>{categories.map(s => <option key={s}>{s}</option>)}</select></label>
        <label><span className="sr-only">Filter priority</span><select aria-label="Filter priority" value={priority} onChange={e => { setPriority(e.target.value); setPage(1) }}><option value="">All priorities</option>{priorities.map(s => <option key={s}>{s}</option>)}</select></label>
        <button className="icon-btn" onClick={refresh} aria-label="Refresh tickets"><Icon name="refresh" size={18}/></button>
      </div>
      {error && <div className="panel-pad"><Alert>{error} <button className="text-button" onClick={refresh}>Try again</button></Alert></div>}
      {loading && <Loading/>}
      {data && <>
        {data.items.length ? <TicketTable items={data.items}/> : <Empty title={data.total === 0 ? 'No tickets to show' : 'No tickets on this page'}>Try another filter or create a ticket. <button className="text-button" onClick={reset}>Clear filters</button></Empty>}
        <div className="pagination"><span>{data.total === 0 ? '0 tickets' : String((page - 1) * 10 + 1) + '–' + String(Math.min(page * 10, data.total)) + ' of ' + data.total + ' tickets'}</span><div><button className="btn secondary small" onClick={() => setPage(p => p - 1)} disabled={page <= 1}>Previous</button><span>Page {page}</span><button className="btn secondary small" onClick={() => setPage(p => p + 1)} disabled={page * 10 >= data.total}>Next</button></div></div>
      </>}
    </section>
  </>
}

export function CreateTicket() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    const data = Object.fromEntries(form.entries())
    try {
      const ticket = await api<Ticket>('/tickets', { method: 'POST', body: JSON.stringify(data) })
      window.location.hash = 'tickets/' + ticket.id
    } catch (reason) { setError(errorText(reason)) } finally { setBusy(false) }
  }
  return <>
    <a className="back-link" href="#tickets"><Icon name="back" size={16}/>Back to tickets</a>
    <div className="page-heading"><div><span className="eyebrow">We are here to help</span><h1>Create a ticket</h1><p>Tell your IT team what is happening.</p></div></div>
    <div className="create-layout"><section className="panel panel-pad">
      {error && <Alert>{error}</Alert>}
      <form className="stack" onSubmit={submit}>
        <label>Issue title<input name="title" aria-label="Issue title" aria-describedby="title-help" minLength={5} maxLength={160} placeholder="Example: Unable to connect to office Wi-Fi" required disabled={busy}/><small id="title-help">A brief, specific summary of the problem.</small></label>
        <div className="form-grid">
          <label>Category<select aria-label="Category" name="category" required defaultValue="" disabled={busy}><option value="" disabled>Select a category</option>{categories.map(c => <option key={c}>{c}</option>)}</select></label>
          <label>Priority<select aria-label="Priority" name="priority" defaultValue="Normal" disabled={busy}>{priorities.map(c => <option key={c}>{c}</option>)}</select></label>
        </div>
        <label>What is happening?<textarea name="description" aria-label="What is happening?" aria-describedby="description-help" rows={7} minLength={15} maxLength={10000} placeholder="Describe the issue, when it started, and what you have already tried." required disabled={busy}/><small id="description-help">At least 15 characters. Include any relevant error message.</small></label>
        <div className="form-actions"><a href="#tickets" className="btn secondary" aria-disabled={busy} onClick={e => { if (busy) e.preventDefault() }}>Cancel</a><button className="btn primary" disabled={busy}>{busy ? 'Submitting…' : 'Submit ticket'}<Icon name="arrow" size={17}/></button></div>
      </form>
    </section><aside className="guidance"><span className="eyebrow">A useful request includes</span><h3>Help us help you.</h3><ol><li>The device or application affected</li><li>The exact error you see</li><li>When the issue first started</li><li>How it affects your work</li></ol><div className="guidance-note"><Icon name="shield"/><p>Keep passwords, recovery codes, and other secrets out of your ticket.</p></div><h4>Choosing a priority</h4><p><strong>High:</strong> Work is blocked or several people are affected.</p><p><strong>Normal:</strong> You can continue with a workaround.</p><p><strong>Low:</strong> General questions or non-urgent requests.</p></aside></div>
  </>
}

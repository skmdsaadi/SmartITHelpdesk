import { useEffect, useState } from 'react'
import { api, ApiError, errorText } from './api'
import type { User } from './types'
import Auth from './Auth'
import Overview from './Overview'
import AIInsights from './AI'
import Knowledge, { KnowledgeDetail } from './Knowledge'
import Chat from './Chat'
import { CreateTicket, Tickets } from './Tickets'
import TicketDetail from './TicketDetail'
import { Alert, Icon, Loading } from './ui'

function route() { return window.location.hash.slice(1) || 'overview' }

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [startupError, setStartupError] = useState('')
  const [path, setPath] = useState(route)
  const [logoutBusy, setLogoutBusy] = useState(false)
  const [logoutError, setLogoutError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    api<User>('/auth/me', { signal: controller.signal }).then(value => {
      if (!controller.signal.aborted) setUser(value)
    }).catch(error => {
      if (!controller.signal.aborted && !(error instanceof ApiError && error.status === 401)) setStartupError(errorText(error))
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    const changed = () => { setPath(route()); window.scrollTo(0, 0) }
    const expired = () => { setUser(null); setStartupError('Please sign in to continue.'); setLogoutError('') }
    window.addEventListener('hashchange', changed)
    window.addEventListener('helpdesk:unauthorized', expired)
    return () => { controller.abort(); window.removeEventListener('hashchange', changed); window.removeEventListener('helpdesk:unauthorized', expired) }
  }, [])
  function signedIn(value: User) { setUser(value); setStartupError(''); window.location.hash = 'overview' }
  async function logout() {
    setLogoutBusy(true); setLogoutError('')
    try { await api('/auth/logout', { method: 'POST' }); setUser(null); setStartupError(''); window.location.hash = 'overview' }
    catch (error) { setLogoutError(errorText(error)) } finally { setLogoutBusy(false) }
  }
  if (loading) return <div className="boot-screen"><div className="brand-icon"><Icon size={28}/></div><Loading/></div>
  if (!user) return <Auth onLogin={signedIn} initialError={startupError}/>
  const [page, query = ''] = path.split('?')
  const ticketMatch = /^tickets\/([1-9]\d*)$/.exec(page)
  const documentMatch = /^knowledge\/([1-9]\d*)$/.exec(page)
  const chatMatch = /^chat\/([1-9]\d*)$/.exec(page)
  let content
  if (page === 'overview') content = <Overview user={user}/>
  else if (page === 'tickets') content = <Tickets key={path} user={user} query={query}/>
  else if (page === 'create') content = <CreateTicket/>
  else if (page === 'ai' && user.role === 'admin') content = <AIInsights/>
  else if (page === 'knowledge') content = <Knowledge user={user}/>
  else if (documentMatch) content = <KnowledgeDetail key={path} id={Number(documentMatch[1])} chunkId={Number(new URLSearchParams(query).get('chunk')) || null}/>
  else if (page === 'chat' || chatMatch) content = <Chat key={page} threadId={chatMatch ? Number(chatMatch[1]) : null}/>
  else if (ticketMatch) content = <TicketDetail key={page} id={Number(ticketMatch[1])} user={user}/>
  else content = <div className="panel panel-pad"><h1>Page not found</h1><a className="text-link" href="#overview">Back to overview</a></div>
  return <div className="workspace">
    <aside className="sidebar">
      <a className="brand" href="#overview"><div className="brand-icon"><Icon size={25}/></div><div>Smart IT<small>HELPDESK</small></div></a>
      <div className="workspace-label">WORKSPACE</div>
      <nav aria-label="Main navigation">
        <a href="#overview" className={page === 'overview' ? 'active' : ''} aria-current={page === 'overview' ? 'page' : undefined}><Icon name="grid"/>Overview</a>
        <a href="#tickets" className={page.startsWith('tickets') ? 'active' : ''} aria-current={page === 'tickets' ? 'page' : undefined}><Icon name="ticket"/>{user.role === 'admin' ? 'All tickets' : 'My tickets'}</a>
        <a href="#create" className={page === 'create' ? 'active' : ''} aria-current={page === 'create' ? 'page' : undefined}><Icon name="plus"/>Create ticket</a>
        <a href="#chat" className={page.startsWith('chat') ? 'active' : ''} aria-current={page.startsWith('chat') ? 'page' : undefined}><Icon name="chat"/>Ask helpdesk</a>
        <a href="#knowledge" className={page.startsWith('knowledge') ? 'active' : ''} aria-current={page.startsWith('knowledge') ? 'page' : undefined}><Icon name="book"/>Knowledge</a>
        {user.role === 'admin' && <a href="#ai" className={page === 'ai' ? 'active' : ''} aria-current={page === 'ai' ? 'page' : undefined}><Icon name="sparkles"/>AI insights</a>}
      </nav>
      <div className="sidebar-tip"><Icon name="headset" size={28}/><h3>Support, kept simple.</h3><p>From the first report to the final resolution.</p></div>
      <div className="sidebar-profile"><span className="avatar">{user.name.slice(0, 1).toUpperCase()}</span><div><strong>{user.name}</strong><small>{user.role === 'admin' ? 'IT Administrator' : 'Employee'}</small></div><button className="icon-btn" aria-label="Sign out" title="Sign out" disabled={logoutBusy} onClick={() => void logout()}><Icon name="logout" size={19}/></button></div>
    </aside>
    <div className="workspace-main">
      <header className="topbar"><div className="breadcrumb">Workspace <span>/</span><strong>{page === 'overview' ? 'Overview' : page === 'create' ? 'Create ticket' : page === 'ai' ? 'AI insights' : page.startsWith('chat') ? 'Ask helpdesk' : page.startsWith('knowledge') ? 'Knowledge' : 'Tickets'}</strong></div><div className="topbar-right"><span className="role-label">{user.role === 'admin' ? 'Admin workspace' : 'Employee workspace'}</span><span className="avatar top-avatar">{user.name.slice(0, 1).toUpperCase()}</span></div></header>
      <main className="main-content" id="main-content">{logoutError && <Alert>{logoutError}</Alert>}{content}</main>
      <footer className="workspace-footer"><span>Smart IT Helpdesk</span><span>One place. Every request.</span></footer>
    </div>
  </div>
}

import { useResource } from './api'
import type { Dashboard, User } from './types'
import { Alert, Empty, Icon, Loading, TicketTable } from './ui'

export default function Overview({ user }: { user: User }) {
  const { data, error, loading, refresh } = useResource<Dashboard>('/dashboard')
  return <>
    <div className="page-heading"><div><span className="eyebrow">Your workspace at a glance</span><h1>Support overview</h1><p>{user.role === 'admin' ? 'A clear view of every request across your helpdesk.' : 'Keep track of your requests and the next steps.'}</p></div><a className="btn primary" href="#create"><Icon name="plus" size={18}/>Create ticket</a></div>
    {error && <Alert>{error} <button className="text-button" onClick={refresh}>Try again</button></Alert>}
    {loading && <Loading/>}
    {data && <>
      <div className="stats-grid">
        {[
          { label: 'Total tickets', value: data.total, icon: 'ticket', color: 'slate', status: '' },
          { label: 'Open', value: data.open, icon: 'ticket', color: 'blue', status: 'Open' },
          { label: 'In progress', value: data.in_progress, icon: 'clock', color: 'amber', status: 'In Progress' },
          { label: 'Resolved', value: data.resolved, icon: 'check', color: 'teal', status: 'Resolved' },
        ].map(card => <a className="stat-card" key={card.label} href={'#tickets' + (card.status ? '?status=' + encodeURIComponent(card.status) : '')}>
          <div className="stat-top"><span>{card.label}</span><span className={'stat-icon ' + card.color}><Icon name={card.icon}/></span></div>
          <strong>{card.value}</strong><small>View tickets <Icon name="arrow" size={13}/></small>
        </a>)}
      </div>
      <div className="attention-line"><span className="attention-dot"/><strong>{data.high_priority}</strong> high-priority {data.high_priority === 1 ? 'ticket needs' : 'tickets need'} attention <a href="#tickets?priority=High">Review tickets <Icon name="arrow" size={13}/></a></div>
      <section className="panel">
        <div className="panel-heading"><div><h2>Recent activity</h2><p>Your five most recently updated tickets</p></div><a href="#tickets" className="text-link">View all <Icon name="arrow" size={15}/></a></div>
        {data.recent.length ? <TicketTable items={data.recent}/> : <Empty title="Your workspace is ready">Create your first ticket to start a conversation with IT.</Empty>}
      </section>
      <section className="help-strip"><span className="help-strip-icon"><Icon size={28}/></span><div><h3>A little detail goes a long way.</h3><p>Include the device, the error message, and when the issue started. Never share your password in a ticket.</p></div><a href="#create" className="btn secondary">Report an issue<Icon name="arrow" size={16}/></a></section>
    </>}
  </>
}

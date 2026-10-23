import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, errorText, useResource } from './api'
import type { ChatTurn, ThreadDetail, ThreadPage } from './types'
import { Alert, dateTime, Icon, Loading } from './ui'

export default function Chat({ threadId }: { threadId: number | null }) {
  const [historyPage, setHistoryPage] = useState(1)
  const history = useResource<ThreadPage>('/chat/threads?page=' + historyPage)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [title, setTitle] = useState('A little guidance, with a source.')
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(threadId !== null)
  const [error, setError] = useState('')
  const [loadError, setLoadError] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [revision, setRevision] = useState(0)
  const pending = useRef<{ id: string; question: string } | null>(null)
  const request = useRef<AbortController | null>(null)
  const bottom = useRef<HTMLDivElement>(null)
  useEffect(() => () => request.current?.abort(), [])
  useEffect(() => {
    if (threadId === null) return
    const controller = new AbortController(); setLoading(true); setLoadError('')
    api<ThreadDetail>(`/chat/threads/${threadId}`, { signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) { setTurns(data.turns); setTitle(data.title) }
    }).catch(err => { if (!controller.signal.aborted) setLoadError(errorText(err)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [threadId, revision])
  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest' }) }, [turns, busy])
  async function ask(event: FormEvent) {
    event.preventDefault()
    const text = question.trim()
    if (text.length < 5 || busy) return
    if (!pending.current || pending.current.question !== text) pending.current = { id: crypto.randomUUID(), question: text }
    const controller = new AbortController(); request.current = controller; setBusy(true); setError('')
    try {
      const turn = await api<ChatTurn>('/chat/ask', { method: 'POST', signal: controller.signal,
        body: JSON.stringify({ question: text, thread_id: threadId, request_id: pending.current.id }) }, 30000)
      if (controller.signal.aborted) return
      setQuestion(''); pending.current = null
      if (threadId === null) window.location.hash = `chat/${turn.thread_id}`
      else { setTurns(old => old.some(t => t.id === turn.id) ? old : [...old, turn]); history.refresh() }
    } catch (err) { if (!controller.signal.aborted) setError(errorText(err)) }
    finally { if (!controller.signal.aborted) setBusy(false) }
  }
  async function remove() {
    if (!threadId) return
    setDeleting(true); setError('')
    try { await api(`/chat/threads/${threadId}`, { method: 'DELETE' }); window.location.hash = 'chat' }
    catch (err) { setError(errorText(err)); setDeleting(false) }
  }
  function startConversation() {
    if (threadId) window.location.hash = 'chat'
    else { setQuestion(''); setError(''); pending.current = null }
  }
  return <>
    <div className="page-heading"><div><div className="eyebrow">ANSWERS WITH A SOURCE</div><h1>Ask helpdesk</h1><p>Find relevant guidance in your team's active documents.</p></div><a className="btn secondary" href="#knowledge"><Icon name="book" size={17}/>Browse knowledge</a></div>
    <div className="chat-layout">
      <aside className="panel chat-history" aria-label="Your conversations"><div className="chat-history-top"><h2>Your conversations</h2><button className="btn primary wide" disabled={busy} onClick={startConversation}><Icon name="plus" size={17}/>Start conversation</button></div>
        {history.error && <div className="chat-history-error"><Alert>{history.error}</Alert><button className="text-button" onClick={history.refresh}>Retry history</button></div>}
        {history.loading ? <Loading/> : <div className="chat-history-list">{history.data?.items.map(t => <button key={t.id} className={t.id === threadId ? 'selected' : ''} disabled={busy} aria-current={t.id === threadId ? 'page' : undefined} onClick={() => { window.location.hash = `chat/${t.id}` }}><Icon name="chat" size={16}/><span><strong>{t.title}</strong><small>{dateTime(t.updated_at)}</small></span></button>)}
          {history.data?.total === 0 && <p>Your saved conversations will appear here.</p>}</div>}
        {history.data && history.data.total > 20 && <div className="history-pagination"><button className="text-button" disabled={historyPage === 1 || busy} onClick={() => setHistoryPage(p => p - 1)}>Previous</button><span>{historyPage}</span><button className="text-button" disabled={historyPage * 20 >= history.data.total || busy} onClick={() => setHistoryPage(p => p + 1)}>Next</button></div>}
        <p className="chat-private-note"><Icon name="shield" size={15}/>Your conversations are visible only to your account.</p>
      </aside>
      <section className="panel chat-main" aria-label="Knowledge conversation">
        <div className="chat-heading"><div className="chat-assistant-icon"><Icon name="book" size={22}/></div><div><h2>{title}</h2><p>Document passages · Source links · Saved history</p></div>
          {threadId && <button className="icon-btn" title="Delete conversation" aria-label="Delete conversation" disabled={busy || deleting} onClick={() => setConfirmDelete(true)}><Icon name="trash" size={18}/></button>}
        </div>
        {confirmDelete && <div className="inline-confirm chat-confirm"><p>Delete this conversation and its questions? This cannot be undone.</p><button className="btn secondary small" disabled={deleting} onClick={() => setConfirmDelete(false)}>Cancel</button><button className="btn danger small" disabled={deleting} onClick={() => void remove()}>Confirm delete</button></div>}
        {loadError ? <div className="panel-pad"><Alert>{loadError}</Alert><button className="btn secondary" onClick={() => setRevision(v => v + 1)}>Retry conversation</button></div> : loading ? <Loading/> : <>
          <div className="chat-log" role="log" aria-label="Questions and document responses" aria-live="polite">
            {turns.length === 0 && <div className="chat-welcome"><div className="welcome-icon"><Icon name="chat" size={33}/></div><span className="eyebrow">START WITH YOUR QUESTION</span><h2>Find the right passage.</h2><p>Ask about an IT issue. The helpdesk searches uploaded documents and shows the matching text with its source.</p><div className="question-examples">{['How do I troubleshoot a Wi-Fi connection?', 'How do I reset my password?', 'What should I check when the printer is offline?'].map(q => <button type="button" disabled={busy} key={q} onClick={() => setQuestion(q)}>{q}<Icon name="arrow" size={14}/></button>)}</div><small>Results depend on the documents your administrator has added.</small></div>}
            {turns.map(turn => <article className="chat-turn" key={turn.id}><div className="chat-question"><span>You · {dateTime(turn.created_at)}</span><p>{turn.question}</p></div><div className="chat-response"><div className="response-label"><Icon name="book" size={17}/>Knowledge assistant<span>{turn.sources.length ? 'Matching passages' : 'No source answer'}</span></div><p className="response-answer">{turn.answer}</p>
              <div className="chat-sources">{turn.sources.map((source, i) => <article className="chat-source" key={source.chunk_id}><div className="chat-source-heading"><span>{i + 1}</span><div><a href={`#knowledge/${source.document_id}?chunk=${source.chunk_id}`}>{source.document_title}<Icon name="arrow" size={13}/></a><small>{source.filename} · {source.page_number ? `Page ${source.page_number} · ` : ''}Passage {source.chunk_index}</small></div></div><blockquote>{source.text}</blockquote></article>)}</div>
              {!turn.sources.length && <a className="text-link" href="#create">Create a support ticket<Icon name="arrow" size={13}/></a>}
            </div></article>)}
            {busy && <div className="chat-searching" role="status"><span className="spinner"/>Searching active documents…</div>}
            <div ref={bottom}/>
          </div>
          <div className="chat-composer">{error && <Alert>{error}</Alert>}<form onSubmit={e => void ask(e)}><label htmlFor="helpdesk-question">Your question</label><textarea id="helpdesk-question" required minLength={5} maxLength={2000} rows={3} value={question} disabled={busy || deleting} onChange={e => setQuestion(e.target.value)} placeholder="Describe the issue and what you want to know…"/><div className="composer-bottom"><small>Each question is searched independently. Replies quote documents; they do not generate a diagnosis.</small><button type="submit" className="btn primary" disabled={busy || deleting || question.trim().length < 5 || turns.length >= 50}>{busy ? 'Searching…' : 'Ask helpdesk'}<Icon name="arrow" size={16}/></button></div>{turns.length >= 50 && <p className="knowledge-warning">This conversation has reached 50 questions. Start another conversation to continue.</p>}</form></div>
        </>}
      </section>
    </div>
  </>
}

import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, errorText, useResource } from './api'
import type { DocumentDetail, DocumentPage, KnowledgeDocument, User } from './types'
import { Alert, dateTime, Empty, Icon, Loading } from './ui'

export default function Knowledge({ user }: { user: User }) {
  const admin = user.role === 'admin'
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [includeInactive, setIncludeInactive] = useState(admin)
  const { data, loading, error, refresh } = useResource<DocumentPage>(`/knowledge/documents?page=${page}&include_inactive=${includeInactive}&search=${encodeURIComponent(search)}`)
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const request = useRef<AbortController | null>(null)
  const [uploading, setUploading] = useState(false)
  const [busy, setBusy] = useState<number | null>(null)
  const [confirm, setConfirm] = useState<number | null>(null)
  const [actionError, setActionError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => () => request.current?.abort(), [])
  async function upload(event: FormEvent) {
    event.preventDefault(); setActionError(''); setNotice('')
    if (!file || !/\.(pdf|txt)$/i.test(file.name) || file.size === 0 || file.size > 2 * 1024 * 1024) {
      setActionError('Choose a non-empty PDF or UTF-8 TXT file of at most 2 MiB.'); return
    }
    const controller = new AbortController(); request.current = controller; setUploading(true)
    try {
      const document = await api<KnowledgeDocument>(`/knowledge/documents?title=${encodeURIComponent(title.trim())}&filename=${encodeURIComponent(file.name)}`,
        { method: 'POST', body: file, headers: { 'Content-Type': 'application/octet-stream' }, signal: controller.signal }, 30000)
      if (controller.signal.aborted) return
      setTitle(''); setFile(null); if (fileInput.current) fileInput.current.value = ''
      setNotice(`${document.title} is ready: ${document.chunk_count} passage${document.chunk_count === 1 ? '' : 's'} added.`)
      setSearch(''); setSearchInput(''); setPage(1); refresh()
    } catch (err) { if (!controller.signal.aborted) setActionError(errorText(err)) }
    finally { if (!controller.signal.aborted) setUploading(false) }
  }
  async function change(document: KnowledgeDocument, remove = false) {
    setBusy(document.id); setActionError(''); setNotice('')
    try {
      if (remove) await api(`/knowledge/documents/${document.id}?version=${document.version}`, { method: 'DELETE' })
      else await api(`/knowledge/documents/${document.id}`, { method: 'PATCH', body: JSON.stringify({ is_active: !document.is_active, version: document.version }) })
      setConfirm(null); setNotice(remove ? 'Document removed. Its passages are no longer shown in chat history.' : document.is_active ? 'Document deactivated. Its passages are hidden from search and chat history.' : 'Document is active and available for questions.')
      if (remove && data?.items.length === 1 && page > 1) setPage(p => p - 1)
      refresh()
    } catch (err) { setActionError(errorText(err)) } finally { setBusy(null) }
  }
  return <>
    <div className="page-heading"><div><div className="eyebrow">GUIDANCE IN ONE PLACE</div><h1>Knowledge base</h1><p>Browse the documents behind your helpdesk answers.</p></div><a href="#chat" className="btn primary"><Icon name="chat" size={17}/>Ask helpdesk</a></div>
    {actionError && <Alert>{actionError}</Alert>}{notice && <div role="status" className="success-note"><Icon name="check" size={18}/>{notice}</div>}
    <div className={admin ? 'knowledge-layout' : ''}>
      <section className="panel knowledge-library" aria-label="Document library">
        <form className="filters" onSubmit={e => { e.preventDefault(); setPage(1); setSearch(searchInput.trim()) }}>
          <label className="search-label"><span className="sr-only">Search document titles</span><Icon name="search" size={17}/><input placeholder="Search document titles…" value={searchInput} maxLength={160} onChange={e => setSearchInput(e.target.value)}/></label>
          <button className="btn secondary small" type="submit">Search</button>
          {admin && <label className="inline-check"><input type="checkbox" checked={includeInactive} onChange={e => { setIncludeInactive(e.target.checked); setPage(1) }}/>Show inactive</label>}
        </form>
        {error && <div className="panel-pad"><Alert>{error}</Alert><button className="btn secondary" onClick={refresh}>Retry</button></div>}
        {loading ? <Loading/> : data?.items.length ? <div className="document-list">{data.items.map(doc => <article className="document-card" key={doc.id}>
          <div className="document-icon"><Icon name="file" size={23}/><small>{doc.media_type === 'application/pdf' ? 'PDF' : 'TXT'}</small></div>
          <div className="document-card-content"><div className="document-card-heading"><a href={`#knowledge/${doc.id}`}>{doc.title}</a><span className={'knowledge-status ' + (doc.is_active ? 'is-active' : '')}>{doc.is_active ? 'Active' : 'Inactive'}</span></div>
            <p className="document-meta">{doc.filename} · {doc.chunk_count} passage{doc.chunk_count === 1 ? '' : 's'}{doc.page_count > 0 && ` · ${doc.page_count} page${doc.page_count === 1 ? '' : 's'}`} · {Math.ceil(doc.byte_size / 1024)} KiB</p>
            <p className="document-date">Added {dateTime(doc.created_at)}</p>
            {doc.warnings.map(w => <p className="knowledge-warning" key={w}>{w}</p>)}
            <div className="document-actions"><a className="text-link" href={`#knowledge/${doc.id}`}>View passages<Icon name="arrow" size={13}/></a>
              {admin && <><button className="text-button" disabled={busy !== null} onClick={() => void change(doc)}>{busy === doc.id ? 'Saving…' : doc.is_active ? 'Deactivate' : 'Activate'}</button><button className="text-button danger-text" disabled={busy !== null} onClick={() => setConfirm(doc.id)}>Remove</button></>}
            </div>
            {confirm === doc.id && <div className="inline-confirm"><p>Remove this document and its passages? Earlier chat responses will no longer show these sources.</p><button className="btn secondary small" disabled={busy !== null} onClick={() => setConfirm(null)}>Cancel</button><button className="btn danger small" disabled={busy !== null} onClick={() => void change(doc, true)}>Confirm removal</button></div>}
          </div>
        </article>)}</div> : !error && <Empty title={search ? 'No matching documents' : 'No documents available'}>{admin ? 'Upload an approved guide to make it available to your team.' : 'Your administrator can add IT guides here. You can still create a support ticket.'}</Empty>}
        {data && <div className="pagination"><span>{data.total} document{data.total !== 1 ? 's' : ''}</span><div><button className="btn secondary small" disabled={page === 1 || loading} onClick={() => setPage(p => p - 1)}>Previous</button><span>{page}</span><button className="btn secondary small" disabled={page * data.page_size >= data.total || loading} onClick={() => setPage(p => p + 1)}>Next</button></div></div>}
      </section>
      {admin && <aside className="panel panel-pad knowledge-upload"><div className="upload-emblem"><Icon name="upload" size={25}/></div><h2>Add a document</h2><p>Active documents are available to every signed-in user. Upload guidance approved for sharing with your team.</p>
        <form className="stack compact" onSubmit={e => void upload(e)}>
          <label>Document title<input required minLength={3} maxLength={160} value={title} disabled={uploading} onChange={e => setTitle(e.target.value)} placeholder="e.g. Office Wi-Fi guide"/></label>
          <label><span id="knowledge-file-label">PDF or TXT file</span><input aria-labelledby="knowledge-file-label" aria-describedby="knowledge-file-help" ref={fileInput} type="file" accept=".pdf,.txt" required disabled={uploading} onChange={e => setFile(e.target.files?.[0] ?? null)}/><small id="knowledge-file-help">Up to 2 MiB. PDFs need selectable text; TXT files must use UTF-8.</small></label>
          <button className="btn primary wide" type="submit" disabled={uploading || !file || title.trim().length < 3}><Icon name="upload" size={17}/>{uploading ? 'Processing document…' : 'Upload document'}</button>
        </form>
        <div className="knowledge-upload-note"><Icon name="book" size={17}/><p>Answers show matching passages and link back to this library. Review the extracted text after uploading.</p></div>
      </aside>}
    </div>
  </>
}

export function KnowledgeDetail({ id, chunkId }: { id: number; chunkId: number | null }) {
  const { data, error, loading, refresh } = useResource<DocumentDetail>(`/knowledge/documents/${id}`)
  useEffect(() => { if (data && chunkId) document.getElementById('passage-' + chunkId)?.scrollIntoView({ block: 'center' }) }, [data, chunkId])
  if (loading) return <Loading/>
  return <><a className="back-link" href="#knowledge"><Icon name="back" size={14}/>Back to knowledge base</a>
    {error && <Alert>{error} <button className="text-button" onClick={refresh}>Retry</button></Alert>}
    {data && <><div className="page-heading"><div><div className="eyebrow">DOCUMENT SOURCE</div><h1>{data.title}</h1><p>{data.filename} · {data.chunk_count} passage{data.chunk_count === 1 ? '' : 's'}{data.page_count > 0 && ` · ${data.page_count} page${data.page_count === 1 ? '' : 's'}`}</p></div><a href="#chat" className="btn primary">Ask helpdesk</a></div>
      {!data.is_active && <div className="knowledge-warning standalone">This document is inactive. Only administrators can view it; it is excluded from answers.</div>}
      {data.warnings.map(w => <div className="knowledge-warning standalone" key={w}>{w}</div>)}
      <p className="source-intro">Extracted text is shown below. PDF layout and tables may not be preserved. Overlapping passages can repeat some text.</p>
      <div className="source-passages">{data.chunks.map(chunk => <article id={'passage-' + chunk.id} className={'panel panel-pad source-passage ' + (chunk.id === chunkId ? 'source-highlight' : '')} key={chunk.id}>
        <div className="source-passage-label"><Icon name="file" size={16}/>Passage {chunk.chunk_index}{chunk.page_number !== null && <span>Page {chunk.page_number}</span>}</div><p>{chunk.text}</p>
      </article>)}</div>
    </>}
  </>
}

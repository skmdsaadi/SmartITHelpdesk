import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, errorText } from './api'
import type { Health, User } from './types'
import { Alert, Icon } from './ui'

export default function Auth({ onLogin, initialError }: { onLogin: (user: User) => void; initialError: string }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(initialError)
  const [registration, setRegistration] = useState(false)
  useEffect(() => { api<Health>('/health').then(h => setRegistration(h.registration_enabled)).catch(() => {}) }, [])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    const values = { email: String(form.get('email')).trim(), password: String(form.get('password')) }
    try {
      const user = await api<User>('/auth/' + mode, {
        method: 'POST', body: JSON.stringify(mode === 'register' ? { ...values, name: String(form.get('name')).trim() } : values),
      })
      onLogin(user)
    } catch (reason) { setError(errorText(reason)) } finally { setBusy(false) }
  }
  return <div className="auth-layout">
    <section className="auth-story">
      <div className="brand"><div className="brand-icon"><Icon size={26}/></div><div>Smart IT Helpdesk<small>Your IT support workspace</small></div></div>
      <div className="auth-story-content">
        <span className="eyebrow light">Less downtime. More progress.</span>
        <h1>IT support,<br/>without the<br/><em>back and forth.</em></h1>
        <p>Report an issue, follow its progress, and keep every conversation in one place.</p>
        <div className="story-steps">
          {['Tell us what is happening', 'Follow your ticket’s progress', 'Keep a record of the resolution'].map((v, i) =>
            <div key={v}><span>{String(i + 1).padStart(2, '0')}</span>{v}</div>)}
        </div>
      </div>
      <p className="auth-story-footer"><Icon name="shield" size={17}/>Personal accounts. Clear ownership. Shared progress.</p>
    </section>
    <main className="auth-main">
      <div className="auth-form-wrap">
        <div className="auth-mobile-brand"><Icon/> Smart IT Helpdesk</div>
        <span className="eyebrow">Welcome to your workspace</span>
        <h2>{mode === 'login' ? 'Good to see you.' : 'Let’s get you started.'}</h2>
        <p className="muted">{mode === 'login' ? 'Sign in to manage your IT support requests.' : 'Create an employee account to request IT support.'}</p>
        {error && <Alert>{error}</Alert>}
        <form onSubmit={submit} className="stack" key={mode}>
          {mode === 'register' && <label>Full name<input name="name" autoComplete="name" minLength={2} maxLength={100} placeholder="Your full name" required disabled={busy}/></label>}
          <label>Email address<input name="email" type="email" autoComplete="username" maxLength={254} placeholder="you@company.com" required disabled={busy}/></label>
          <label>Password<input name="password" type="password" aria-label="Password" aria-describedby={mode === 'register' ? 'password-help' : undefined} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'register' ? 12 : 1} maxLength={128} required disabled={busy}/>
            {mode === 'register' && <small id="password-help">Use 12 or more characters. A memorable passphrase works well.</small>}
          </label>
          <button className="btn primary wide" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in to helpdesk' : 'Create employee account'}<Icon name="arrow" size={17}/></button>
        </form>
        {registration && <p className="auth-switch">{mode === 'login' ? 'Need an account? ' : 'Already have an account? '}
          <button className="text-button" disabled={busy} onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>{mode === 'login' ? 'Create account' : 'Sign in'}</button></p>}
        <div className="auth-help"><Icon name="headset"/><p>Need access help?<br/><span>Contact your IT administrator.</span></p></div>
      </div>
    </main>
  </div>
}

import type { AIResult, ModelReport } from './types'
import { useResource } from './api'
import { Alert, Icon, Loading } from './ui'

export function percent(value: number | null) { return value === null ? '—' : (value * 100).toFixed(1) + '%' }

export function AIResultCard({ result, onApply, disabled = false, selectedCategory }: {
  result: AIResult; onApply?: (category: NonNullable<AIResult['suggested_category']>) => void; disabled?: boolean; selectedCategory?: string
}) {
  const suggested = result.suggested_category
  return <div className={'ai-result ' + (suggested ? 'ai-matched' : 'ai-review')} role="status">
    <div className="ai-result-top"><span className="ai-label"><Icon name="sparkles" size={17}/>{suggested ? 'Suggested category' : 'Choose a category manually'}</span><span className="demo-tag">English demo</span></div>
    {suggested && <div className="ai-choice"><strong>{suggested}</strong><span>Model score {percent(result.model_score)}</span></div>}
    <p>{result.message}</p>
    {result.scores.length > 0 && <div className="ai-scores" aria-label="Top model scores">
      {!suggested && <small>Closest labels, for reference only</small>}
      {result.scores.slice(0, 3).map(item => <div className="ai-score-row" key={item.category}><span>{item.category}</span><div className="score-track"><span style={{ width: (item.score * 100) + '%' }}/></div><span>{percent(item.score)}</span></div>)}
    </div>}
    <div className="ai-result-bottom"><small>Trained on illustrative examples. Scores do not guarantee a correct category.</small>
      {suggested && onApply && <button type="button" className="btn secondary small" disabled={disabled || selectedCategory === suggested} onClick={() => onApply(suggested)}>{selectedCategory === suggested ? 'Selected: ' : 'Use '}{suggested}<Icon name="check" size={15}/></button>}
    </div>
  </div>
}

export default function AIInsights() {
  const { data, error, loading, refresh } = useResource<ModelReport>('/ai/model')
  const abbreviations: Record<string, string> = { Access: 'Acc', Email: 'Email', Hardware: 'HW', Network: 'Net', Printer: 'Print', Software: 'SW' }
  return <>
    <div className="page-heading"><div><span className="eyebrow">Understand the suggestion</span><h1>AI insights</h1><p>A transparent look at the category model and its evaluation.</p></div><button className="btn secondary" onClick={refresh}><Icon name="refresh" size={16}/>Refresh</button></div>
    {error && <Alert>{error} <button className="text-button" onClick={refresh}>Try again</button></Alert>}
    {loading && <Loading/>}
    {data && <>
      <section className="ai-banner"><div className="ai-banner-icon"><Icon name="sparkles" size={25}/></div><div><span className="demo-tag">SYNTHETIC DATA · ENGLISH</span><h2>A working model. A starting point.</h2><p>These results come from {data.examples} project-authored examples. They measure this demo dataset; real-office performance still needs independent evaluation.</p></div></section>
      <div className="stats-grid ai-metrics">
        <div className="stat-card"><div className="stat-top"><span>Held-out accuracy</span><Icon name="check" size={19}/></div><strong>{percent(data.test.accuracy)}</strong><small>All {data.test.count} test examples · before abstention</small></div>
        <div className="stat-card"><div className="stat-top"><span>Macro-F1</span><Icon name="grid" size={19}/></div><strong>{data.test.macro_f1.toFixed(3)}</strong><small>Each of the six categories weighted equally</small></div>
        <div className="stat-card"><div className="stat-top"><span>Suggestion coverage</span><Icon name="sparkles" size={19}/></div><strong>{percent(data.test.coverage)}</strong><small>{data.test.accepted} of {data.test.count} test examples suggested</small></div>
        <div className="stat-card"><div className="stat-top"><span>Accepted accuracy</span><Icon name="shield" size={19}/></div><strong>{percent(data.test.accepted_accuracy)}</strong><small>Correct among the {data.test.accepted} accepted suggestions</small></div>
      </div>
      <div className="ai-report-grid">
        <section className="panel panel-pad"><div className="ai-section-head"><h2>How the data is separated</h2><span className="count-pill">{data.groups} intent groups</span></div>
          <p className="ai-copy">Paraphrases of the same issue stay together. Training learns the model; validation selects the score threshold; testing measures the held-out result.</p>
          <div className="split-cards">{(['train', 'validation', 'test'] as const).map((name, index) => <div key={name}><span>0{index + 1} / {name === 'train' ? 'Training' : name === 'validation' ? 'Validation' : 'Test'}</span><strong>{data.split_counts[name]}</strong><small>{data.split_group_counts[name]} groups</small></div>)}</div>
          <div className="model-fact"><span>Model</span><strong>{data.algorithm}</strong></div>
          <div className="model-fact"><span>Suggestion threshold</span><strong>{data.threshold > 1 ? 'Manual review only' : percent(data.threshold)}</strong></div>
          <div className="model-fact"><span>Majority-class baseline</span><strong>{percent(data.majority_baseline_accuracy)}</strong></div>
          <div className="model-fact"><span>Unrelated test requests accepted</span><strong>{data.negative_controls.test.accepted} / {data.negative_controls.test.count}</strong></div>
          <p className="ai-footnote">The threshold also requires a score gap and a minimum match to training vocabulary. Small negative-control results cannot guarantee rejection of every unrelated request.</p>
        </section>
        <section className="panel panel-pad"><h2>Where predictions landed</h2><p className="ai-copy">Test-set confusion matrix before abstention. Diagonal cells are correct predictions.</p>
          <table className="confusion-table"><caption>Rows: actual category · Columns: predicted category</caption><thead><tr><th scope="col">Actual</th>{data.categories.map(c => <th scope="col" key={c}><abbr title={c}>{abbreviations[c] || c}</abbr></th>)}</tr></thead><tbody>{data.categories.map((c, i) => <tr key={c}><th scope="row">{c}</th>{data.test.confusion_matrix[i].map((value, j) => <td key={j} className={i === j ? 'matrix-correct' : value ? 'matrix-error' : ''}>{value}</td>)}</tr>)}</tbody></table>
          <div className="matrix-legend"><span><i/>Correct prediction</span><span><i/>Misclassification</span></div>
          <p className="ai-footnote">HW = Hardware · Net = Network · Print = Printer · SW = Software · Acc = Access</p>
          <div className="model-version"><span>MODEL VERSION</span><code>{data.model_version}</code></div>
        </section>
      </div>
      <section className="panel panel-pad ai-limitations"><h2>Use the result with context</h2><ul>{data.limitations.map(item => <li key={item}>{item}</li>)}</ul></section>
    </>}
  </>
}

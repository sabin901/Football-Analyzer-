'use strict';
let analystDraft = {},
  analystVideoTime = 0;
const analystKey = 'footlyzer.analysis.v1';
let ap = AnalystCore.empty(),
  analystMessage = '',
  analystFilter = '',
  analystAction = '',
  analystVideo = '',
  analystVideoName = '',
  analystTimer = null;
try {
  const saved = localStorage.getItem(analystKey);
  if (saved) ap = AnalystCore.backup(saved);
} catch {
  analystMessage =
    'Saved project could not be opened. Import a backup or start a new project. Existing device storage has not been overwritten.';
}
function analystRows() {
  return ap.events.filter(
    (e) =>
      (!analystFilter || wbFold(`${e.team} ${e.player}`).includes(wbFold(analystFilter))) &&
      (!analystAction || e.action === analystAction),
  );
}
function analystMap(rows) {
  const g = AnalystCore.grid(rows),
    maximum = Math.max(1, ...g.bins);
  if (!g.located)
    return empty('No coordinates in this selection. Evidence and video review still work.');
  return `<svg class="analyst-pitch" viewBox="0 0 720 480" role="img" aria-label="Imported action locations in a 12 by 8 grid. ${g.located} located events; ${g.missing} have no coordinates."><rect width="720" height="480" fill="#142e31"/>${g.bins.map((n, i) => `<rect x="${(i % 12) * 60 + 1}" y="${Math.floor(i / 12) * 60 + 1}" width="58" height="58" fill="${heatColor(n, maximum)}"><title>Cell ${i + 1}: ${n} events</title></rect>`).join('')}<g stroke="#edf6ef" fill="none" opacity=".8"><rect x="1" y="1" width="718" height="478"/><path d="M360 0V480M0 108H108V372H0M720 108H612V372H720"/><circle cx="360" cy="240" r="60"/></g></svg><p class="muted">${g.located} located / ${rows.length} selected events · Scale 0–${maximum} actions per cell · Attacking direction must be normalized in your CSV. No tracking or smoothing.</p><details><summary>Accessible grid counts</summary>${wbTable(
    ['Row', 'Cells, left to right'],
    Array.from(
      { length: 8 },
      (_, i) =>
        `<tr><td>${i + 1}</td><td>${g.bins.slice(i * 12, i * 12 + 12).join(' · ')}</td></tr>`,
    ),
    'Imported event grid',
  )}</details>`;
}
function analystView() {
  const rows = analystRows();
  return `<div class="analyst-intro"><div><span class="eyebrow">YOUR MATCH · YOUR EVIDENCE</span><h2>From an observation to a useful decision.</h2><p>Import event data, review your local video, and build a brief with traceable evidence.</p></div><span class="pill">On this device</span></div>
    <div class="notice">Files and notes stay in this browser. Nothing is uploaded. Save on device is optional and unencrypted; anyone using this browser profile can access saved notes. Keep a backup. <a href="docs/PRIVACY.html">Privacy & storage</a></div>
    ${ap.demo ? '<div class="notice"><strong>Synthetic demo.</strong> These events and observations describe no real team.</div>' : ''}
    <p id="analyst-status" class="analyst-status" role="status">${esc(analystMessage)}</p>
    <section class="panel"><div class="panel-head"><h2>1. Set the question</h2><button class="secondary" data-analyst="demo">Try a synthetic example</button></div><div class="panel-body"><div class="analyst-fields"><label for="analysis-title">Match / project title<input id="analysis-title" maxlength="160" value="${esc(ap.title)}"></label><label for="analysis-question">What decision should this analysis help?<textarea id="analysis-question" rows="2" maxlength="4000" placeholder="For example: which pressing triggers should we review?">${esc(ap.question)}</textarea></label></div><div class="analyst-actions"><label class="file-button">Import event CSV<input id="analysis-csv" type="file" accept=".csv,text/csv"></label><button class="secondary" data-analyst="template">Download CSV template</button><button class="secondary" data-analyst="save">Save on this device</button><button class="secondary" data-analyst="backup">Export project backup</button><label class="file-button secondary">Open project backup<input id="analysis-backup" type="file" accept=".json,application/json"></label><button class="secondary" data-analyst="new">New project</button><button class="secondary" data-analyst="forget">Remove device copy</button></div><p class="muted">${esc(ap.source.name)} · ${ap.events.length.toLocaleString()} events. Import a single match. Coordinates: 0–100, origin top left, attacking right for each team; empty coordinate pairs are allowed. Time: seconds from the start of each period. Only import material you may use. <a href="docs/ANALYST_GUIDE.html">Import and workflow guide</a></p>${ap.source.sha256 ? `<details><summary>Source fingerprint</summary><code class="source-hash">${esc(ap.source.sha256)}</code><p>SHA-256 of the imported file. Detects a changed file; does not prove accuracy or permissions.</p></details>` : ''}</div></section>
    <div class="analyst-columns"><section class="panel"><div class="panel-head"><h2>2. Review the evidence</h2><label class="file-button secondary">Attach local video<input id="analysis-video-file" type="file" accept="video/*"></label></div><div class="panel-body">${analystVideo ? `<video id="analysis-video" controls preload="metadata" src="${esc(analystVideo)}" aria-label="Local match video"></video><p class="muted">${esc(analystVideoName)} · Session only; reattach after reopening.</p>` : empty('Attach your own match video to jump from an event to its evidence. The file stays on your device.')}<details><summary>Synchronize video periods</summary><p>Video time in seconds where each period begins. Set these using your recording; halftime gaps vary.</p><div class="offset-fields">${ap.offsets.map((n, i) => `<label for="offset-${i}">Period ${i + 1}<input id="offset-${i}" data-offset="${i}" type="number" min="0" max="28800" step="0.1" value="${n}"></label>`).join('')}</div></details><div class="toolbar"><label for="analysis-filter">Team or player<input id="analysis-filter" type="search" value="${esc(analystFilter)}" placeholder="Filter imported evidence"></label>${wbSelect(
      'analysis-action',
      'Action',
      [
        ['', 'All actions'],
        ...Array.from(new Set(ap.events.map((e) => e.action)))
          .sort()
          .map((v) => [v, v]),
      ],
      analystAction,
    )}</div>${analystMap(rows)}${wbTable(
      ['Event', 'Team / player', 'Action', 'Time', 'Review'],
      rows
        .slice(0, 100)
        .map(
          (e) =>
            `<tr><td>${esc(e.id)}</td><td>${esc(e.team)}<small>${esc(e.player)}</small></td><td>${esc(e.action)}<small>${esc(e.outcome)}</small></td><td>P${e.period} ${Math.floor(e.second / 60)}:${String(Math.floor(e.second % 60)).padStart(2, '0')}</td><td><button class="secondary" data-evidence="${esc(e.id)}">Use event</button></td></tr>`,
        ),
      'Imported evidence',
    )}<p class="muted">Showing ${Math.min(rows.length, 100)} of ${rows.length} selected events. Filter to narrow the list; all events remain in exports.</p></div></section>
    <section class="panel"><div class="panel-head"><h2>3. Write the decision brief</h2></div><div class="panel-body"><form id="analysis-note" class="analyst-fields"><label for="note-evidence">Evidence IDs, comma separated<input id="note-evidence" maxlength="2000" placeholder="Select Use event, or enter IDs"></label><label for="note-observation">Observation · what happened?<textarea id="note-observation" rows="3" maxlength="4000" required></textarea></label><label for="note-interpretation">Interpretation · what might explain it?<textarea id="note-interpretation" rows="3" maxlength="4000" required></textarea></label><label for="note-decision">Recommendation · what should change?<textarea id="note-decision" rows="3" maxlength="4000" required></textarea></label><label for="note-limitation">Limitations and counterevidence<textarea id="note-limitation" rows="2" maxlength="4000" required></textarea></label>${wbSelect(
      'note-confidence',
      'Confidence · analyst judgement',
      [
        ['low', 'Low'],
        ['medium', 'Medium'],
        ['high', 'High'],
      ],
      'low',
    )}<button class="primary" type="submit">Add evidence note</button></form><div class="analyst-notes">${ap.notes.map((n, i) => `<article><span class="eyebrow">FINDING ${i + 1} · ${esc(n.confidence)} CONFIDENCE</span><h3>${esc(n.observation)}</h3><p><strong>Interpretation:</strong> ${esc(n.interpretation)}</p><p><strong>Recommendation:</strong> ${esc(n.decision)}</p><p><strong>Limits:</strong> ${esc(n.limitation)}</p><p class="muted">Evidence: ${n.evidence.map(esc).join(', ') || 'No event references; manual observation only'}</p><button class="secondary" data-remove-note="${i}">Remove note</button></article>`).join('')}</div><button class="primary" data-analyst="brief">Export decision brief ↓</button><p class="muted">Markdown brief includes evidence IDs, video times, source fingerprint and limitations. Analyst statements are not automatically verified.</p></div></section></div>
    <section class="panel"><div class="panel-head"><h2>Did this workflow help?</h2><span class="muted">Local feedback · not sent anywhere</span></div><div class="panel-body"><p>Measure a real task, then record whether the brief changed a decision. A demo is not a customer result.</p><div class="analyst-actions"><button class="secondary" data-analyst="timer">${analystTimer ? 'Stop task timer' : 'Start task timer'}</button><span>${Math.round(ap.feedback.seconds / 60)} recorded task minutes</span>${wbSelect('analysis-rating', 'Usefulness', [['', 'Not rated'], ...[1, 2, 3, 4, 5].map((n) => [n, `${n} / 5`])], ap.feedback.rating ?? '')}</div><label for="analysis-outcome">Outcome / what is still missing?<textarea id="analysis-outcome" rows="2" maxlength="2000">${esc(ap.feedback.outcome)}</textarea></label><button class="secondary" data-analyst="feedback">Export workflow feedback</button></div></section>`;
}
function analystMount() {
  for (const [id, value] of Object.entries(analystDraft)) {
    const field = document.getElementById(id);
    if (field) field.value = value;
  }
  const v = $('#analysis-video');
  if (v) {
    v.addEventListener('loadedmetadata', () => {
      if (analystVideoTime <= v.duration) v.currentTime = analystVideoTime;
    });
    v.addEventListener('error', () =>
      analystNotice(
        'This browser cannot play this video codec. Try a browser supported MP4 or WebM file.',
      ),
    );
  }
}
function analystNotice(message) {
  analystMessage = message;
  const el = $('#analyst-status');
  if (el) el.textContent = message;
}
function collectAnalyst() {
  if (!$('#analysis-title')) return;
  document
    .querySelectorAll('#analysis-note input,#analysis-note textarea,#analysis-note select')
    .forEach((el) => (analystDraft[el.id] = el.value));
  const video = $('#analysis-video');
  if (video) analystVideoTime = video.currentTime;
  ap.title = $('#analysis-title').value;
  ap.question = $('#analysis-question').value;
  ap.feedback.outcome = $('#analysis-outcome').value;
  ap.feedback.rating = $('#analysis-rating').value ? Number($('#analysis-rating').value) : null;
  ap.offsets = ap.offsets.map((_, i) => Number($(`#offset-${i}`).value));
  ap = AnalystCore.validate(ap);
}
function replaceProject(next) {
  if (analystVideo) URL.revokeObjectURL(analystVideo);
  analystVideo = '';
  analystVideoName = '';
  analystFilter = '';
  analystAction = '';
  analystTimer = null;
  analystDraft = {};
  analystVideoTime = 0;
  ap = next;
}
document.addEventListener('input', (e) => {
  if (view !== 'analyst') return;
  if (
    ['analysis-title', 'analysis-question', 'analysis-outcome', 'analysis-rating'].includes(
      e.target.id,
    ) ||
    e.target.hasAttribute('data-offset')
  ) {
    try {
      collectAnalyst();
    } catch (error) {
      analystNotice(error.message);
    }
  }
  if (e.target.id === 'analysis-filter') {
    collectAnalyst();
    analystFilter = e.target.value;
    const pos = e.target.selectionStart;
    render();
    $('#analysis-filter').focus();
    $('#analysis-filter').setSelectionRange(pos, pos);
  }
});
document.addEventListener('change', async (e) => {
  if (view !== 'analyst') return;
  try {
    collectAnalyst();
    if (e.target.id === 'analysis-action') {
      analystAction = e.target.value;
      render();
      return;
    }
    const file = e.target.files?.[0];
    if (!file) return;
    if (e.target.id === 'analysis-video-file') {
      if (analystVideo) URL.revokeObjectURL(analystVideo);
      analystVideo = URL.createObjectURL(file);
      analystVideoName = file.name;
      render();
      return;
    }
    if (!['analysis-csv', 'analysis-backup'].includes(e.target.id)) return;
    if (file.size > AnalystCore.LIMIT) throw new Error('Choose a file no larger than 5 MB.');
    const source = await file.text();
    const next = e.target.id === 'analysis-backup' ? AnalystCore.backup(source) : null;
    const rows = next ? null : AnalystCore.csv(source);
    if (
      (ap.events.length || ap.notes.length) &&
      !confirm('Replace the current project? Export a backup first if you need to keep it.')
    ) {
      e.target.value = '';
      return;
    }
    if (next) replaceProject(next);
    else {
      const hash = Array.from(
        new Uint8Array(await crypto.subtle.digest('SHA-256', await file.arrayBuffer())),
      )
        .map((n) => n.toString(16).padStart(2, '0'))
        .join('');
      const p = AnalystCore.empty();
      p.title = file.name.replace(/\.csv$/i, '');
      p.events = rows;
      p.source = {
        name: file.name,
        sha256: hash,
        license: 'User supplied; permissions not independently verified',
      };
      replaceProject(p);
    }
    analystMessage =
      'Imported and validated. Save on this device or export a backup to keep your work.';
    render();
  } catch (error) {
    analystNotice(error.message);
    e.target.value = '';
  }
});
document.addEventListener('click', (e) => {
  if (view !== 'analyst') return;
  const b = e.target.closest('button');
  if (!b) return;
  try {
    collectAnalyst();
    if (b.dataset.evidence) {
      const event = ap.events.find((x) => x.id === b.dataset.evidence);
      const field = $('#note-evidence');
      field.value = Array.from(
        new Set([
          ...field.value
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean),
          event.id,
        ]),
      ).join(', ');
      const v = $('#analysis-video');
      if (v) {
        const t = ap.offsets[event.period - 1] + event.second;
        if (!Number.isFinite(v.duration)) analystNotice('Wait for video metadata before seeking.');
        else if (t > v.duration)
          analystNotice('This event falls beyond the video. Check period offsets.');
        else {
          v.currentTime = t;
          v.pause();
          analystNotice(
            `Video positioned at ${Math.round(t)} seconds. Review before writing a finding.`,
          );
        }
      } else analystNotice(`Event ${event.id} added. Attach video to review the clip.`);
      return;
    }
    if (b.dataset.removeNote !== undefined) {
      if (confirm('Remove this evidence note?')) {
        ap.notes.splice(Number(b.dataset.removeNote), 1);
        render();
      }
      return;
    }
    switch (b.dataset.analyst) {
      case 'demo':
        if (
          (ap.events.length || ap.notes.length) &&
          !confirm(
            'Replace this project with the synthetic demo? Export a backup first to keep it.',
          )
        )
          return;
        replaceProject(AnalystCore.demo());
        analystMessage = 'Synthetic example opened. No real club conclusions.';
        render();
        break;
      case 'new':
        if (!confirm('Start a new project? Unsaved changes will be removed.')) return;
        replaceProject(AnalystCore.empty());
        analystMessage =
          'New project in memory. An older saved device copy remains until you save or remove it.';
        render();
        break;
      case 'forget':
        if (
          confirm(
            'Remove the saved copy from this browser? The current in-memory project remains open.',
          )
        ) {
          localStorage.removeItem(analystKey);
          analystNotice(
            'Device copy removed. Close or start a new project to clear the in-memory copy.',
          );
        }
        break;
      case 'template':
        downloadFile(
          'footlyzer-event-template.csv',
          toCsv([
            AnalystCore.headers,
            [
              'example-1',
              1,
              120,
              'Example team',
              'Example player',
              'Pass',
              35,
              40,
              60,
              45,
              'Complete',
            ],
          ]),
          'text/csv;charset=utf-8',
        );
        break;
      case 'save': {
        const value = JSON.stringify(ap);
        if (new TextEncoder().encode(value).length > AnalystCore.LIMIT)
          throw new Error('Project exceeds the 5 MB backup limit. Reduce the import first.');
        localStorage.setItem(analystKey, value);
        analystNotice(
          'Added notes saved. Unfinished note fields are not saved. Saved on this browser profile. Export a backup before clearing browser data.',
        );
        break;
      }
      case 'backup':
        downloadFile(
          'footlyzer-project.json',
          JSON.stringify(AnalystCore.validate(ap)),
          'application/json',
        );
        analystNotice('Project backup exported. Local video is not included.');
        break;
      case 'brief':
        downloadFile('footlyzer-decision-brief.md', AnalystCore.brief(ap));
        analystNotice('Decision brief exported. Review all claims before sharing.');
        break;
      case 'timer':
        if (analystTimer) {
          ap.feedback.seconds += (Date.now() - analystTimer) / 1000;
          analystTimer = null;
        } else analystTimer = Date.now();
        render();
        break;
      case 'feedback':
        downloadFile(
          'footlyzer-workflow-feedback.json',
          JSON.stringify(
            {
              schema: 1,
              demo: ap.demo,
              ...ap.feedback,
              notes: ap.notes.length,
              events: ap.events.length,
              note: 'Self reported workflow feedback; no claim of customer adoption.',
            },
            null,
            2,
          ),
          'application/json',
        );
        break;
    }
  } catch (error) {
    analystNotice(
      error.name === 'QuotaExceededError'
        ? 'Browser storage is full. Export a project backup instead.'
        : error.message,
    );
  }
});
document.addEventListener('submit', (e) => {
  if (e.target.id !== 'analysis-note') return;
  e.preventDefault();
  try {
    collectAnalyst();
    const n = {
      evidence: $('#note-evidence')
        .value.split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      observation: $('#note-observation').value,
      interpretation: $('#note-interpretation').value,
      decision: $('#note-decision').value,
      limitation: $('#note-limitation').value,
      confidence: $('#note-confidence').value,
    };
    ap = AnalystCore.validate({ ...ap, notes: [...ap.notes, n] });
    analystDraft = {};
    analystMessage = 'Evidence note added. Save or export to keep it.';
    render();
  } catch (error) {
    analystNotice(error.message);
  }
});

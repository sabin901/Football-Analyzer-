'use strict';
/* Pure, tested import/export boundary. Private evidence never goes to a server. */
const AnalystCore = (() => {
  const LIMIT = 5 * 1024 * 1024;
  const headers = [
    'id',
    'period',
    'second',
    'team',
    'player',
    'action',
    'x',
    'y',
    'end_x',
    'end_y',
    'outcome',
  ];
  function text(value, max = 4000) {
    if (
      typeof value !== 'string' ||
      value.length > max ||
      /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value)
    )
      throw new Error('Invalid text or text exceeds its limit.');
    return value.trim();
  }
  function csv(source) {
    if (typeof source !== 'string' || new TextEncoder().encode(source).length > LIMIT)
      throw new Error('CSV must be at most 5 MB.');
    source = source.replace(/^\ufeff/, '').replace(/\r\n/g, '\n');
    const rows = [];
    let row = [],
      cell = '',
      quoted = false,
      closed = false;
    for (let i = 0; i < source.length; i++) {
      const c = source[i];
      if (quoted) {
        if (c === '"' && source[i + 1] === '"') {
          cell += '"';
          i++;
        } else if (c === '"') {
          quoted = false;
          closed = true;
        } else cell += c;
      } else if (c === ',' || c === '\n') {
        row.push(cell);
        cell = '';
        closed = false;
        if (c === '\n') {
          if (row.some((v) => v !== '')) rows.push(row);
          row = [];
        }
      } else if (c === '"') {
        if (cell || closed) throw new Error('Malformed CSV quotation.');
        quoted = true;
      } else {
        if (closed) throw new Error('Unexpected text after a quoted CSV value.');
        cell += c;
      }
      if (rows.length > 20001) throw new Error('Use at most 20,000 events per project.');
    }
    if (quoted) throw new Error('CSV has an unclosed quote.');
    row.push(cell);
    if (row.some((v) => v !== '')) rows.push(row);
    if (rows.length < 2) throw new Error('CSV needs a header and at least one event.');
    const names = rows.shift().map((v) => v.trim());
    if (
      names.length !== headers.length ||
      new Set(names).size !== headers.length ||
      names.some((v) => !headers.includes(v))
    )
      throw new Error('Use the exact columns from the CSV template. Column order may change.');
    return events(
      rows.map((row, i) => {
        if (row.length !== names.length)
          throw new Error(`CSV record ${i + 2}: wrong number of fields.`);
        const item = Object.fromEntries(names.map((name, j) => [name, row[j].trim()]));
        for (const name of ['period', 'second', 'x', 'y', 'end_x', 'end_y']) {
          if (item[name] === '' && ['period', 'second'].includes(name))
            throw new Error(`CSV record ${i + 2}: ${name} is required.`);
          item[name] = item[name] === '' ? null : Number(item[name]);
        }
        return item;
      }),
    );
  }
  function events(rows) {
    if (!Array.isArray(rows) || rows.length > 20000) throw new Error('Invalid event collection.');
    const ids = new Set();
    return rows.map((r, i) => {
      if (!r || typeof r !== 'object') throw new Error(`Event ${i + 1}: invalid row.`);
      const event = Object.fromEntries(
        ['id', 'team', 'player', 'action', 'outcome'].map((k) => [k, text(r[k], 160)]),
      );
      if (!event.id || event.id.includes(',') || ids.has(event.id) || !event.team || !event.action)
        throw new Error(`Event ${i + 1}: unique ID, team and action are required.`);
      ids.add(event.id);
      if (
        !Number.isInteger(r.period) ||
        r.period < 1 ||
        r.period > 4 ||
        typeof r.second !== 'number' ||
        !Number.isFinite(r.second) ||
        r.second < 0 ||
        r.second > 3600
      )
        throw new Error(`Event ${event.id}: invalid period or second.`);
      event.period = r.period;
      event.second = r.second;
      for (const k of ['x', 'y', 'end_x', 'end_y']) {
        if (
          r[k] !== null &&
          (typeof r[k] !== 'number' || !Number.isFinite(r[k]) || r[k] < 0 || r[k] > 100)
        )
          throw new Error(`Event ${event.id}: coordinates must be 0–100 or empty.`);
        event[k] = r[k];
      }
      if (
        (event.x === null) !== (event.y === null) ||
        (event.end_x === null) !== (event.end_y === null)
      )
        throw new Error(`Event ${event.id}: supply both coordinates of a point.`);
      return event;
    });
  }
  function empty() {
    return {
      format: 'footlyzer-analysis',
      version: 1,
      title: 'Untitled match analysis',
      question: '',
      created_at: new Date().toISOString(),
      source: {
        name: 'No CSV imported',
        sha256: '',
        license: 'User supplied; permissions not independently verified',
      },
      demo: false,
      events: [],
      notes: [],
      offsets: [0, 2700, 5400, 6300],
      feedback: { seconds: 0, rating: null, outcome: '' },
    };
  }
  function validate(raw) {
    if (!raw || raw.format !== 'footlyzer-analysis' || raw.version !== 1)
      throw new Error('Unsupported project format or version.');
    const p = empty();
    p.title = text(raw.title, 160);
    p.question = text(raw.question);
    p.created_at = text(raw.created_at, 40);
    if (!Number.isFinite(Date.parse(p.created_at)))
      throw new Error('Invalid project creation date.');
    p.events = events(raw.events);
    p.demo = raw.demo === true;
    p.source = {
      name: text(raw.source?.name, 200),
      sha256: text(raw.source?.sha256, 64),
      license: text(raw.source?.license, 500),
    };
    if (p.source.sha256 && !/^[a-f0-9]{64}$/.test(p.source.sha256))
      throw new Error('Invalid source fingerprint.');
    if (
      !Array.isArray(raw.offsets) ||
      raw.offsets.length !== 4 ||
      raw.offsets.some((n) => typeof n !== 'number' || !Number.isFinite(n) || n < 0 || n > 28800)
    )
      throw new Error('Invalid video offsets.');
    p.offsets = [...raw.offsets];
    if (!Array.isArray(raw.notes) || raw.notes.length > 200)
      throw new Error('Use at most 200 evidence notes.');
    const ids = new Set(p.events.map((e) => e.id));
    p.notes = raw.notes.map((n) => {
      if (
        !Array.isArray(n.evidence) ||
        n.evidence.length > 100 ||
        n.evidence.some((id) => !ids.has(id))
      )
        throw new Error('A note refers to missing evidence.');
      if (!['low', 'medium', 'high'].includes(n.confidence)) throw new Error('Invalid confidence.');
      return {
        evidence: [...new Set(n.evidence)],
        observation: text(n.observation),
        interpretation: text(n.interpretation),
        decision: text(n.decision),
        limitation: text(n.limitation),
        confidence: n.confidence,
      };
    });
    const f = raw.feedback;
    if (
      !f ||
      typeof f.seconds !== 'number' ||
      !Number.isFinite(f.seconds) ||
      f.seconds < 0 ||
      f.seconds > 1e7 ||
      (f.rating !== null && ![1, 2, 3, 4, 5].includes(f.rating))
    )
      throw new Error('Invalid workflow feedback.');
    p.feedback = { seconds: f.seconds, rating: f.rating, outcome: text(f.outcome, 2000) };
    if (new TextEncoder().encode(JSON.stringify(p)).length > LIMIT)
      throw new Error('Project exceeds 5 MB. Reduce the import or evidence notes.');
    return p;
  }
  function backup(source) {
    if (new TextEncoder().encode(source).length > LIMIT)
      throw new Error('Project backup exceeds 5 MB.');
    return validate(JSON.parse(source));
  }
  function grid(rows) {
    const bins = Array(96).fill(0);
    let located = 0;
    for (const e of rows)
      if (e.x !== null && e.y !== null) {
        bins[Math.min(7, Math.floor(e.y * 0.08)) * 12 + Math.min(11, Math.floor(e.x * 0.12))]++;
        located++;
      }
    return { bins, located, missing: rows.length - located };
  }
  const md = (value) => String(value).replace(/([\\`*_{}\[\]()#+!|<>])/g, '\\$1');
  function brief(raw) {
    const p = validate(raw);
    let out = `# ${md(p.title)}\n\n${p.demo ? '**SYNTHETIC DEMONSTRATION — not evidence about a real team.**\n\n' : ''}Question: ${md(p.question || 'Not specified')}\n\nSource: ${md(p.source.name)}\nSHA-256: ${p.source.sha256 || 'Not recorded'}\nPermissions: ${md(p.source.license)}\nEvents: ${p.events.length}. Local video is not included.\n\n`;
    for (const [i, n] of p.notes.entries()) {
      out += `## Finding ${i + 1}\n\nObservation: ${md(n.observation)}\n\nInterpretation: ${md(n.interpretation)}\n\nRecommendation: ${md(n.decision)}\n\nConfidence: ${n.confidence} (analyst judgement, not a probability).\n\nLimitation / counterevidence: ${md(n.limitation)}\n\n`;
      out +=
        n.evidence
          .map((id) => {
            const e = p.events.find((e) => e.id === id);
            return `- Event ${md(id)}: period ${e.period}, ${e.second}s; ${md(e.team)} / ${md(e.player)} / ${md(e.action)}; video ${p.offsets[e.period - 1] + e.second}s.`;
          })
          .join('\n') + '\n\n';
    }
    return (
      out +
      '## Review limits\n\nUser supplied events and observations are not independently verified. Action locations are not continuous player tracking. Video offsets require manual synchronization. Check the source, sample, score state and alternative explanations before acting.\n'
    );
  }
  function demo() {
    const p = empty();
    p.demo = true;
    p.title = 'Demo · defending the right channel';
    p.question = 'Which observations deserve a second look on video?';
    p.source.name = 'Synthetic demonstration generated in this browser';
    p.source.license = 'Fictional sample; freely reusable';
    p.events = Array.from({ length: 18 }, (_, i) => ({
      id: `demo-${i + 1}`,
      period: i < 9 ? 1 : 2,
      second: 120 + i * 73,
      team: i % 3 ? 'Sample A' : 'Sample B',
      player: `Player ${(i % 4) + 1}`,
      action: i % 4 ? 'Pass' : 'Shot',
      x: 30 + ((i * 7) % 65),
      y: 10 + ((i * 13) % 80),
      end_x: null,
      end_y: null,
      outcome: i % 4 ? 'Complete' : 'Off target',
    }));
    p.notes = [
      {
        evidence: ['demo-1', 'demo-5'],
        observation: 'Two fictional shot events are selected to demonstrate evidence references.',
        interpretation: 'No tactical conclusion can be drawn from synthetic events.',
        decision: 'Replace this example with your own permitted match data and video.',
        limitation: 'This is a product demonstration, not a club case study.',
        confidence: 'low',
      },
    ];
    return p;
  }
  return { LIMIT, headers, csv, events, empty, validate, backup, grid, brief, demo };
})();
if (typeof module !== 'undefined') module.exports = AnalystCore;

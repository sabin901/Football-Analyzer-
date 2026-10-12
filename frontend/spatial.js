'use strict';
const hs={set:'',scope:'season',match:'',team:'',player:'',compare:'',action:'all',period:'all',measure:'share'};
let heatExport=null;
function xgFlow(m){
  const end=Math.max(90,...m.shots.map(s=>s.minute));
  const totals=[m.home_id,m.away_id].map(id=>m.shots.filter(s=>s.team_id===id).reduce((n,s)=>n+s.xg,0));
  const ymax=Math.max(1,Math.ceil(Math.max(...totals)*2)/2);
  const px=min=>48+min/end*520,py=v=>222-v/ymax*184;
  const paths=[m.home_id,m.away_id].map((id,i)=>{
    let sum=0,path='M48 222',goals='';
    for(const s of m.shots.filter(s=>s.team_id===id).sort((a,b)=>a.minute-b.minute)){
      sum+=s.xg;path+=`H${px(s.minute)}V${py(sum)}`;
      if(s.goal)goals+=`<circle cx="${px(s.minute)}" cy="${py(sum)}" r="4" fill="${i?'#7c54a8':'#256345'}" stroke="white"><title>${esc(s.player)} · ${s.minute} minutes · goal</title></circle>`;
    }
    return `<path d="${path}H568" fill="none" stroke="${i?'#7c54a8':'#256345'}" stroke-width="2.5" ${i?'stroke-dasharray="7 4"':''}/>${goals}`;
  }).join('');
  return wbPanel('Chance creation through the match',`<div class="xg-legend"><span><i class="xg-key"></i>${esc(m.home)} · ${totals[0].toFixed(2)} xG</span><span><i class="xg-key away"></i>${esc(m.away)} · ${totals[1].toFixed(2)} xG</span></div><svg class="xg-flow" viewBox="0 0 610 267" role="img" aria-label="Cumulative expected goals for ${esc(m.home)} and ${esc(m.away)}. Goal markers are circles. Shot table above provides the underlying values.">${[0,.5,1].map(f=>`<path d="M48 ${py(f*ymax)}H568" stroke="#dbe3d5"/><text x="34" y="${py(f*ymax)+4}" text-anchor="end" fill="#657169" font-size="11">${(f*ymax).toFixed(1)}</text>`).join('')}${paths}${[0,45,end].map(t=>`<text x="${px(t)}" y="245" text-anchor="middle" fill="#657169" font-size="11">${t}′</text>`).join('')}<text x="48" y="20" fill="#657169" font-size="11">Cumulative xG</text></svg><p class="muted">Provider shot xG accumulated by recorded minute. Penalties included. Dots mark goals from shots; own goals are not shot xG. This describes chance creation, not momentum, possession or the deserved winner.</p>`);
}
const heatColors=['#102d29','#17483f','#236553','#378668','#64a47b','#a6c783','#f5e6a1'];
function heatGrid(d,team,player=''){
  const bins=Array(d.cols*d.rows).fill(0);
  for(const [i,period,kind,cell,n] of d.cells){
    const p=d.players[i];
    if(String(p.team_id)!==String(team)||(player&&String(p.id)!==String(player)))continue;
    if(hs.action!=='all'&&kind!==Number(hs.action))continue;
    if(hs.period!=='all'&&period!==Number(hs.period))continue;
    bins[cell]+=n;
  }
  const total=bins.reduce((a,b)=>a+b,0);
  return {bins,total,values:bins.map(n=>hs.measure==='share'?(total?100*n/total:0):n)};
}
function heatSvg(grid,maximum,title,subtitle){
  const value=v=>hs.measure==='share'?`${v.toFixed(1)}%`:String(v);
  const cells=grid.values.map((v,i)=>`<rect x="${10+(i%12)*10}" y="${24+Math.floor(i/12)*10}" width="10" height="10" fill="${heatColors[v?Math.max(1,Math.ceil(v/maximum*6)):0]}"><title>x ${i%12*10} to ${i%12*10+10}, y ${Math.floor(i/12)*10} to ${Math.floor(i/12)*10+10}: ${grid.bins[i]} events, ${value(v)}</title></rect>`).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" class="heat-pitch" viewBox="0 0 140 137" role="img" aria-label="${esc(title)} activity heatmap. ${grid.total} located events. Both teams attack right. Numeric grid available below."><rect width="140" height="137" rx="4" fill="#10231f"/><text x="10" y="11" fill="#eef5e9" font-family="sans-serif" font-size="4.8" font-weight="700">${esc(title)}</text><text x="10" y="18" fill="#b8d0c3" font-family="sans-serif" font-size="2.8">${esc(subtitle)}</text>${cells}<g fill="none" stroke="#edf7ed" stroke-opacity=".65" stroke-width=".35"><rect x="10" y="24" width="120" height="80"/><path d="M70 24V104M10 42H28V86H10M130 42H112V86H130M10 54H16V74H10M130 54H124V74H130"/><circle cx="70" cy="64" r="10"/></g><text x="10" y="113" fill="#b8d0c3" font-family="sans-serif" font-size="3">ATTACK DIRECTION →</text>${heatColors.map((c,i)=>`<rect x="${86+i*6}" y="109" width="6" height="3" fill="${c}"/>`).join('')}<text x="86" y="117" fill="#b8d0c3" font-family="sans-serif" font-size="2.8">0</text><text x="128" y="117" text-anchor="end" fill="#b8d0c3" font-family="sans-serif" font-size="2.8">${value(maximum)}</text><text x="10" y="125" fill="#e4eedf" font-family="sans-serif" font-size="3">${grid.total.toLocaleString()} events · ${hs.measure==='share'?'Share within this selection':'Event count'} · 12 × 8 grid</text><text x="10" y="132" fill="#b8d0c3" font-family="sans-serif" font-size="2.5">Footlyzer · StatsBomb Open Data · Historical event activity</text></svg>`;
}
function heatmapView(){
  heatExport=null;
  const manifest=wbLoad('spatial_manifest.json');
  if(!manifest)return empty('Loading the spatial archive…');if(manifest.error)return empty('Spatial archive unavailable. Refresh to retry.');
  const sets=manifest.sets.filter(s=>s.league===leagueId&&s.imported_matches);
  if(!sets.length)return empty('No spatial data imported for this league.');
  if(!sets.some(s=>s.key===hs.set))hs.set=sets.find(s=>s.imported_matches>=300)?.key||sets[0].key;
  const season=wbLoad(`spatial_${hs.set}.json`),events=wbLoad(`events_${hs.set}.json`);
  if(!season||!events)return empty('Loading historical locations…');
  if(season.error||events.error)return empty('This spatial dataset is unavailable. Refresh to retry.');
  const matches=events.matches.filter(m=>season.match_ids.includes(m.id));
  if(!matches.some(m=>String(m.id)===hs.match))hs.match=String(matches.at(-1)?.id||'');
  const d=hs.scope==='match'?wbLoad(`spatial_matches/${hs.match}.json`):season;
  if(!d)return empty('Loading match locations…');if(d.error)return empty('Match locations unavailable. Choose another match or refresh.');
  const teams=[...new Map(d.players.map(p=>[String(p.team_id),p.team])).entries()].sort((a,b)=>a[1].localeCompare(b[1]));
  if(!teams.some(([id])=>id===hs.team)){hs.team=teams[0]?.[0]||'';hs.player=''}
  if(!teams.some(([id])=>id===hs.compare)||hs.compare===hs.team)hs.compare='';
  const players=d.players.filter(p=>String(p.team_id)===hs.team).sort((a,b)=>a.name.localeCompare(b.name));
  if(!players.some(p=>String(p.id)===hs.player))hs.player='';
  const p=players.find(p=>String(p.id)===hs.player),name=p?.name||teams.find(([id])=>id===hs.team)?.[1]||'Team';
  const grid=heatGrid(d,hs.team,hs.player),other=hs.compare?heatGrid(d,hs.compare):null;
  const maximum=Math.max(0,...grid.values,...(other?.values||[]));
  const currentMatch=matches.find(m=>String(m.id)===hs.match);
  const context=hs.scope==='match'?`${currentMatch.date} · ${currentMatch.home} vs ${currentMatch.away}`:`${season.competition} ${season.season} · imported season sample`;
  const action=hs.action==='all'?'All located actions':d.actions[Number(hs.action)];
  const period=hs.period==='all'?'All periods':`Period ${hs.period}`;
  const subtitle=`${season.season} · ${action} · ${period}`;
  const svg=heatSvg(grid,maximum,name,subtitle);
  heatExport={d,grid,other,maximum,name,context,action,period,svg};
  const third=[0,0,0];grid.bins.forEach((n,i)=>third[Math.floor(i%12/4)]+=n);
  const playerMatches=hs.scope==='match'?Number(grid.total>0):(p?.matches??matches.filter(m=>String(m.home_id)===hs.team||String(m.away_id)===hs.team).length);
  return `<section class="spatial-intro"><div><p class="eyebrow">SPATIAL INTELLIGENCE</p><h2>Where does the game happen?</h2><p>Explore the spaces teams use and the actions players make.</p></div><span class="spatial-tag">${icon('scan-line')} Historical event data</span></section><div class="toolbar heat-source">${wbSelect('heat-set','Historical dataset',sets.map(s=>[s.key,`${s.competition} ${s.season} · ${s.imported_matches} matches`]),hs.set)}${wbSelect('heat-scope','Sample',[['season','Imported season sample'],['match','Single match']],hs.scope)}${hs.scope==='match'?wbSelect('heat-match','Match',[...matches].reverse().map(m=>[m.id,`${m.date} · ${m.home} vs ${m.away}`]),hs.match):''}</div><div class="heat-context"><span class="small-dot"></span>${esc(context)}<span>${season.imported_matches} / ${season.available_matches} archive matches mapped</span></div><section class="panel"><div class="toolbar heat-filters">${wbSelect('heat-team','Team',teams,hs.team)}${wbSelect('heat-player','Player',[['','Whole team'],...players.map(p=>[p.id,p.name])],hs.player)}${wbSelect('heat-action','Action',[['all','All actions'],...d.actions.map((n,i)=>[i,n])],hs.action)}${wbSelect('heat-period','Period',[['all','All periods'],[1,'First half'],[2,'Second half'],[3,'Extra time first'],[4,'Extra time second']],hs.period)}${wbSelect('heat-measure','Colour scale',[['share','Event share %'],['count','Event counts']],hs.measure)}${wbSelect('heat-compare','Compare with team',[['','No comparison'],...teams.filter(([id])=>id!==hs.team)],hs.compare)}</div><div class="panel-body"><div class="heat-maps ${other?'two-maps':''}"><div><div class="heat-map-caption"><h3>${esc(name)}</h3><p>${esc(action)} · ${period}</p></div>${svg}<p class="heat-scale-note">Attack right · Colour: 0 to ${hs.measure==='share'?maximum.toFixed(1)+'%':maximum} per cell</p>${grid.total?'':empty('No located events match this selection. Try another action or period.')}</div>${other?`<div><div class="heat-map-caption"><h3>${esc(teams.find(([id])=>id===hs.compare)[1])}</h3><p>Whole team · ${esc(action)} · ${period}</p></div>${heatSvg(other,maximum,teams.find(([id])=>id===hs.compare)[1],subtitle)}<p class="heat-scale-note">Attack right · Colour: 0 to ${hs.measure==='share'?maximum.toFixed(1)+'%':maximum} per cell</p>${other.total?'':empty('No located events in this comparison.')}</div>`:''}</div><div class="heat-summary"><div><strong>${grid.total.toLocaleString()}</strong><span>Selected events</span></div><div><strong>${playerMatches}</strong><span>${p?'Matches with any located action':'Team matches in sample'}</span></div><div><strong>${grid.total?Math.round(100*third[2]/grid.total)+'%':'—'}</strong><span>In attacking third</span></div><div><strong>${grid.total?Math.round(100*third[0]/grid.total)+'%':'—'}</strong><span>In defensive third</span></div></div><div class="heat-actions"><button class="secondary" data-heat-csv>${icon('download')} Export grid CSV</button><button class="secondary" data-heat-svg>${icon('image')} Save selected map SVG</button><a href="docs/SPATIAL_METHOD.html">Method and coordinate guide ${icon('arrow-up-right')}</a></div><p class="muted">${other?'Both maps share the same colour maximum. ':''}${hs.measure==='share'?'Each map sums to 100% when events exist. This compares distributions, not work rate.':'Counts depend on playing time, possession and sample size.'} A brighter cell means more recorded activity, not better performance.</p><details><summary>Accessible numeric grid for ${esc(name)}</summary>${wbTable(['Y / X',...Array.from({length:12},(_,i)=>`${i*10} to ${i*10+10}`)],Array.from({length:8},(_,y)=>`<tr><th scope="row">${y*10} to ${y*10+10}</th>${grid.values.slice(y*12,y*12+12).map(v=>`<td>${hs.measure==='share'?v.toFixed(2)+'%':v}</td>`).join('')}</tr>`),'Selected heatmap numeric grid')}</details><details><summary>Coverage and interpretation</summary><p>StatsBomb Open Data. ${season.first_date} to ${season.last_date}. ${season.errors.length} spatial import failures. The full ${hs.scope==='match'?'match':'dataset'} contains ${d.located.toLocaleString()} located player events, ${d.missing_location.toLocaleString()} events without locations, ${d.invalid_location} invalid locations excluded, and ${d.edge_clamped} boundary locations clamped for binning. These quality counts cover the whole sample, before filters.</p><p>Locations are action start positions on a 120 × 80 provider pitch. Both teams attack right; no half is rotated again. Defensive actions include recoveries, interceptions, duels, blocks, clearances and dribbled past events. All actions also include receipts and other located events, so they are not unique touches. Missing coordinates never become zero coordinates.</p></details></div></section><div class="notice"><strong>Event activity, not player tracking.</strong> These maps show recorded historical actions, not distance covered, off ball positioning or time spent in a zone. Current free match summaries have no reliable event locations. Some archive seasons contain only selected clubs.</div><div class="spatial-credit">Event data provided by <img src="https://raw.githubusercontent.com/statsbomb/open-data/master/img/SB%20-%20Icon%20Lockup%20-%20Colour%20positive.png" alt="StatsBomb" width="125" loading="lazy"></div>`;
}
document.addEventListener('change',e=>{
  if(!e.target.id.startsWith('heat-'))return;
  const key=e.target.id.slice(5);if(!(key in hs))return;
  hs[key]=e.target.value;
  if(['set','scope','match','team'].includes(key)){hs.player='';hs.compare=''}
  render();document.getElementById(e.target.id)?.focus();
});
document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b||!heatExport)return;
  const h=heatExport;
  if(b.hasAttribute('data-heat-csv')){
    const quote=v=>'"'+String(v).replace(/^[=+@\-]/,"'$&").replaceAll('"','""')+'"';
    const rows=[['dataset','sample','selection','team_id','player_id','action','period','x_min','x_max','y_min','y_max','count','share_pct','source']];
    h.grid.bins.forEach((n,i)=>rows.push([hs.set,h.context,h.name,hs.team,hs.player||'all',h.action,h.period,i%12*10,i%12*10+10,Math.floor(i/12)*10,Math.floor(i/12)*10+10,n,h.grid.total?(100*n/h.grid.total).toFixed(4):0,'StatsBomb Open Data']));
    wbDownload(`footlyzer-heatmap-${hs.set}.csv`,'\ufeff'+rows.map(r=>r.map(quote).join(',')).join('\r\n'),'text/csv;charset=utf-8');
  }
  if(b.hasAttribute('data-heat-svg')){
    const metadata=`<metadata>${esc(JSON.stringify({dataset:hs.set,sample:h.context,team:hs.team,player:hs.player||'all',action:h.action,period:h.period,measure:hs.measure,source:'StatsBomb Open Data',method:'12 by 8 event start bins, both teams attack right',limitation:'Historical event activity, not continuous tracking'}))}</metadata>`;
    wbDownload(`footlyzer-heatmap-${hs.set}.svg`,h.svg.replace(/(<svg[^>]*>)/,`$1${metadata}`),'image/svg+xml');
  }
});

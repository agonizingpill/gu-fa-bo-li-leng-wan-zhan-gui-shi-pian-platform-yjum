import {awaitCompute, request} from './api.js';
import {el, display} from './dom.js';
import {COMPUTE_STATES, evidence} from './store.js';
import {status} from './widgets.js';

const fallback = field => field.kind === 'token' ? evidence.get() : field.initial;
function input(field) {
  if (field.kind === 'bool') return el('select', {name:field.name},
    el('option',{value:'true', selected:fallback(field) === true ? '' : undefined},'是'),
    el('option',{value:'false', selected:fallback(field) === false ? '' : undefined},'否'));
  if (field.kind === 'json') return el('textarea', {name:field.name, required:''}, JSON.stringify(fallback(field), null, 2));
  const numeric = ['int','float'].includes(field.kind);
  return el('input',{name:field.name, required:'', type:numeric ? 'number' : 'text',
    step:field.kind === 'float' ? 'any' : undefined, value:fallback(field) ?? ''});
}
function parse(form, fields) {
  const data = new FormData(form);
  return Object.fromEntries(fields.map(field => {
    const raw = data.get(field.name);
    const convert = ['int','float'].includes(field.kind) ? Number :
      ['bool','json'].includes(field.kind) ? JSON.parse : String;
    return [field.name, convert(raw)];
  }));
}

const SIDE_TEXT = {train:'训练', holdout:'留验', excluded:'排除', quarantined:'隔离'};
function sideText(row) {
  return row.side_label || row.label || SIDE_TEXT[row.side || row.split] || row.side || row.split || '—';
}

export function plateReportView(payload) {
  const source = payload?.result || payload || {};
  const report = source.plate_report || source.allocation || source;
  const plates = source.plates || source.groups || report?.plates || report?.groups || [];
  if (!Array.isArray(plates) || !plates.length) return null;

  const counts = report.counts || source.counts || {};
  const caption = counts && Object.keys(counts).length
    ? `母板 ${counts.plates ?? plates.length} · 训练 ${counts.train_plates ?? ''} · 留验 ${counts.holdout_plates ?? ''} · 排除 ${counts.excluded_plates ?? plates.filter(x => x.excluded).length}`
    : `母板 ${plates.length}`;

  return el('div', {class:'plate-report', id:'plate-report', 'aria-label':'母板分组追溯'},
    el('h4', {}, '当时母板分组'),
    el('p', {class:'report-counts'}, caption),
    el('div', {class:'scroll report-scroll'}, el('table', {},
      el('thead', {}, el('tr', {},
        el('th', {scope:'col'}, '母板/保留号'),
        el('th', {scope:'col'}, '合并旧号'),
        el('th', {scope:'col'}, '试片'),
        el('th', {scope:'col'}, '去向'),
        el('th', {scope:'col'}, '原因'))),
      el('tbody', {}, plates.map(row => el('tr', {class: row.excluded ? 'excluded' : ''},
        el('td', {}, display(row.plate || row.canonical || row.code)),
        el('td', {}, display((row.codes || row.aliases || []).filter(code => code !== (row.plate || row.canonical)))),
        el('td', {}, display(row.coupon_codes || row.coupons)),
        el('td', {}, sideText(row)),
        el('td', {}, row.detail || row.explanation || row.reason || '—')))))));
}

export function actionForm(action, refresh) {
  const notice = status('');
  const reportBox = el('div', {class:'report-slot'});
  const button = el('button', {type:'submit'}, action.label);
  const form = el('form', {class:'action', id:action.name},
    el('h3',{},action.label), el('p',{},action.help),
    el('div',{class:'fields'},action.fields.map(field => el('label',{},
      el('span',{},field.label), input(field)))),
    button, notice, reportBox);
  form.addEventListener('submit',async event => {
    event.preventDefault();
    button.disabled = true;
    notice.className = 'status';
    reportBox.replaceChildren();
    try {
      const data = await request(action.path, parse(form, action.fields));
      if (data.token && data.status === 'queued') {
        evidence.save(data.token);
        const result = await awaitCompute(data.token, current => {
          notice.textContent = COMPUTE_STATES[current.status] || current.status;
        });
        if (result.status === 'rejected') throw new Error(result.detail);
        const metric = result.result || {};
        notice.textContent = `任务 ${data.token} · 预测 ${display(metric.prediction)} · MAE ${display(metric.mae)} · 留验 ${display(metric.held_out)}`;
        const report = plateReportView(metric || result);
        if (report) reportBox.replaceChildren(report);
      } else {
        notice.textContent = action.success + ' · ' + display(data.code ?? data.plate ?? data.status);
        if (action.report || data.plates || data.groups || data.plate_report) {
          const report = plateReportView(data);
          if (report) reportBox.replaceChildren(report);
        }
      }
      notice.classList.add('ok');
      await refresh();
    } catch (error) {
      notice.textContent = error.message;
      notice.classList.add('error');
    } finally { button.disabled = false; }
  });
  return form;
}

(() => {
  'use strict';
  const list = document.getElementById('reports');
  const status = document.getElementById('list-status');
  function showStatus(message) {
    status.textContent = message;
    status.hidden = false;
  }
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function validReport(report) {
    return report && ['title', 'institution', 'category', 'date', 'summary', 'region'].every(key => typeof report[key] === 'string')
      && /^\d{4}-\d{2}-\d{2}$/.test(report.date)
      && typeof report.url === 'string'
      && /^reports\/\d{4}\/[a-z0-9]+(?:-[a-z0-9]+)*\/index\.html$/.test(report.url)
      && Array.isArray(report.tags) && report.tags.every(tag => typeof tag === 'string');
  }
  function reportRow(report) {
    const row = element('li', 'report');
    const link = element('a', 'report-link');
    link.href = report.url;
    const body = element('div', 'report-text');
    body.append(element('h2', '', report.title));
    const meta = element('div', 'report-meta');
    const date = element('time', '', report.date.replaceAll('-', '.'));
    date.dateTime = report.date;
    meta.append(element('span', '', report.institution), element('span', '', report.category), date);
    body.append(meta, element('p', 'summary', report.summary));
    const tags = element('div', 'tags');
    report.tags.forEach(tag => tags.append(element('span', 'tag', tag)));
    body.append(tags);
    const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    arrow.setAttribute('class', 'arrow'); arrow.setAttribute('viewBox', '0 0 24 24'); arrow.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'm9 5 7 7-7 7'); arrow.append(path);
    link.append(body, arrow); row.append(link);
    return row;
  }
  async function load() {
    showStatus('正在加载研报…');
    try {
      const response = await fetch('reports.json', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const reports = await response.json();
      if (!Array.isArray(reports) || !reports.every(validReport)) throw new Error('Invalid report list');
      reports.sort((a, b) => b.date.localeCompare(a.date));
      const fragment = document.createDocumentFragment();
      reports.forEach(report => fragment.append(reportRow(report)));
      list.replaceChildren(fragment);
      if (reports.length) status.hidden = true;
      else showStatus('暂无研报，稍后再来看看。');
    } catch (error) {
      showStatus(location.protocol === 'file:' ? '请通过本地预览服务或网站地址打开页面。' : '研报列表暂时无法加载，请刷新页面重试。');
      console.error('研报目录加载失败', error);
    }
  }
  load();
})();

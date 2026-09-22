/**
 * Lightweight, secure, zero-dependency Markdown parser for Enterprise AI Assistant.
 * Fully compliant with WCAG AA and UI/UX Pro Max typography guidelines.
 */

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function renderMarkdown(content) {
  if (!content) return '';

  // 1. Separate code blocks to protect them from inline parsing
  const codeBlocks = [];
  let text = content.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
    const escapedCode = escapeHtml(code.trimEnd());
    const displayLang = escapeHtml(lang || 'code');
    const html = `
      <div class="my-3 rounded-xl overflow-hidden border border-border-subtle bg-slate-950/90 shadow-md">
        <div class="flex items-center justify-between px-3 py-1.5 bg-slate-900/90 border-b border-border-subtle text-[11px] text-text-secondary select-none">
          <span class="font-mono text-brand-primary uppercase font-medium">${displayLang}</span>
          <button
            onclick="navigator.clipboard && navigator.clipboard.writeText(decodeURIComponent('${encodeURIComponent(code)}'))"
            class="interactive-action px-2 py-0.5 rounded text-[10px] text-text-secondary hover:text-text-main hover:bg-slate-800 border border-transparent hover:border-border-subtle transition-colors duration-150"
            title="复制代码"
          >
            复制
          </button>
        </div>
        <pre class="p-3 text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed"><code>${escapedCode}</code></pre>
      </div>
    `.trim();
    codeBlocks.push(html);
    return placeholder;
  });

  // 2. Parse Markdown tables
  text = text.replace(/((?:\|[^\n]+\|\r?\n)+)/g, (tableBlock) => {
    const rows = tableBlock.trim().split(/\r?\n/).map(r => r.trim());
    if (rows.length < 2) return tableBlock;

    // Check if second row is divider e.g. |---|---|
    const isDivider = /^\|?(\s*:?-+:?\s*\|?)+$/.test(rows[1]);
    if (!isDivider) return tableBlock;

    const parseCells = (row) => {
      return row.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
    };

    const headerCells = parseCells(rows[0]);
    let tableHtml = '<div class="my-3 overflow-x-auto rounded-xl border border-border-subtle shadow-sm"><table class="w-full text-xs text-left border-collapse bg-slate-900/40">';
    tableHtml += '<thead><tr class="bg-slate-800/80 border-b border-border-card text-text-main font-semibold">';
    headerCells.forEach(cell => {
      tableHtml += `<th class="px-3.5 py-2.5">${escapeHtml(cell)}</th>`;
    });
    tableHtml += '</tr></thead><tbody>';

    for (let i = 2; i < rows.length; i++) {
      const cells = parseCells(rows[i]);
      tableHtml += '<tr class="border-b border-border-subtle/50 hover:bg-slate-800/30 transition-colors duration-150">';
      cells.forEach(cell => {
        tableHtml += `<td class="px-3.5 py-2 text-text-secondary">${escapeHtml(cell)}</td>`;
      });
      tableHtml += '</tr>';
    }

    tableHtml += '</tbody></table></div>';
    return tableHtml;
  });

  // 3. Headings
  text = text.replace(/^### (.*$)/gim, '<h3 class="text-sm font-bold text-text-main mt-3 mb-1.5 flex items-center space-x-1.5"><span class="w-1.5 h-1.5 rounded-full bg-brand-primary shrink-0"></span><span>$1</span></h3>');
  text = text.replace(/^## (.*$)/gim, '<h2 class="text-base font-bold text-text-main mt-4 mb-2 pb-1 border-b border-border-subtle">$1</h2>');
  text = text.replace(/^# (.*$)/gim, '<h1 class="text-lg font-extrabold text-text-main mt-4 mb-2">$1</h1>');

  // 4. Blockquotes
  text = text.replace(/^\> (.*$)/gim, '<blockquote class="border-l-2 border-brand-primary pl-3 my-2 text-text-secondary italic text-xs bg-slate-900/30 py-1 rounded-r-lg">$1</blockquote>');

  // 5. Inline Code
  text = text.replace(/`([^`]+)`/g, (match, code) => {
    return `<code class="px-1.5 py-0.5 mx-0.5 rounded bg-slate-900 border border-border-subtle font-mono text-xs text-cyan-300">$code</code>`.replace('$code', escapeHtml(code));
  });

  // 6. Bold & Italic
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-text-main">$1</strong>');
  text = text.replace(/\*([^*]+)\*/g, '<em class="italic text-text-secondary">$1</em>');

  // 7. Links
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, url) => {
    const safeUrl = escapeHtml(url.trim());
    return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer" class="text-brand-primary underline hover:text-brand-primary-hover transition-colors duration-150">${escapeHtml(label)}</a>`;
  });

  // 8. Lists (Unordered & Ordered)
  text = text.replace(/^[\*\-] (.*$)/gim, '<li class="text-xs text-text-main leading-relaxed pl-1">$1</li>');
  text = text.replace(/^\d+\. (.*$)/gim, '<li class="text-xs text-text-main leading-relaxed pl-1">$1</li>');

  // Group <li> into <ul>
  text = text.replace(/(<li[\s\S]*?<\/li>\n?)+/g, (match) => {
    return `<ul class="list-disc list-inside space-y-1 my-2 pl-1">${match}</ul>`;
  });

  // 9. Paragraphs and line breaks
  const paragraphs = text.split(/\n{2,}/);
  text = paragraphs.map(p => {
    const trimmed = p.trim();
    if (!trimmed) return '';
    // If it's already a block tag, do not wrap in <p>
    if (trimmed.startsWith('<h1') || trimmed.startsWith('<h2') || trimmed.startsWith('<h3') ||
        trimmed.startsWith('<div') || trimmed.startsWith('<table') || trimmed.startsWith('<ul') ||
        trimmed.startsWith('<blockquote') || trimmed.startsWith('__CODE_BLOCK_')) {
      return trimmed;
    }
    return `<p class="my-1.5 leading-relaxed text-xs sm:text-sm text-text-main">${trimmed.replace(/\n/g, '<br/>')}</p>`;
  }).join('\n');

  // 10. Restore code blocks
  codeBlocks.forEach((block, idx) => {
    text = text.replace(`__CODE_BLOCK_${idx}__`, block);
  });

  return text;
}

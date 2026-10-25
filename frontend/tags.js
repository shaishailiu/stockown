function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
}
function renderStockTags(stock) {
    return (stock.tags || []).map(t => `<span class="type-tag type-other">${escapeHtml(t.name)}</span>`).join(' ') || '<span style="color:#999">未标记</span>';
}
// 空字符串表示全部；筛选标签互斥，持仓本身仍可绑定多个标签。
let selectedFilterTag = '';
function fillTagFilter(tags) {
    const container = document.getElementById('tag-filter');
    const options = [{id: '', name: '全部'}, ...tags, {id: 'untagged', name: '未标记'}];
    const valid = new Set(options.map(t => String(t.id)));
    if (!valid.has(selectedFilterTag)) selectedFilterTag = '';
    container.replaceChildren();
    for (const option of options) {
        const id = String(option.id);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'tag-filter-chip';
        button.textContent = option.name;
        button.dataset.tagId = id;
        button.setAttribute('aria-pressed', String(id === selectedFilterTag));
        button.addEventListener('click', () => {
            selectedFilterTag = id;
            for (const chip of container.children) {
                const key = chip.dataset.tagId;
                chip.setAttribute('aria-pressed', String(key === selectedFilterTag));
            }
            container.dispatchEvent(new Event('change', {bubbles: true}));
        });
        container.append(button);
    }
}
function filterStocks(stocks) {
    if (!selectedFilterTag) return stocks;
    return stocks.filter(stock => {
        const ids = stock.tag_ids || [];
        return (selectedFilterTag === 'untagged' ? !ids.length : ids.includes(Number(selectedFilterTag)));
    });
}

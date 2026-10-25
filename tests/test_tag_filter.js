const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const container = {
    children: [], changes: 0,
    replaceChildren() { this.children = []; },
    append(button) { this.children.push(button); },
    dispatchEvent() { this.changes++; }
};
const context = {Event: class {}, document: {
    getElementById: () => container,
    createElement: () => ({dataset: {}, attrs: {}, setAttribute(k,v) { this.attrs[k]=v; },
        addEventListener(event, callback) { this.click=callback; }})
}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('frontend/tags.js', 'utf8'), context);
const tags = [{id:1,name:'AI'}, {id:2,name:'中概股'}, {id:3,name:'<测试>'}];
const stocks = [{id:1,tag_ids:[1]}, {id:2,tag_ids:[2]}, {id:3,tag_ids:[1,2]}, {id:4,tag_ids:[]}];
const click = id => container.children.find(b => b.dataset.tagId===id).click();
const ids = () => Array.from(context.filterStocks(stocks), s => s.id);
context.fillTagFilter(tags);
assert.equal(container.children.length,5);
assert.equal(container.children[0].attrs['aria-pressed'],'true');
assert.deepEqual(ids(),[1,2,3,4]);
function assertSingleActive(id) {
    assert.deepEqual(container.children.filter(b => b.attrs['aria-pressed']==='true').map(b => b.dataset.tagId), [id]);
}
click('1'); assert.deepEqual(ids(),[1,3]); assertSingleActive('1');
click('2'); assert.deepEqual(ids(),[2,3]); assertSingleActive('2');
context.fillTagFilter(tags); assert.deepEqual(ids(),[2,3]); assertSingleActive('2');
click('2'); assert.deepEqual(ids(),[2,3]); assertSingleActive('2');
click('untagged'); assert.deepEqual(ids(),[4]); assertSingleActive('untagged');
click(''); assert.deepEqual(ids(),[1,2,3,4]); assertSingleActive('');
click('3'); assert.deepEqual(ids(),[]); assertSingleActive('3');
context.fillTagFilter(tags.slice(0,2)); assert.deepEqual(ids(),[1,2,3,4]); assertSingleActive('');
assert.equal(container.changes,6);
console.log('单选互斥、重复点击、全部、未标记、刷新及标签删除检查通过');

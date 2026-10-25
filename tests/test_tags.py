import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('stockown_app', Path(__file__).parents[1] / 'backend/app.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = {name: getattr(m, name) for name in ('DATA_FILE', 'TAGS_FILE', 'CACHE_FILE', 'LAST_UPDATE_FILE')}
        for name in self.original:
            setattr(m, name, str(Path(self.temp.name) / (name + '.json')))
        m.write_json(m.DATA_FILE, [dict(id=1, code='AAPL', name='Apple', market='US', type='AI', buy_price=100, current_price=120, quantity=10)])
        self.c = m.app.test_client()
    def tearDown(self):
        for name, value in self.original.items(): setattr(m, name, value)
        self.temp.cleanup()
    def test_migration(self):
        d = self.c.get('/api/stocks').get_json()
        self.assertEqual(d['stocks'][0]['tags'], [{'id': 1, 'name': 'AI'}])
        self.assertEqual(d['stocks'][0]['profit'], 1560)
        self.c.get('/api/stocks')
        self.assertEqual(len(m.load_tags()), 1)
        self.assertNotIn('type', m.load_stocks()[0])
    def test_multi_tag_lifecycle(self):
        self.c.get('/api/stocks')
        r = self.c.post('/api/tags', json={'name': '半导体'})
        self.assertEqual(r.status_code, 201)
        i = r.get_json()['tag']['id']
        self.assertEqual(self.c.put('/api/stocks/1', json={'tag_ids': [1, i, i]}).status_code, 200)
        self.assertEqual(m.load_stocks()[0]['tag_ids'], [1, i])
        self.assertEqual(self.c.put('/api/tags/1', json={'name': '人工智能'}).status_code, 200)
        d = self.c.get('/api/stocks').get_json()
        self.assertEqual([t['name'] for t in d['stocks'][0]['tags']], ['人工智能', '半导体'])
        self.assertEqual([s['ratio'] for s in d['sectors']], [100, 100])
        self.c.delete('/api/tags/1')
        self.c.delete(f'/api/tags/{i}')
        self.assertEqual(self.c.get('/api/stocks').get_json()['stocks'][0]['tags'], [])
        self.assertEqual(m.load_tags(), [])
        self.assertEqual(len(m.load_stocks()), 1)
    def test_price_refresh_preserves_concurrent_tag_changes(self):
        self.c.get('/api/stocks')
        self.c.put('/api/stocks/1', json={'tag_ids': []})
        m.apply_cached_prices({'AAPL': {'price': 150}})
        stock = m.load_stocks()[0]
        self.assertEqual(stock['tag_ids'], [])
        self.assertEqual(stock['current_price'], 150)

    def test_validation(self):
        self.c.get('/api/stocks')
        for name in ['', '   ', 'a' * 41, 12, None, 'ai']:
            self.assertEqual(self.c.post('/api/tags', json={'name': name}).status_code, 400)
        for value in [[999], 'AI', [True], [1.0]]:
            self.assertEqual(self.c.put('/api/stocks/1', json={'tag_ids': value}).status_code, 400)
        self.assertEqual(m.load_stocks()[0]['tag_ids'], [1])
        self.assertEqual(self.c.delete('/api/tags/999').status_code, 404)
    def test_create_and_partial_update(self):
        self.c.get('/api/stocks')
        r = self.c.post('/api/stocks', json=dict(code='0700', name='腾讯', market='HK', tag_ids=[1], buy_price=100, quantity=5))
        self.assertEqual(r.status_code, 201)
        i = r.get_json()['stock']['id']
        self.c.put(f'/api/stocks/{i}', json={'current_price': 200})
        self.assertEqual(m.load_stocks()[1]['tag_ids'], [1])
        self.c.put(f'/api/stocks/{i}', json={'tag_ids': []})
        self.assertEqual(m.load_stocks()[1]['tag_ids'], [])

if __name__ == '__main__': unittest.main()

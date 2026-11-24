import json
import tempfile
import zipfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runner as r


class ExperimentTests(unittest.TestCase):
    def test_budget_and_unknown_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            calls = []
            ledger = r.Ledger(path, r.money('0.01'))
            with self.assertRaisesRegex(r.Stop, 'BUDGET'):
                ledger.post('U', '/files', b'x', 'x', r.UPLOAD,
                            lambda *args: calls.append(args), lambda _: {})
            self.assertEqual(calls, [])
            other = path / 'other'
            other.mkdir()
            ledger = r.Ledger(other, r.money('1.00'))

            def timeout(*args):
                calls.append(args)
                self.assertIn('pending', (other / 'ledger.json').read_text())
                raise TimeoutError

            with self.assertRaisesRegex(r.Stop, 'UNKNOWN'):
                ledger.post('U', '/files', b'x', 'x', r.UPLOAD, timeout, lambda _: {})
            with self.assertRaises(FileExistsError):
                r.Ledger(other, r.money('1.00'))
            self.assertEqual(len(calls), 1)

    def test_stateless_arms(self):
        a = r.chat('A', 'test Q', 'file-api-test')
        b = r.chat('B', 'test Q', 'test essence')
        d = r.chat('D', r.DISTILL, 'file-api-test')
        self.assertEqual(a['messages'][0], b['messages'][0])
        self.assertEqual(a['messages'][1]['content'][0], b['messages'][1]['content'][0])
        self.assertIn('file_id', a['messages'][1]['content'][1])
        self.assertNotIn('file_id', str(b))
        self.assertNotIn('test essence', str(a))
        self.assertNotIn('test Q', str(d))
        for arm in (a, b, d):
            self.assertEqual(len(arm['messages']), 2)
            self.assertNotIn('tools', arm)
            self.assertEqual(arm['reasoning_effort'], 'high')

    def test_usage_accounting(self):
        response = {'usage': {'prompt_tokens': 20, 'prompt_cache_hit_tokens': 5,
                              'prompt_cache_miss_tokens': 15, 'completion_tokens': 3,
                              'completion_tokens_details': {'reasoning_tokens': 2}}}
        self.assertEqual(r.usage(response, 10)['upper_charge_nusd'], 8130)
        response['usage']['prompt_tokens'] = 21
        with self.assertRaises(ValueError):
            r.usage(response, 10)

    def test_complete_mock_and_partial_pair(self):
        for budget, expected, count in [('1.00', 'PASS', 26), ('0.40', 'PARTIAL_STOP', 2)]:
            with self.subTest(budget=budget), tempfile.TemporaryDirectory() as d:
                path = Path(d)
                calls = []
                secret_id = 'file-api-private-mock'

                def mock(endpoint, body, mime):
                    if endpoint == '/files':
                        calls.append('U')
                        self.assertLess(body.index(b'rich_layout_recognition'), body.index(b'filename'))
                        return r.encode({'id': secret_id, 'purpose': 'rich_layout_recognition',
                                         'bytes': 3024578})
                    request = json.loads(body)
                    question, material = request['messages'][1]['content']
                    is_d = question['text'] == r.DISTILL
                    arm = 'D' if is_d else ('A' if material['type'] == 'file' else 'B')
                    calls.append(arm)
                    text = '\n'.join('## ' + marker + '\n' + 'Страница 1. ' * 8
                                     for marker in r.SECTIONS) if is_d else 'Ответ fixture'
                    return r.encode({'model': r.MODEL, 'choices': [
                        {'message': {'content': text, 'reasoning_content': 'private-chain'},
                         'finish_reason': 'stop'}],
                        'usage': {'prompt_tokens': 20, 'prompt_cache_hit_tokens': 5,
                                  'prompt_cache_miss_tokens': 15, 'completion_tokens': 3,
                                  'completion_tokens_details': {'reasoning_tokens': 2}}})

                archive = r.perform(b'mock', {}, {}, path, r.money(budget), mock)
                with zipfile.ZipFile(archive) as bundle:
                    self.assertIsNone(bundle.testzip())
                    self.assertNotIn('ledger.json', bundle.namelist())
                    all_content = b''.join(bundle.read(n) for n in bundle.namelist())
                    self.assertNotIn(secret_id.encode(), all_content)
                    self.assertNotIn(b'private-chain', all_content)
                    summary = json.loads(bundle.read('summary.json'))
                    self.assertEqual(summary['status'], expected)
                    self.assertEqual(summary['attempted_operations'], count)
                    for row in bundle.read('SHA256SUMS').decode().splitlines():
                        sha, filename = row.split('  ')
                        self.assertEqual(r.digest(bundle.read(filename)), sha)
                self.assertEqual(calls[:2], ['U', 'D'])
                self.assertEqual(calls[2:6], ['A', 'B', 'B', 'A'] if count > 2 else [])

    def test_cloud_live_rejected_before_transport(self):
        with patch.object(r, 'is_wsl', return_value=False), patch.object(r, 'transport') as send:
            with self.assertRaisesRegex(r.Stop, 'WSL'):
                r.live(None, None, None, False)
            send.assert_not_called()

    def test_length_and_missing_sections_stop(self):
        self.assertFalse(r.complete_essence('## Назначение\nТест', 'stop'))
        text = '\n'.join('## ' + marker + '\n' + 'Страница 1. ' * 8 for marker in r.SECTIONS)
        self.assertTrue(r.complete_essence(text, 'stop'))
        self.assertFalse(r.complete_essence(text, 'length'))


if __name__ == '__main__':
    unittest.main()

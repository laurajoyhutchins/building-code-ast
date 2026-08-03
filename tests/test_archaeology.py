from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_archaeology import validate  # noqa: E402

class ArchaeologyTests(unittest.TestCase):
    def test_graph_and_generated_views_validate(self):
        errors,summary=validate(write=False)
        self.assertEqual(errors,[])
        self.assertEqual(summary['nodes'],96)
        self.assertEqual(summary['edges'],107)
        self.assertEqual(summary['patches'],9)

    def test_current_support_is_qualified(self):
        current=json.loads((ROOT/'docs/archaeology/current-architecture.json').read_text())
        by_id={node['semantic_id']:node for node in current['nodes']}
        self.assertIn('obs.current-main-support',by_id)
        self.assertIn('obs.branch-bound-support',by_id)
        export=json.loads((ROOT/'.deciduous/exports/building-code-ast-archaeology.json').read_text())
        nodes={json.loads(node['metadata_json'])['semantic_id']:json.loads(node['metadata_json']) for node in export['nodes']}
        self.assertEqual(nodes['outcome.ibc-not-current-main']['lifecycle_status'],'branch-only')
        self.assertEqual(nodes['outcome.nfpa13-draft-not-main']['lifecycle_status'],'branch-only')
        self.assertEqual(nodes['outcome.nec2020-changelog-not-main']['lifecycle_status'],'branch-only')

if __name__=='__main__': unittest.main()

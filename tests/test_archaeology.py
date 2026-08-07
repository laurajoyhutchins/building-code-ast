from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_archaeology import validate  # noqa: E402

class ArchaeologyTests(unittest.TestCase):
    def test_graph_and_generated_views_validate(self):
        errors,summary=validate(write=False)
        self.assertEqual(errors,[])
        self.assertEqual(summary['nodes'],107)
        self.assertEqual(summary['edges'],120)
        self.assertEqual(summary['patches'],11)

    def test_validation_is_content_based_not_git_history_dependent(self):
        with mock.patch('subprocess.run',side_effect=AssertionError('validation inspected git history')):
            errors,summary=validate(write=False)
        self.assertEqual(errors,[])
        self.assertEqual(summary['nodes'],107)

    def test_current_support_tracks_merged_frameworks_and_remaining_gates(self):
        current=json.loads((ROOT/'docs/archaeology/current-architecture.json').read_text())
        by_id={node['semantic_id']:node for node in current['nodes']}
        for semantic_id in (
            'decision.section-address-primary',
            'outcome.pages-provenance-only',
            'outcome.ibc2018-corpus-merged-pr33',
            'outcome.nfpa13-support-merged-pr34',
            'outcome.nec2020-framework-merged-pr35',
            'outcome.provision-ast-0.3-merged-pr37',
        ):
            self.assertIn(semantic_id,by_id)
        export=json.loads((ROOT/'.deciduous/exports/building-code-ast-archaeology.json').read_text())
        nodes={json.loads(node['metadata_json'])['semantic_id']:json.loads(node['metadata_json']) for node in export['nodes']}
        self.assertEqual(nodes['decision.section-address-primary']['lifecycle_status'],'completed')
        self.assertEqual(nodes['outcome.pages-provenance-only']['lifecycle_status'],'completed')
        self.assertEqual(nodes['outcome.nec2020-framework-merged-pr35']['lifecycle_status'],'completed')
        self.assertEqual(nodes['obs.nec2020-source-unavailable']['lifecycle_status'],'unresolved')
        self.assertEqual(nodes['obs.nfpa13-unsupported-visual-semantics']['lifecycle_status'],'unresolved')

if __name__=='__main__': unittest.main()

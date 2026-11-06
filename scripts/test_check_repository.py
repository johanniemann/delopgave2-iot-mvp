"""Failure-oriented checks for references and portability in the shared setup."""
import tempfile
import unittest
from pathlib import Path

from check_repository import check_paths


class RepositoryChecksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, content=''):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return name

    def test_relative_links_import_and_unicode_anchor(self):
        paths = [self.write('AGENTS.md', '# Policy\n'),
                 self.write('CLAUDE.md', '@AGENTS.md\n'),
                 self.write('docs/guide.md', '# Ændringer\n# Ændringer\n'),
                 self.write('README.md', '[guide](docs/guide.md#ændringer-1)\n'
                            '[policy](AGENTS.md)\n[official](https://example.com)')]
        self.assertEqual([], check_paths(self.root, paths))

    def test_missing_reference_fails(self):
        name = self.write('README.md', '[missing](docs/missing.md)')
        self.assertIn('broken local reference', '\n'.join(check_paths(self.root, [name])))

    def test_missing_import_fails(self):
        name = self.write('CLAUDE.md', '@missing.md\n')
        self.assertIn('broken local reference', '\n'.join(check_paths(self.root, [name])))

    def test_missing_heading_fails(self):
        name = self.write('README.md', '# Actual\n[wrong](#missing)')
        self.assertIn('missing heading', '\n'.join(check_paths(self.root, [name])))

    def test_external_local_file_cannot_become_dependency(self):
        name = self.write('README.md', '[outside](../outside.md)')
        self.assertIn('leaves repository', '\n'.join(check_paths(self.root, [name])))

    def test_absolute_contributor_path_fails(self):
        name = self.write('README.md', 'Run from /Users/someone/Desktop/course')
        self.assertIn('absolute path', '\n'.join(check_paths(self.root, [name])))

    def test_secret_filenames_fail_but_placeholder_is_allowed(self):
        names = [self.write('.env'), self.write('server.key'), self.write('.env.example')]
        errors = check_paths(self.root, names)
        self.assertEqual(2, len(errors))
        self.assertFalse(any('.env.example' in error for error in errors))

    def test_examples_are_not_treated_as_real_links(self):
        name = self.write('README.md', '```md\n[example](not-an-actual-file.md)\n```\n')
        self.assertEqual([], check_paths(self.root, [name]))

    def test_indexed_missing_file_fails(self):
        self.assertIn('indexed file is missing', '\n'.join(
            check_paths(self.root, ['deleted.md'])))


if __name__ == '__main__':
    unittest.main()

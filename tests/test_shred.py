import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dmk.a_utils.shred import shred


class TestShred(unittest.TestCase):
    def test(self):
        with TemporaryDirectory() as tds:
            tds = Path(tds)
            file = tds/"temp.txt"
            file.write_text('life is short')
            self.assertTrue(file.exists())
            shred(file)
            self.assertFalse(file.exists())


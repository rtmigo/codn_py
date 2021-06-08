# SPDX-FileCopyrightText: (c) 2021 Artёm IG <github.com/rtmigo>
# SPDX-License-Identifier: MIT

import unittest

from ksf._10_randoms import get_fast_random_bytes


class TestRandomBytes(unittest.TestCase):

    def test_len(self):
        self.assertEqual(len(get_fast_random_bytes(16)), 16)
        self.assertEqual(len(get_fast_random_bytes(10)), 10)
        self.assertEqual(len(get_fast_random_bytes(0)), 0)

    def test_type(self):
        self.assertIsInstance(get_fast_random_bytes(16), bytes)

    def test_is_different(self):
        self.assertNotEqual(
            get_fast_random_bytes(50),
            get_fast_random_bytes(50))

# SPDX-FileCopyrightText: (c) 2021 Artёm IG <github.com/rtmigo>
# SPDX-License-Identifier: MIT

import unittest

from ksf._20_key_derivation import password_to_key, KeyDerivationSettings


class TestPtk(unittest.TestCase):

    def test(self):
        # the password to key returns cached values, so we
        # test two things at once:
        # * that all the parameter changes lead to different keys
        # * that cache keys are unique

        seen = set()

        PWD = "password"
        SALT = bytes([1, 2, 3])
        POWER = KeyDerivationSettings.power

        p = password_to_key(PWD, SALT)
        self.assertNotIn(p, seen)
        seen.add(p)

        # different password
        p = password_to_key("other password", SALT)
        self.assertNotIn(p, seen)
        seen.add(p)

        # different salt
        p = password_to_key(PWD, bytes([99, 88, 77]))
        self.assertNotIn(p, seen)
        seen.add(p)

        try:
            KeyDerivationSettings.power -= 1

            # different power
            p = password_to_key(PWD, SALT)
            self.assertNotIn(p, seen)
            seen.add(p)

        finally:
            KeyDerivationSettings.power = POWER

        self.assertEqual(len(seen), 4)

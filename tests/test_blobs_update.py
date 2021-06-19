# SPDX-FileCopyrightText: (c) 2021 Artёm IG <github.com/rtmigo>
# SPDX-License-Identifier: MIT


import io
import unittest
from io import BytesIO
from typing import BinaryIO

from dmk.a_base._10_kdf import FasterKDF, CodenameKey
from dmk.b_cryptoblobs._20_encdec_part import is_content_io, \
    is_fake_io
from dmk.b_storage_file import BlocksIndexedReader, BlocksSequentialWriter
from dmk.c_namegroups._update import update_namegroup_b
from tests.common import testing_salt


def full_stream_to_bytes(stream: BinaryIO) -> bytes:
    stream.seek(0, io.SEEK_SET)
    return stream.read()


class TestUpdate(unittest.TestCase):
    faster: FasterKDF

    @classmethod
    def setUpClass(cls) -> None:
        cls.faster = FasterKDF()
        cls.faster.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.faster.end()

    def test_update_adds_fakes_and_content(self):
        pk = CodenameKey("abc", testing_salt)

        fake_nums = set()
        part_nums = set()
        content_sizes = set()

        for _ in range(20):
            empty_reader = BlocksIndexedReader(BytesIO())

            new_storage_io = BytesIO()
            with BlocksSequentialWriter(new_storage_io) as writer:
                original_content_io = BytesIO(b'0' * (1024 * 128))
                update_namegroup_b(pk, original_content_io, empty_reader,
                                   writer)

            new_storage_io.seek(0, io.SEEK_SET)
            new_reader = BlocksIndexedReader(new_storage_io)
            self.assertGreater(len(new_reader), 0)
            self.assertGreater(new_reader.tail_size, 0)

            with self.subTest("Content appeared"):
                content_blobs = [full_stream_to_bytes(s) for s in new_reader
                                 if is_content_io(pk, s)]
                self.assertGreater(len(content_blobs), 0)
                part_nums.add(len(content_blobs))
                content_sizes.add(tuple(sorted(len(b) for b in content_blobs)))

            with self.subTest("Fakes appeared"):
                fake_blobs = [full_stream_to_bytes(s) for s in new_reader
                              if is_fake_io(pk, s)]
                self.assertGreater(len(fake_blobs), 0)
                fake_nums.add(len(fake_blobs))

        with self.subTest("Number of fakes is random"):
            self.assertGreaterEqual(len(fake_nums), 3)


if __name__ == "__main__":
    unittest.main()

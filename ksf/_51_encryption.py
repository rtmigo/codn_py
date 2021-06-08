# SPDX-FileCopyrightText: (c) 2021 Artёm IG <github.com/rtmigo>
# SPDX-License-Identifier: MIT

import io
import os
import random
import struct
from pathlib import Path
from typing import BinaryIO

from Crypto.Cipher import ChaCha20_Poly1305
from Crypto.Hash import BLAKE2b

from ksf._10_randoms import get_fast_random_bytes
from ksf._40_imprint import Imprint, HashCollision, half_n_half
from ksf._50_sur import set_random_last_modified
from ksf._wtf import WritingToTempFile


class MacCheckFailed(Exception):
    pass


class InsufficientData(Exception):
    pass


def double_to_bytes(x: float) -> bytes:
    return struct.pack('>d', x)


def bytes_to_double(b: bytes) -> float:
    result = struct.unpack('>d', b)
    # print(result)
    return result[0]


def encrypt_to_dir(source_file: Path, name: str, target_dir: Path) -> Path:
    """The file contains two imprints: one in the file name, and the other
    at the beginning of the file.

    Both imprints are generated from the same name, but with different
    nonce values.
    """

    imprint = Imprint(name)
    fn = target_dir / imprint.as_str
    if fn.exists():
        raise HashCollision

    _encrypt_file_to_file(source_file, name, fn)
    return fn


def pwd_to_encryption_key(password: str, salt: bytes) -> bytes:
    """Converts string password to a 256-bit key.

    This function will be used to generate:
    - dictionary keys (they are public)
    - encryption keys (they are secret)
    For each item both keys are generated from the same password,
    but the salt must be different."""
    password = ''.join(reversed(password))
    h_obj = BLAKE2b.new(digest_bits=256)

    a, b = half_n_half(salt)
    h_obj.update(a + password.encode('utf-8') + b)
    return h_obj.digest()


MAC_LEN = 16
VERSION_LEN = 1
SRC_MTIME_LEN = 8
SRC_SIZE_LEN = 3


class _IntroPadding:
    """When the encrypted content always starts with the same bytes, this
    could hypothetically make it easier to crack the cipher. So I put a little
    random padding at the beginning of the file.

    Without this padding, every file would begin with a constant: the version
    of the file format. But if padding is added before that, we only know that
    the constant is somewhere in the first seventeen bytes.
    """

    @staticmethod
    def first_byte_to_len(x: int) -> int:
        """Returns number from range 0..15"""
        return x & 15

    @staticmethod
    def gen_bytes():
        first_byte = random.randint(0, 0xFF)
        length = _IntroPadding.first_byte_to_len(first_byte)
        assert 0 <= length <= 15

        result = bytes((first_byte,))
        if length > 1:
            result += get_fast_random_bytes(length - 1)

        return result

    @staticmethod
    def skip_in_file(df: BinaryIO):
        # skipping the intro padding
        intro_padding_first_byte = read_or_fail(df, 1)[0]
        intro_length = _IntroPadding.first_byte_to_len(intro_padding_first_byte)
        if intro_length > 1:
            read_or_fail(df, intro_length - 1)  # or just seek?


def _encrypt_file_to_file(source_file: Path, name: str, target_file: Path):
    header_imprint = Imprint(name)

    stat = source_file.stat()

    version = bytes([1])

    src_mtime_bytes = double_to_bytes(stat.st_mtime)
    assert len(src_mtime_bytes) == SRC_MTIME_LEN

    src_size_bytes = stat.st_size.to_bytes(SRC_SIZE_LEN,
                                           byteorder='big',
                                           signed=False)
    assert len(src_size_bytes) == SRC_SIZE_LEN

    plain_parts = [
        _IntroPadding.gen_bytes(),
        version,
        src_mtime_bytes,
        src_size_bytes,
        source_file.read_bytes()
    ]

    # todo test end padding
    end_padding_len = random.randint(0, max(stat.st_size * 2, 8096))
    if end_padding_len > 0:
        plain_parts.append(get_fast_random_bytes(end_padding_len))

    plain_bytes = b''.join(plain_parts)

    # print(name, header_imprint.nonce)

    key = pwd_to_encryption_key(name, salt=header_imprint.nonce)
    # print('enc key', key)
    cipher_config = ChaCha20_Poly1305.new(key=key, nonce=header_imprint.nonce)
    cipher_bytes, mac = cipher_config.encrypt_and_digest(plain_bytes)
    # print('enc mac', mac)
    # print('enc bytes', cipher_bytes)

    assert len(mac) == MAC_LEN

    with WritingToTempFile(target_file) as wtf:
        # must be the same as writing a fake file
        with wtf.dirty.open('wb') as outfile:
            outfile.write(header_imprint.as_bytes)
            outfile.write(mac)
            outfile.write(cipher_bytes)  # todo chunks?
        set_random_last_modified(wtf.dirty)  # todo test it
        wtf.replace()


def read_or_fail(f: BinaryIO, n: int) -> bytes:
    result = f.read(n)
    if len(result) != n:
        raise InsufficientData
    return result


class DecryptedFile:

    def __init__(self, source_file: Path, name: str):
        with source_file.open('rb') as f:
            imprint_bytes = f.read(Imprint.FULL_LEN)
            # todo check header?
            mac = read_or_fail(f, MAC_LEN)

            nonce = Imprint.bytes_to_nonce(imprint_bytes)
            encrypted_bytes = f.read()

            key = pwd_to_encryption_key(name, salt=nonce)
            cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)

            try:
                decrypted = cipher.decrypt_and_verify(encrypted_bytes,
                                                      received_mac_tag=mac)
            except ValueError as e:
                if str(e) == 'MAC check failed':
                    raise MacCheckFailed from e
                raise

            with io.BytesIO(decrypted) as df:

                _IntroPadding.skip_in_file(df)

                version_bytes = df.read(VERSION_LEN)
                src_mtime_bytes = df.read(SRC_MTIME_LEN)
                self.mtime = bytes_to_double(src_mtime_bytes)
                src_size_bytes = df.read(SRC_SIZE_LEN)

                src_size = int.from_bytes(src_size_bytes,
                                          byteorder='big',
                                          signed=False)

                data = df.read(src_size)
                if len(data) != src_size:
                    raise ValueError
                self.end_padding_size = len(decrypted) - df.seek(0)
                self.body = data

    def write(self, target: Path):
        target.write_bytes(self.body)
        os.utime(str(target), (self.mtime, self.mtime))
        # set_file_last_modified(target, self.mtime)


def name_matches_header(name: str, file: Path) -> bool:
    """Returns True if the header imprint (written into the file) matches
    the `name`."""
    with file.open('rb') as f:
        header_bytes = f.read(Imprint.FULL_LEN)
        if len(header_bytes) < Imprint.FULL_LEN:
            return False
        nonce = Imprint.bytes_to_nonce(header_bytes)
    return Imprint(name, nonce=nonce).as_bytes == header_bytes

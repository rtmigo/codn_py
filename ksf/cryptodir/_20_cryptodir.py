# SPDX-FileCopyrightText: (c) 2021 Artёm IG <github.com/rtmigo>
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Optional

from ._10_kdf import FilesetPrivateKey
from ._10_salt import find_salt_in_dir, write_salt_and_fakes
from .fileset import update_fileset, Fileset, DecryptedIO


class CryptoDir:

    def __init__(self, directory: Path):
        self.directory = directory

        salt = find_salt_in_dir(self.directory)
        if salt is None:
            salt, _ = write_salt_and_fakes(self.directory)
        assert isinstance(salt, bytes)
        self.salt = salt

    def set_from_file(self, name: str, source: Path):
        pk = FilesetPrivateKey(name, self.salt)
        update_fileset(source, pk, self.directory)

    def get(self, name: str) -> Optional[bytes]:
        pk = FilesetPrivateKey(name, self.salt)
        fs = Fileset(self.directory, pk)
        if fs.real_file is None:
            return None

        with fs.real_file.open('rb') as f:
            return DecryptedIO(pk, f).read_data()

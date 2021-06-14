# SPDX-FileCopyrightText: (c) 2021 Artёm IG <github.com/rtmigo>
# SPDX-License-Identifier: MIT
import io
from io import BytesIO
from pathlib import Path
from typing import Optional, BinaryIO

from ._10_kdf import FilesetPrivateKey
from ._10_salt_files_old import find_salt_in_dir, write_salt_and_fakes
from .namegroup import NewNameGroup, decrypt_from_dios, update_namegroup


class CryptoDir:

    def __init__(self, directory: Path):
        if not directory.exists():
            raise FileNotFoundError(directory)
        self.directory = directory

        salt = find_salt_in_dir(self.directory)
        if salt is None:
            salt = write_salt_and_fakes(self.directory).salt
        assert isinstance(salt, bytes)
        self.salt = salt

    def set_from_io(self, name: str, source: BinaryIO):
        pk = FilesetPrivateKey(name, self.salt)
        update_namegroup(source, pk, self.directory)

    def get(self, name: str) -> Optional[bytes]:
        pk = FilesetPrivateKey(name, self.salt)
        with NewNameGroup(self.directory, pk) as nng:
            if not nng.fresh_content_files:
                return None

            with BytesIO() as decrypted:
                decrypt_from_dios(nng.fresh_content_files, decrypted)
                decrypted.seek(0, io.SEEK_SET)
                return decrypted.read()

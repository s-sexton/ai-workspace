from __future__ import annotations

import io

from common.console import print_text


class Cp1252Stream(io.StringIO):
    encoding = "cp1252"

    def write(self, text):
        text.encode(self.encoding)
        return super().write(text)


def test_print_text_replaces_unencodable_characters(monkeypatch):
    stream = Cp1252Stream()
    monkeypatch.setattr("sys.stdout", stream)

    print_text("hello 🤩")

    assert stream.getvalue() == "hello ?\n"

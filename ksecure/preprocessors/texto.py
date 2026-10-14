"""Texto plano, equivalente a plaintext_preprocessor.go y encoding.go de ferret-scan."""

import os

from ksecure.preprocessors.base import Preprocessor

MAX_BYTES = 100 * 1024 * 1024  # 100 MB, igual que ferret-scan

_PDF_MAGIC = b"%PDF-"


def decode(raw: bytes) -> str:
    """Bytes a texto: BOM UTF-8/UTF-16, UTF-16 sin BOM, UTF-8 y, si no, cp1252 (Excel/Notepad en Windows)."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="replace")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    # UTF-16 sin BOM: un byte nulo por cada letra ASCII, en posiciones alternadas.
    sample = raw[:512]
    if len(sample) >= 4 and sample[1::2].count(0) > len(sample) // 4 and sample[0::2].count(0) == 0:
        return raw.decode("utf-16-le", errors="replace")
    if len(sample) >= 4 and sample[0::2].count(0) > len(sample) // 4 and sample[1::2].count(0) == 0:
        return raw.decode("utf-16-be", errors="replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def looks_like_text(raw: bytes) -> bool:
    """Revisa los primeros 512 bytes, como LooksLikeText de ferret-scan."""
    head = raw[:512]
    if not head or head.startswith(_PDF_MAGIC):
        return False
    text = decode(head)
    if "\x00" in text:
        return False
    control = sum(1 for c in text if ord(c) < 32 and c not in "\t\r\n")
    return control / len(text) < 0.05


class PlainTextPreprocessor(Preprocessor):
    name = "Plain Text"
    processor_type = "plaintext"
    extensions = (
        ".txt", ".text", ".log", ".md", ".markdown", ".rst",
        ".yaml", ".yml", ".json", ".xml", ".toml", ".ini", ".conf", ".config", ".cfg",
        ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php",
        ".html", ".htm", ".css", ".scss", ".sass", ".less",
        ".sql", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
        ".csv", ".tsv", ".jsonl", ".ndjson",
        ".env", ".gitignore", ".dockerfile", ".makefile",
    )

    def can_process(self, path: str) -> bool:
        if super().can_process(path):
            return True
        # Sin extensión (Dockerfile, .env.local...): se decide mirando el contenido.
        if os.path.splitext(path)[1] == "":
            with open(path, "rb") as f:
                return looks_like_text(f.read(512))
        return False

    def extract(self, path: str) -> tuple[str, dict]:
        if os.path.getsize(path) > MAX_BYTES:
            raise ValueError(f"archivo demasiado grande (máx. {MAX_BYTES} bytes)")
        with open(path, "rb") as f:
            text = decode(f.read(MAX_BYTES))
        return text, {"line_count": text.count("\n") + 1}

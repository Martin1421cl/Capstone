"""Interfaz base que deben implementar todos los validadores de K-Secure.

Inspirado conceptualmente en el enfoque de detector.Validator de FerretScan
(AWS Labs): cada validador expone un método para escanear contenido y un
sistema de scoring de confianza basado en contexto (palabras clave
positivas/negativas alrededor de la coincidencia).
"""

from abc import ABC, abstractmethod

from ksecure.models import Finding


class BaseValidator(ABC):
    """Contrato mínimo de un validador de K-Secure."""

    #: Palabras clave que aumentan la confianza si aparecen cerca del match.
    POSITIVE_KEYWORDS: tuple[str, ...] = ()

    #: Palabras clave que disminuyen la confianza si aparecen cerca del match.
    NEGATIVE_KEYWORDS: tuple[str, ...] = ()

    #: Cuántos caracteres a cada lado del match se consideran "contexto".
    CONTEXT_WINDOW = 40

    @abstractmethod
    def find(self, content: str, source: str) -> list[Finding]:
        """Escanea `content` (texto plano) y retorna los Finding detectados.

        `source` identifica de dónde viene el contenido (ej. nombre de
        columna, archivo, etc.) y se propaga a cada Finding para trazabilidad.
        """
        raise NotImplementedError

    def _extract_context(self, content: str, start: int, end: int) -> str:
        lo = max(0, start - self.CONTEXT_WINDOW)
        hi = min(len(content), end + self.CONTEXT_WINDOW)
        return content[lo:hi].lower()

    def _keyword_adjustment(self, context: str) -> tuple[float, list[str]]:
        """Calcula el ajuste de score por palabras clave de contexto.

        Retorna (delta, motivos) donde delta se suma al score base.
        """
        delta = 0.0
        reasons: list[str] = []

        for kw in self.POSITIVE_KEYWORDS:
            if kw in context:
                delta += 0.10
                reasons.append(f'palabra clave positiva "{kw}"')

        for kw in self.NEGATIVE_KEYWORDS:
            if kw in context:
                delta -= 0.20
                reasons.append(f'palabra clave negativa "{kw}"')

        return delta, reasons

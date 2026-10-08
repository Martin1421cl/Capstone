"""Módulo de generación de reportes de clasificación.

Toma la lista de Finding producida por el KSecureScanner y genera un
reporte clasificado por nivel de riesgo/criticidad, pensado como
insumo de entrada para una herramienta DLP (Data Loss Prevention).
"""

import csv
import json
from collections import Counter
from pathlib import Path

from ksecure.models import Finding, RiskLevel


class ClassificationReport:
    """Reporte de clasificación construido a partir de una lista de Finding."""

    # Orden de severidad, de mayor a menor, para ordenar el reporte.
    _ORDEN_RIESGO = [
        RiskLevel.RESTRINGIDO,
        RiskLevel.CONFIDENCIAL,
        RiskLevel.INTERNO,
        RiskLevel.PUBLICO,
    ]

    def __init__(self, findings: list[Finding], limite: int = 10):
        # Ordenamos los hallazgos por nivel de riesgo y luego recortamos al límite especificado (por defecto 10)
        findings_ordenados = sorted(
            findings, key=lambda f: self._ORDEN_RIESGO.index(f.risk_level)
        )
        self.findings = findings_ordenados[:limite]

    def summary(self) -> dict:
        """Resumen: cantidad de hallazgos por nivel de riesgo y por tipo de dato."""
        por_riesgo = Counter(f.risk_level.value for f in self.findings)
        por_tipo = Counter(f.data_type.value for f in self.findings)
        return {
            "total_hallazgos": len(self.findings),
            "por_nivel_riesgo": dict(por_riesgo),
            "por_tipo_dato": dict(por_tipo),
        }

    def to_console(self) -> str:
        """Formato legible en texto plano, para revisar rápido en pantalla."""
        lines = ["=" * 70, "REPORTE DE CLASIFICACIÓN K-SECURE", "=" * 70]

        summary = self.summary()
        lines.append(f"Total de hallazgos: {summary['total_hallazgos']}")
        for nivel, cantidad in summary["por_nivel_riesgo"].items():
            lines.append(f"  - {nivel}: {cantidad}")
        lines.append("-" * 70)

        for f in self.findings:
            lines.append(
                f"[{f.risk_level.value:12}] {f.data_type.value:22} "
                f"'{f.raw_value}' -> {f.normalized_value} "
                f"(confianza: {f.confidence.value}, origen: {f.source})"
            )
            for reason in f.reasons:
                lines.append(f"      · {reason}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def to_json(self, path: str | Path) -> None:
        payload = {
            "resumen": self.summary(),
            "hallazgos": [f.to_dict() for f in self.findings],
        }
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def to_csv(self, path: str | Path) -> None:
        if not self.findings:
            Path(path).write_text("", encoding="utf-8")
            return

        fieldnames = list(self.findings[0].to_dict().keys())
        with Path(path).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for f in self.findings:
                writer.writerow(f.to_dict())

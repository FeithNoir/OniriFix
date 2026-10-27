"""Consistencia onomástica y de glosario (L2)."""

from __future__ import annotations

from collections.abc import Iterator

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.modelo import Contexto, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar


def _limites(patron: str) -> str:
    return rf"(?<![^\W\d_])(?:{patron})(?![^\W\d_])"


@registrar
class VariantesRegistradas:
    id = "CON-001"
    nivel = Nivel.L2
    descripcion = "Sustituye variantes explícitas por su forma canónica del registro."
    prioridad = 45
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        variantes = ctx.glosario.variantes
        if not variantes:
            return
        patron = re.compile(
            _limites("|".join(re.escape(v) for v in sorted(variantes, key=len, reverse=True))),
            flags=re.IGNORECASE | re.UNICODE,
        )
        for match in patron.finditer(texto):
            original = match.group(0)
            canonico = variantes.get(original.casefold())
            if not canonico:
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=canonico,
                confianza=0.97,
                nota=f"Variante registrada de «{canonico}».",
            )
            if hallazgo:
                yield hallazgo


@registrar
class CapitalizacionCanonica:
    id = "CON-002"
    nivel = Nivel.L2
    descripcion = "Restaura la capitalización de nombres y lugares canónicos."
    prioridad = 46
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        candidatos: set[str] = set()
        if bool(ctx.config.obtener("consistencia.incluir_personajes", True)):
            candidatos.update(ctx.glosario.nombres)
        if bool(ctx.config.obtener("consistencia.incluir_lugares", True)):
            candidatos.update(ctx.glosario.toponimos)
        if bool(ctx.config.obtener("consistencia.incluir_terminos", True)):
            candidatos.update(ctx.glosario.terminos)

        # Solo los nombres con una señal interna de nombre propio. Así «Mico»
        # (que también es un animal) no se corrige a ciegas.
        seleccionados = [
            nombre
            for nombre in candidatos
            if len(nombre.split()) > 1
            or any(c.isupper() for c in nombre[1:])
            or "'" in nombre
            or "’" in nombre
        ]
        if not seleccionados:
            return

        patron = re.compile(
            _limites("|".join(re.escape(n) for n in sorted(seleccionados, key=len, reverse=True))),
            flags=re.IGNORECASE | re.UNICODE,
        )
        for match in patron.finditer(texto):
            original = match.group(0)
            canonico = next(
                (n for n in seleccionados if n.casefold() == original.casefold()), None
            )
            if canonico is None or original == canonico:
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=canonico,
                confianza=0.84,
                nota=f"Capitalización canónica de «{canonico}».",
            )
            if hallazgo:
                yield hallazgo

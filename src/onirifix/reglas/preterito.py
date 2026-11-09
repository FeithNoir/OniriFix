"""Pasados sin tilde y su error espejo (L1/L2).

El informe editorial de Oniriums describe «familias enteras» de pretéritos
sin tilde: río/rió, suspiro/suspiró, continúo/continuó, poso/posó… Estas
reglas no adivinan: solo proponen un cambio cuando el contexto inmediato
descarta la otra lectura (un nombre propio delante, «se», una raya de
atribución, un determinante). Si el contexto no basta, callan.
"""

from __future__ import annotations

from collections.abc import Iterator

try:  # pragma: no cover
    import regex as re
except ImportError:  # pragma: no cover
    import re  # type: ignore[no-redef]

from onirifix.modelo import Contexto, Hallazgo, Nivel, crear_hallazgo
from onirifix.nucleo.registro_reglas import registrar
from onirifix.reglas._comun import es_palabra_glosario, preservar_caso

# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------

# Verbos -ar regulares frecuentes en narrativa. Su 1.ª persona del presente
# («miro») coincide con el pretérito sin tilde («miró»): son ambiguos.
_AR_AMBIGUOS = ["mirar", "suspirar", "posar", "cambiar", "señalar", "esquivar", "pasar", "fracasar", "brillar", "tragar", "contestar", "silenciar", "girar", "levantar", "gritar", "susurrar", "murmurar", "preguntar", "observar", "asomar", "avanzar", "apartar", "tomar", "dejar", "llegar", "entrar", "sacar", "notar", "alzar", "lanzar", "tocar", "acercar", "apoyar", "golpear", "saltar", "empujar", "intentar", "quedar", "llamar", "frenar", "terminar", "bostezar", "abrazar", "besar", "regresar", "saludar", "sollozar", "disparar", "resoplar", "carraspear", "escuchar", "esperar", "caminar", "voltear", "agarrar", "arrojar", "estirar", "sujetar", "guardar", "ignorar", "aclarar", "explicar", "replicar", "comentar", "tardar", "cruzar", "olvidar", "acariciar", "retirar", "analizar", "ajustar", "chocar", "gastar", "pagar", "firmar", "cargar", "liberar", "tirar", "marcar", "contemplar", "examinar", "lamentar", "bromear", "asegurar", "parpadear", "jadear", "gruñir", "chasquear", "sonrojar", "palidecer", "resbalar", "asentar", "arquear", "entrecerrar", "soplar", "inclinar"]

# Verbos con cambio de raíz: «conto», «solto» o «encontro» no existen, así
# que la tilde que falta es inequívoca.
_SIN_AMBIGUEDAD = ["contar", "soltar", "mostrar", "encontrar", "recordar", "sonar", "volar", "negar", "pensar", "despertar", "empezar", "comenzar", "colgar", "rogar", "acostar", "volcar", "temblar", "confesar", "atravesar", "calentar", "apretar"]

# Formas sin tilde que sí existen como otra palabra y por eso no pueden ir a
# la lista inequívoca: cerro (monte), jugo (zumo), probo (honrado), siento…
_AMBIGUOS_EXTRA = {
    "cerro": "cerró",
    "jugo": "jugó",
    "probo": "probó",
    "continuo": "continuó",
    "continúo": "continuó",
    "actúo": "actuó",
    "sitúo": "situó",
    "evalúo": "evaluó",
    "insinúo": "insinuó",
    "acentúo": "acentuó",
    "envío": "envió",
    "confío": "confió",
    "desafío": "desafió",
    "enfrío": "enfrió",
    "desvío": "desvió",
    "amplío": "amplió",
    "espío": "espió",
}

# Pretéritos -er/-ir que sin tilde no son ninguna palabra («respondio»).
_IO_INEQUIVOCOS = ["respondio", "salio", "subio", "abrio", "decidio", "recibio", "vivio", "escribio", "partio", "sonrio", "volvio", "movio", "corrio", "comio", "bebio", "temio", "perdio", "cogio", "recogio", "escogio", "aparecio", "desaparecio", "parecio", "conocio", "ofrecio", "obedecio", "crecio", "nacio", "entendio", "encendio", "extendio", "prometio", "metio", "sorprendio", "comprendio", "aprendio", "rompio", "tosio", "ocurrio", "insistio", "asistio", "permitio", "sacudio", "cubrio", "descubrio", "sufrio", "cumplio", "añadio", "compartio", "existio", "interrumpio", "unio", "dirigio", "exigio", "fingio", "surgio", "emitio", "admitio", "resistio", "dividio", "sintio", "pidio", "siguio", "sirvio", "repitio", "vistio", "murio", "durmio", "mintio", "sugirio", "prefirio", "advirtio", "convirtio", "midio", "estremecio", "retrocedio"]
_IO_INEQUIVOCOS = [p for p in _IO_INEQUIVOCOS if p.endswith("io")]

# Sustantivos que comparten forma con un pretérito: «un suspiró» → «un suspiro».
_SUSTANTIVO_DE_PRETERITO = {
    "suspiró": "suspiro",
    "pasó": "paso",
    "cambió": "cambio",
    "tragó": "trago",
    "posó": "poso",
    "fracasó": "fracaso",
    "brilló": "brillo",
    "barrió": "barrio",
    "silenció": "silencio",
    "gestó": "gesto",
    "murmulló": "murmullo",
    "giró": "giro",
    "gritó": "grito",
    "susurró": "susurro",
    "saltó": "salto",
    "intentó": "intento",
    "abrazó": "abrazo",
    "besó": "beso",
    "regresó": "regreso",
    "saludó": "saludo",
    "sollozó": "sollozo",
    "bostezó": "bostezo",
    "disparó": "disparo",
    "terminó": "término",
    "rió": "río",
    "envió": "envío",
    "desvió": "desvío",
    "pesó": "peso",
    "usó": "uso",
    "tiró": "tiro",
    "gastó": "gasto",
    "pagó": "pago",
    "apoyó": "apoyo",
    "retiró": "retiro",
    "marcó": "marco",
    "golpeó": "golpe",
    "cargó": "cargo",
    "reflejó": "reflejo",
    "destelló": "destello",
}

_DETERMINANTES_FUERTES = {
    "un",
    "su",
    "sus",
    "del",
    "al",
    "este",
    "ese",
    "aquel",
    "mi",
    "tu",
    "nuestro",
    "vuestro",
    "cada",
    "ningún",
    "algún",
    "otro",
    "primer",
    "último",
    "dicho",
}
_DETERMINANTES_TRAS_VERBO = {
    "su", "sus", "la", "las", "el", "los", "un", "una", "unos", "unas", "mi", "mis",
    "tu", "tus", "nuestra", "nuestro", "aquel", "aquella", "esa", "ese", "esta", "este",
}
_ADJETIVOS_PUENTE = {
    "leve",
    "largo",
    "breve",
    "pequeño",
    "gran",
    "profundo",
    "último",
    "primer",
    "nuevo",
    "fuerte",
    "suave",
    "débil",
    "ligero",
    "rápido",
    "lento",
    "sonoro",
    "ahogado",
    "cansado",
    "mal",
    "buen",
}

# Palabras que delante de la forma ambigua indican sustantivo, no verbo.
_ANTE_SUSTANTIVO = _DETERMINANTES_FUERTES | {
    "el",
    "los",
    "la",
    "las",
    "una",
    "de",
    "en",
    "con",
    "por",
    "sin",
    "a",
    "para",
    "sobre",
    "tras",
    "cuyo",
    "lo",
}

_FUNCIONALES_CAPITALIZADAS = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "y",
    "pero",
    "luego",
    "entonces",
    "después",
    "cuando",
    "mientras",
    "si",
    "no",
    "yo",
    "tú",
    "que",
    "qué",
    "por",
    "con",
    "sin",
    "de",
    "en",
    "ahora",
    "hoy",
    "siempre",
    "nunca",
    "aquí",
    "ya",
    "así",
    "solo",
    "también",
    "todavía",
    "aún",
    "tampoco",
    "casi",
    "apenas",
    "o",
    "ni",
    "pues",
    "porque",
    "como",
    "te",
    "me",
    "lo",
    "le",
    "nos",
    "os",
    "les",
    "se",
}

_ADJETIVOS_PUENTE |= {
    "mismo",
    "siguiente",
    "segundo",
    "tercer",
    "otro",
    "enorme",
    "pesado",
    "corto",
    "único",
    "verdadero",
    "simple",
    "torpe",
    "firme",
    "mero",
    "mejor",
    "peor",
    "propio",
    "extraño",
    "súbito",
    "brusco",
    "repentino",
}


def _construir_ambiguos(forma_rio: str) -> dict[str, str]:
    mapa = {verbo[:-2] + "o": verbo[:-2] + "ó" for verbo in _AR_AMBIGUOS if verbo.endswith("ar")}
    mapa.update(_AMBIGUOS_EXTRA)
    # reír: «río» siempre es ambiguo (sustantivo). «rio» solo es error si la
    # obra decide escribir el pretérito con tilde, como pide el informe.
    mapa["río"] = forma_rio
    if forma_rio != "rio":
        mapa["rio"] = forma_rio
    return mapa


def _construir_inequivocos() -> dict[str, str]:
    mapa = {verbo[:-2] + "o": verbo[:-2] + "ó" for verbo in _SIN_AMBIGUEDAD}
    mapa.update({forma: forma[:-1] + "ó" for forma in _IO_INEQUIVOCOS})
    return mapa


_PALABRA = re.compile(r"[^\W\d_]+", re.UNICODE)
_INICIO_ORACION = re.compile(r"(?:^|[.!?…»\"”]\s+|\n\s*|—\s*|[¿¡])$")


def _token_previo(texto: str, inicio: int) -> tuple[str, int]:
    """Devuelve la palabra anterior en la misma oración (o "") y su inicio."""

    tramo = texto[max(0, inicio - 80) : inicio]
    coincidencia = re.search(r"([^\W\d_]+)[ \t]+$", tramo, re.UNICODE)
    if not coincidencia:
        return "", -1
    return coincidencia.group(1), inicio - len(tramo) + coincidencia.start(1)


def _token_siguiente(texto: str, fin: int) -> str:
    coincidencia = re.match(r"[ \t]+([^\W\d_]+)", texto[fin : fin + 60], re.UNICODE)
    return coincidencia.group(1) if coincidencia else ""


def _inicia_oracion(texto: str, inicio: int) -> bool:
    return bool(_INICIO_ORACION.search(texto[max(0, inicio - 4) : inicio]))


def _es_nombre(palabra: str, texto: str, inicio: int, ctx: Contexto) -> bool:
    if not palabra:
        return False
    if es_palabra_glosario(palabra, ctx.glosario):
        return True
    if not palabra[:1].isupper() or palabra.casefold() in _FUNCIONALES_CAPITALIZADAS:
        return False
    return not _inicia_oracion(texto, inicio)


_FINALES_PRETERITO_IRREGULAR = ("uvo", "ijo", "izo", "uso", "ino", "iso", "udo", "ajo", "upo", "ujo")


def _parece_preterito(palabra: str) -> bool:
    minuscula = palabra.casefold()
    return (
        minuscula.endswith("ó")
        or minuscula in {"fue", "dio", "vio", "fueron", "dieron", "vieron"}
        or (len(minuscula) > 4 and minuscula.endswith(_FINALES_PRETERITO_IRREGULAR))
    )


_SUSTANTIVOS_FRECUENTES = {
    "silencio", "camino", "intento", "paso", "cambio", "apoyo", "abrazo", "beso",
    "grito", "giro", "salto", "llanto", "susurro", "regreso", "aviso", "trago",
    "gesto", "golpe", "suspiro", "respiro", "descanso", "juego", "baño", "viaje",
}


def _parece_conjugado(palabra: str) -> bool:
    return len(palabra) > 3 and (
        palabra.endswith(("ó", "é", "aba", "aban", "ían", "aron", "ieron"))
        or palabra in {"fue", "dio", "vio", "hizo", "tuvo", "puso", "dijo", "quiso"}
    )


def _tras_raya_de_atribucion(texto: str, inicio: int) -> bool:
    """«…? —contesto Mico»: la raya abre un inciso del narrador."""

    previo = texto[max(0, inicio - 4) : inicio]
    return bool(re.search(r"[.,!?…][ \t]+—$", previo))


@registrar
class PreteritoSinTilde:
    id = "TIL-003"
    nivel = Nivel.L2
    descripcion = "Pretéritos sin tilde (miro → miró, río → rió, continúo → continuó)."
    prioridad = 38
    por_defecto = True

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tildes.preteritos", True)):
            return
        forma_rio = str(ctx.config.obtener("tildes.forma_rio", "rió") or "rió")
        ambiguos = _construir_ambiguos(forma_rio)
        inequivocos = _construir_inequivocos()

        for match in _PALABRA.finditer(texto):
            palabra = match.group(0)
            minuscula = palabra.casefold()
            if minuscula in inequivocos:
                if es_palabra_glosario(palabra, ctx.glosario):
                    continue
                es_minuscula = palabra.islower()
                hallazgo = crear_hallazgo(
                    texto,
                    regla=self.id,
                    # Sin tilde no existe: si está en minúscula es mecánico.
                    nivel=Nivel.L1 if es_minuscula else Nivel.L2,
                    inicio=match.start(),
                    fin=match.end(),
                    sugerencia=preservar_caso(palabra, inequivocos[minuscula]),
                    confianza=0.96 if es_minuscula else 0.9,
                    nota="Pretérito sin tilde: la forma sin acento no existe.",
                )
                if hallazgo:
                    yield hallazgo
                continue

            if minuscula not in ambiguos:
                continue
            if es_palabra_glosario(palabra, ctx.glosario):
                continue
            confianza, motivo = self._evaluar(texto, match.start(), match.end(), ctx)
            if confianza <= 0:
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=Nivel.L2,
                inicio=match.start(),
                fin=match.end(),
                sugerencia=preservar_caso(palabra, ambiguos[minuscula]),
                confianza=confianza,
                nota=motivo,
            )
            if hallazgo:
                yield hallazgo

    def _evaluar(
        self, texto: str, inicio: int, fin: int, ctx: Contexto
    ) -> tuple[float, str]:
        previo, inicio_previo = _token_previo(texto, inicio)
        previo_min = previo.casefold()
        palabra_min = texto[inicio:fin].casefold()
        # Determinante o preposición delante: es sustantivo («Otro silencio»,
        # «Ese trago»), también cuando abre la oración en mayúscula.
        if previo_min in _ANTE_SUSTANTIVO:
            return 0.0, ""
        # Verbo conjugado delante: la forma ambigua es su complemento
        # («Buscó apoyo», «pidió cambio»).
        if previo_min not in {"se"} and _parece_conjugado(previo_min):
            return 0.0, ""
        if previo_min in {"se"}:
            return 0.9, "«se» + 1.ª persona no concuerda: es el pretérito."
        if previo_min in {"él", "ella", "usted"}:
            return 0.9, f"Sujeto «{previo}» en 3.ª persona: es el pretérito."
        if _tras_raya_de_atribucion(texto, inicio):
            return 0.9, "Inciso del narrador tras la raya: es el pretérito."
        if previo and _es_nombre(previo, texto, inicio_previo, ctx):
            return 0.9, f"Sujeto «{previo}» delante: es el pretérito."
        if (
            previo[:1].isupper()
            and previo_min not in _FUNCIONALES_CAPITALIZADAS
            and _inicia_oracion(texto, inicio_previo)
        ):
            return 0.82, f"Probable sujeto «{previo}» al inicio de la oración: es el pretérito."
        if previo_min == "y":
            antes, _ = _token_previo(texto, inicio_previo)
            if _parece_preterito(antes):
                return 0.85, f"Coordinado con «{antes}»: también va en pretérito."
        if inicio_previo >= 0:
            articulo, _ = _token_previo(texto, inicio_previo)
            if (
                articulo.casefold() in {"el", "la"}
                and previo.islower()
                and previo_min not in _ADJETIVOS_PUENTE
            ):
                # «el tenso silencio», «el maldito camino»: con sustantivos muy
                # frecuentes lo normal es adjetivo + sustantivo.
                confianza = 0.6 if palabra_min in _SUSTANTIVOS_FRECUENTES else 0.75
                return confianza, (
                    f"Tras el sujeto «{articulo} {previo}» parece el pretérito; "
                    "revisa que no sea un sustantivo."
                )
        siguiente = _token_siguiente(texto, fin)
        if (
            _inicia_oracion(texto, inicio)
            and siguiente
            and siguiente[:1].isupper()
            and siguiente.casefold() not in _FUNCIONALES_CAPITALIZADAS
        ):
            return 0.88, f"Verbo antepuesto al sujeto «{siguiente}»: es el pretérito."
        return 0.0, ""


@registrar
class SustantivoConTildeDePreterito:
    id = "TIL-004"
    nivel = Nivel.L2
    descripcion = "Sustantivos escritos como pretérito tras determinante (un suspiró → un suspiro)."
    prioridad = 39
    por_defecto = True

    _patron = re.compile(r"\b(?P<palabra>[^\W\d_]+ó)\b", re.UNICODE)
    _previas = re.compile(r"(?:([^\W\d_]+)[ \t]+)?([^\W\d_]+)[ \t]+$", re.UNICODE)

    def aplicar(self, texto: str, ctx: Contexto) -> Iterator[Hallazgo]:
        if not bool(ctx.config.obtener("tildes.preteritos", True)):
            return
        for match in self._patron.finditer(texto):
            sustantivo = _SUSTANTIVO_DE_PRETERITO.get(match.group("palabra").casefold())
            if sustantivo is None:
                continue
            previas = self._previas.search(texto[max(0, match.start() - 60) : match.start()])
            if previas is None:
                continue
            palabra = match.group("palabra")
            # Palabra inmediata y, si es un adjetivo puente, la anterior.
            det, adj = previas.group(2), ""
            if det.casefold() in _ADJETIVOS_PUENTE and previas.group(1):
                det, adj = previas.group(1), det
            etiqueta = det
            det = det.casefold()
            siguiente = _token_siguiente(texto, match.end("palabra")).casefold()
            # «cuando este posó su mano»: con un determinante o posesivo
            # detrás es el verbo, y «este» era pronombre.
            if siguiente in _DETERMINANTES_TRAS_VERBO:
                continue
            if det in _DETERMINANTES_FUERTES:
                confianza = 0.92 if not adj else 0.86
                nota = f"Tras «{etiqueta}» va el sustantivo «{sustantivo}»."
            elif det == "el" and not adj:
                confianza = 0.7
                nota = (
                    f"Tras «el» suele ir el sustantivo «{sustantivo}», pero revisa si "
                    f"quería decir «él {palabra}» (pronombre sin tilde)."
                )
            else:
                continue
            hallazgo = crear_hallazgo(
                texto,
                regla=self.id,
                nivel=self.nivel,
                inicio=match.start("palabra"),
                fin=match.end("palabra"),
                sugerencia=preservar_caso(palabra, sustantivo),
                confianza=confianza,
                nota=nota,
            )
            if hallazgo:
                yield hallazgo

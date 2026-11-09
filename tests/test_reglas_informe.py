"""Reglas añadidas a partir del informe editorial (frases inventadas)."""

from __future__ import annotations

import pytest
from tests.conftest import aplicar_hallazgos, ejecutar_regla

from onirifix.config import Configuracion
from onirifix.modelo import Glosario, Nivel
from onirifix.reglas.diacriticas import subjuntivo_desde_futuro


def _corrige(regla: str, texto: str, **kwargs) -> str:
    return aplicar_hallazgos(ejecutar_regla(regla, texto, **kwargs), texto)


# ---------------------------------------------------------------------------
# Diálogo
# ---------------------------------------------------------------------------


def test_dia_006_verbo_en_linea_siguiente() -> None:
    texto = "—¿Dónde dejaste el mapa?\nPreguntó Lina de repente."
    hallazgos = ejecutar_regla("DIA-006", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].nivel is Nivel.L2
    assert aplicar_hallazgos(hallazgos, texto) == (
        "—¿Dónde dejaste el mapa? —preguntó Lina de repente."
    )


def test_dia_006_elimina_el_punto_de_cierre() -> None:
    assert _corrige("DIA-006", "—Ya basta. Dijo Tomás.") == "—Ya basta —dijo Tomás."
    assert _corrige("DIA-006", "—Ya basta.\nDijo Tomás.") == "—Ya basta —dijo Tomás."


def test_dia_006_respeta_narracion_e_incisos_cerrados() -> None:
    assert ejecutar_regla("DIA-006", "Tomás calló.\nDijo que no.") == []
    assert ejecutar_regla("DIA-006", "—Hola —dijo él—. Preguntó por ti.") == []
    assert ejecutar_regla("DIA-006", "—Basta. —dijo Tomás.") == []


def test_dia_007_cierra_inciso_antes_de_reanudar() -> None:
    texto = "—Llegas tarde —murmuró Lina. ¿Dónde estabas?"
    assert _corrige("DIA-007", texto) == "—Llegas tarde —murmuró Lina—. ¿Dónde estabas?"
    texto = "—Corre —gritó Tomás, sin aliento. ¡Ya vienen!"
    assert _corrige("DIA-007", texto) == "—Corre —gritó Tomás, sin aliento—. ¡Ya vienen!"


def test_dia_007_no_toca_inciso_correcto_ni_narracion() -> None:
    assert ejecutar_regla("DIA-007", "—Llegas tarde —murmuró Lina—. ¿Dónde estabas?") == []
    assert ejecutar_regla("DIA-007", "—Llegas tarde —murmuró Lina. Luego se sentó.") == []


def test_tip_007_guion_simple_inicial() -> None:
    texto = "-Serán tres monedas.\n-¿Tres?\n- elemento de lista"
    assert _corrige("TIP-007", texto) == "—Serán tres monedas.\n—¿Tres?\n- elemento de lista"


# ---------------------------------------------------------------------------
# Tipografía
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Y.… nada más.", "Y… nada más."),
        ("¿No?…. Bueno.", "¿No?… Bueno."),
        ("Espera……", "Espera…"),
    ],
)
def test_tip_011_elipsis_corrupta(texto: str, esperado: str) -> None:
    hallazgos = ejecutar_regla("TIP-011", texto)
    assert hallazgos and all(h.nivel is Nivel.L1 for h in hallazgos)
    assert aplicar_hallazgos(hallazgos, texto) == esperado


def test_tip_012_cierre_invertido() -> None:
    assert _corrige("TIP-012", "—¡Perdón, de verdad ¡") == "—¡Perdón, de verdad!"
    assert _corrige("TIP-012", "¿Qué hora es¿") == "¿Qué hora es?"
    assert ejecutar_regla("TIP-012", "¡Hola! ¡Adiós!") == []


def test_tip_013_apertura_faltante_es_solo_aviso() -> None:
    hallazgos = ejecutar_regla("TIP-013", "Vienes mañana? ¡Claro! Qué alegría!")
    assert [h.original for h in hallazgos] == ["?", "!"]
    assert all(h.nivel is Nivel.L3 and h.sugerencia is None for h in hallazgos)
    assert ejecutar_regla("TIP-013", "¿Vienes? ¿De verdad?!") == []


def test_tip_014_comillas_inglesas_l2_baja_confianza() -> None:
    hallazgos = ejecutar_regla("TIP-014", "Pensó “no puede ser” y siguió.")
    assert len(hallazgos) == 1
    assert hallazgos[0].nivel is Nivel.L2
    assert hallazgos[0].confianza < 0.9
    assert hallazgos[0].sugerencia == "«no puede ser»"


def test_tip_014_respeta_estilo_ingles() -> None:
    config = Configuracion({"tipografia": {"comillas": "“”"}})
    assert ejecutar_regla("TIP-014", "Dijo “sí”.", config=config) == []


def test_tip_015_espacios_dentro_de_signos() -> None:
    assert _corrige("TIP-015", "¿ Vienes? ¡ Ya! « hola »") == "¿Vienes? ¡Ya! «hola»"
    # «¡» pegado a la palabra anterior es un cierre mal escrito: no se toca.
    assert ejecutar_regla("TIP-015", "Levantó el martillo¡ y calló.") == []


# ---------------------------------------------------------------------------
# hacía / hacia
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    [
        "Lina giró hacía el muelle.",
        "Tomás se inclinó hacía adelante.",
        "La mirada se le fue hacía ella.",
        "Corrió hacía allí sin pensar.",
    ],
)
def test_til_001_hacia_mal_acentuada(texto: str) -> None:
    hallazgos = ejecutar_regla("TIL-001", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == "hacia"
    assert hallazgos[0].nivel is Nivel.L2


def test_til_001_no_toca_hacia_verbo() -> None:
    assert ejecutar_regla("TIL-001", "Hacía frío en el puerto.") == []
    assert ejecutar_regla("TIL-001", "Lo hacía todo con calma.") == []
    assert ejecutar_regla("TIL-001", "Ella hacía pan los domingos.") == []


# ---------------------------------------------------------------------------
# Pretéritos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "original", "sugerencia"),
    [
        ("Lina río junto a ellos.", "río", "rió"),
        ("Rio Tomás con ganas.", "Rio", "Rió"),
        ("El viejo se detuvo y señalo la puerta.", "señalo", "señaló"),
        ("Contesto Lina sin dudar.", "Contesto", "Contestó"),
        ("—¿Vienes? —pregunto Tomás.", "pregunto", "preguntó"),
        ("Ella suspiro despacio.", "suspiro", "suspiró"),
        ("Tomás continúo hablando.", "continúo", "continuó"),
        ("El cuervo se poso en la rama.", "poso", "posó"),
    ],
)
def test_til_003_preterito_ambiguo_con_contexto(texto: str, original: str, sugerencia: str) -> None:
    hallazgos = ejecutar_regla("TIL-003", texto)
    assert [(h.original, h.sugerencia) for h in hallazgos] == [(original, sugerencia)]
    assert hallazgos[0].nivel is Nivel.L2


@pytest.mark.parametrize(
    "texto",
    [
        "Cruzaron el río a nado.",
        "Yo miro el mar cada tarde.",
        "Dio el primer paso.",
        "Soltó un leve suspiro.",
        "Ahora paso por tu casa.",
    ],
)
def test_til_003_calla_sin_contexto_suficiente(texto: str) -> None:
    assert ejecutar_regla("TIL-003", texto) == []


def test_til_003_inequivocos_son_l1() -> None:
    hallazgos = ejecutar_regla("TIL-003", "Tomás conto las monedas y respondio tarde.")
    assert [(h.sugerencia, h.nivel) for h in hallazgos] == [
        ("contó", Nivel.L1),
        ("respondió", Nivel.L1),
    ]


def test_til_003_forma_rio_configurable() -> None:
    config = Configuracion({"tildes": {"forma_rio": "rio"}})
    assert ejecutar_regla("TIL-003", "Rio Tomás con ganas.", config=config) == []
    hallazgos = ejecutar_regla("TIL-003", "Lina río con ganas.", config=config)
    assert hallazgos[0].sugerencia == "rio"


def test_til_003_respeta_glosario() -> None:
    glosario = Glosario(nombres=frozenset({"Paso"}))
    assert ejecutar_regla("TIL-003", "Lina Paso llegó.", glosario=glosario) == []


@pytest.mark.parametrize(
    ("texto", "sugerencia"),
    [
        ("vivían en un barrió humilde", "barrio"),
        ("perdieron algo de su brilló", "brillo"),
        ("fue un gestó mínimo", "gesto"),
        ("soltó un leve suspiró", "suspiro"),
    ],
)
def test_til_004_sustantivo_tras_determinante(texto: str, sugerencia: str) -> None:
    hallazgos = ejecutar_regla("TIL-004", texto)
    assert [h.sugerencia for h in hallazgos] == [sugerencia]


def test_til_004_el_es_ambiguo_y_tiene_baja_confianza() -> None:
    hallazgos = ejecutar_regla("TIL-004", "el terminó la carta")
    assert hallazgos[0].confianza < 0.9
    assert "él" in hallazgos[0].nota
    assert ejecutar_regla("TIL-004", "Él terminó la carta.") == []
    assert ejecutar_regla("TIL-004", "Tomás terminó la carta.") == []


# ---------------------------------------------------------------------------
# Diacríticas y subjuntivo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Se lo que piensas.", "Sé lo que piensas."),
        ("No se que decir.", "No sé que decir."),
        ("—Si, eso dijo.", "—Sí, eso dijo."),
        ("pues el ya lo sabía", "pues él ya lo sabía"),
        ("se acercaban a el para oírlo", "se acercaban a él para oírlo"),
        ("—Lina, ya sabes que hacer.", "—Lina, ya sabes qué hacer."),
        ("no sé cuanto tiempo pasó", "no sé cuánto tiempo pasó"),
    ],
)
def test_til_005_diacriticas(texto: str, esperado: str) -> None:
    resultado = _corrige("TIL-005", texto)
    # «No se que decir» también debería llevar «qué»; la regla solo cubre «sé».
    assert resultado == esperado


@pytest.mark.parametrize(
    "texto",
    ["Se fue temprano.", "Si llueve, no salgo.", "el perro y el gato", "Tengo que hacer algo."],
)
def test_til_005_no_toca_usos_correctos(texto: str) -> None:
    assert ejecutar_regla("TIL-005", texto) == []


@pytest.mark.parametrize(
    ("texto", "sugerencia"),
    [
        ("miró a los demás como si esperará una respuesta", "esperara"),
        ("Antes de que Tomás estallará, ella habló.", "estallara"),
        ("respiraba como si le faltará el aire", "faltara"),
        ("bajó la voz para evitar que se escuchará", "escuchara"),
        ("como si tendrá miedo", "tuviera"),
        ("hasta que llegarán los demás", "llegaran"),
    ],
)
def test_til_006_futuro_por_subjuntivo(texto: str, sugerencia: str) -> None:
    hallazgos = ejecutar_regla("TIL-006", texto)
    assert [h.sugerencia for h in hallazgos] == [sugerencia]
    assert hallazgos[0].nivel is Nivel.L2


def test_til_006_no_toca_subjuntivo_correcto() -> None:
    assert ejecutar_regla("TIL-006", "como si fuera poco") == []
    assert ejecutar_regla("TIL-006", "Mañana esperará en la puerta.") == []


def test_subjuntivo_desde_futuro() -> None:
    assert subjuntivo_desde_futuro("temerá") == "temiera"
    assert subjuntivo_desde_futuro("hará") == "hiciera"
    assert subjuntivo_desde_futuro("valdrán") is None


# ---------------------------------------------------------------------------
# Ortografía y repetición
# ---------------------------------------------------------------------------


def test_ort_003_repeticion_enfatica_baja_confianza() -> None:
    hallazgos = ejecutar_regla("ORT-003", "la la casa quedaba muy muy lejos")
    confianzas = {h.original: h.confianza for h in hallazgos}
    assert confianzas["la la"] >= 0.9
    assert confianzas["muy muy"] < 0.9


def test_ort_004_mayuscula_tras_punto() -> None:
    texto = "Parecía molesto. casi cansado. Llegó el Sr. ramos, etc. y más."
    hallazgos = ejecutar_regla("ORT-004", texto)
    assert [h.original for h in hallazgos] == ["c"]
    assert aplicar_hallazgos(hallazgos, texto).startswith("Parecía molesto. Casi")


def test_rep_005_parrafo_duplicado_consecutivo() -> None:
    texto = (
        "El faro giraba sobre la costa gris.\n\n"
        "El faro giraba sobre la costa gris.\n\n"
        "Fin."
    )
    hallazgos = ejecutar_regla("REP-005", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].nivel is Nivel.L2
    assert aplicar_hallazgos(hallazgos, texto) == "El faro giraba sobre la costa gris.\n\nFin."


def test_rep_005_oracion_duplicada() -> None:
    texto = "Lina sonrió sin decir nada. Lina sonrió sin decir nada. Luego salió."
    assert _corrige("REP-005", texto) == "Lina sonrió sin decir nada. Luego salió."


def test_rep_005_no_toca_repeticiones_lejanas() -> None:
    texto = "El faro giraba sin descanso.\n\nOtra cosa.\n\nEl faro giraba sin descanso."
    assert ejecutar_regla("REP-005", texto) == []


def test_rep_006_residuos_de_asistente() -> None:
    texto = (
        "¡Qué excelente adición! Aquí tienes la ampliación del fragmento:\n"
        "(Contexto anterior...)\n"
        "Escena ampliada (Capítulo 2)\n"
        "Todo estaba en calma. [TODO revisar]"
    )
    hallazgos = ejecutar_regla("REP-006", texto)
    originales = [h.original for h in hallazgos]
    assert "¡Qué excelente adición" in originales
    assert "Aquí tienes" in originales
    assert "(Contexto anterior...)" in originales
    assert "Escena ampliada (Capítulo 2)" in originales
    assert "Todo" not in originales  # «Todo» español no es un marcador
    assert all(h.nivel is Nivel.L3 and h.sugerencia is None for h in hallazgos)


def test_rep_006_terminos_vetados_configurables() -> None:
    config = Configuracion({"residuos_borrador": {"vetados": ["jeans"], "patrones": ["kokoro"]}})
    hallazgos = ejecutar_regla("REP-006", "Llevaba jeans y hablaba del kokoro.", config=config)
    assert {h.original for h in hallazgos} == {"jeans", "kokoro"}

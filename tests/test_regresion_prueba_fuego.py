"""Regresiones de la prueba de fuego con un manuscrito real.

Todas las frases son inventadas: reproducen la forma de los falsos positivos
(y de los aciertos) observados, nunca el texto de la obra.
"""

from __future__ import annotations

from tests.conftest import aplicar_hallazgos, ejecutar_regla

from onirifix.config import Configuracion


def _ids(regla: str, texto: str, **kw) -> list[str]:
    return [h.sugerencia or "" for h in ejecutar_regla(regla, texto, **kw)]


# --- TIL-003: sustantivos y verbos ambiguos -------------------------------


def test_til_003_determinante_en_mayuscula_es_sustantivo() -> None:
    assert _ids("TIL-003", "Ese trago le quemó la garganta.") == []
    assert _ids("TIL-003", "Otro silencio llenó la cocina.") == []


def test_til_003_tras_verbo_conjugado_es_complemento() -> None:
    assert _ids("TIL-003", "Buscó apoyo en la barandilla del puente.") == []


def test_til_003_trono_y_bajo_no_son_verbos() -> None:
    assert _ids("TIL-003", "La reina subió al trono de cristal.") == []
    assert _ids("TIL-003", "Se escondió bajo la mesa del capitán.") == []
    assert _ids("TIL-003", "Quedó un vacío en la despensa.") == []


def test_til_003_mantiene_aciertos() -> None:
    texto = "El día paso sin noticias del barco."
    assert aplicar_hallazgos(ejecutar_regla("TIL-003", texto), texto) == (
        "El día pasó sin noticias del barco."
    )


# --- TIL-001 / TIL-004 / TIL-005 ------------------------------------------


def test_til_001_hacia_con_determinante_tras_negacion() -> None:
    assert _ids("TIL-001", "Corrió, pero no hacia la salida del muelle.") == []


def test_til_004_verbo_con_posesivo_detras() -> None:
    assert _ids("TIL-004", "Calló cuando este posó su mano en la mesa.") == []


def test_til_004_mantiene_aciertos() -> None:
    assert _ids("TIL-004", "Soltó un suspiró largo.") == ["suspiro"]


def test_til_005_el_con_puntos_suspensivos_es_articulo() -> None:
    assert _ids("TIL-005", "Y entonces el… no, mejor no.") == []
    assert _ids("TIL-005", "Vio que el... bueno, da igual.") == []


def test_til_005_que_conjuncion_con_verbo_conjugado() -> None:
    texto = "Sabía que cambiar de rumbo ahora pondría en riesgo a todos."
    assert _ids("TIL-005", texto) == []


def test_til_005_mantiene_aciertos() -> None:
    assert _ids("TIL-005", "Ya no sabes que hacer.") == ["qué"]
    assert _ids("TIL-005", "Pensó que el ya lo sabía.") == ["él"]


# --- ORT-001: claves cortas ---------------------------------------------


def _config_ort() -> Configuracion:
    return Configuracion({"ortografia": {"correcciones": {"d": "de", "aun asi": "aún así"}}})


def test_ort_001_claves_cortas_no_tocan_siglas_ni_nombres() -> None:
    config = _config_ort()
    assert _ids("ORT-001", "Era un cazador de Rango D en el gremio.", config=config) == []
    assert _ids("ORT-001", "Leía a D'Artagnan junto al fuego.", config=config) == []
    assert _ids("ORT-001", "Firmado: J. D. Montes.", config=config) == []


def test_ort_001_claves_cortas_y_largas_siguen_funcionando() -> None:
    config = _config_ort()
    assert _ids("ORT-001", "La casa d la abuela.", config=config) == ["de"]
    assert _ids("ORT-001", "Aun asi, siguió.", config=config) == ["Aún así"]


# --- REP-006: residuos de borrador ----------------------------------------


def test_rep_006_formulas_dentro_de_un_parlamento() -> None:
    assert _ids("REP-006", "—Aquí tienes tu jarra —dijo el tabernero.") == []
    assert _ids("REP-006", "—Si quieres, puedo ayudarte con la vela.") == []


def test_rep_006_todo_gritado_no_es_marcador() -> None:
    assert _ids("REP-006", "—¡TODO LO QUE TENGO ES TUYO!") == []
    assert len(ejecutar_regla("REP-006", "TODO: revisar la escena del faro.")) == 1


def test_rep_006_formula_en_narracion_sigue_avisando() -> None:
    assert len(ejecutar_regla("REP-006", "Aquí tienes el capítulo revisado.")) == 1


# --- DIA-006 / DIA-007 ----------------------------------------------------


def test_dia_006_verbo_puro_de_habla_tiene_confianza_alta() -> None:
    texto = "—¿Vienes al puerto?\n\nPreguntó Lina sin mirarlo."
    hallazgos = ejecutar_regla("DIA-006", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].confianza >= 0.9
    assert aplicar_hallazgos(hallazgos, texto) == "—¿Vienes al puerto? —preguntó Lina sin mirarlo."


def test_dia_006_verbo_narrativo_baja_la_confianza() -> None:
    texto = "—Vale.\n\nSoltó el aire de golpe y se sentó."
    hallazgos = ejecutar_regla("DIA-006", texto)
    assert all(h.confianza < 0.9 for h in hallazgos)


def test_dia_006_no_une_tras_narracion_cerrada() -> None:
    texto = "—Hola —dijo Ana, sonriendo.\n\nPreguntó luego por el barco."
    assert ejecutar_regla("DIA-006", texto) == []


def test_dia_007_cierra_inciso_antes_de_reanudar_con_raya() -> None:
    texto = "—Por aquí —contestó Bruno, señalando el muelle. —El barco sale al alba."
    hallazgos = ejecutar_regla("DIA-007", texto)
    assert aplicar_hallazgos(hallazgos, texto) == (
        "—Por aquí —contestó Bruno, señalando el muelle—. El barco sale al alba."
    )


def test_dia_007_no_toca_narracion_sin_verbo_de_habla() -> None:
    texto = "—Por aquí —el muelle crujió. —Corre."
    assert ejecutar_regla("DIA-007", texto) == []


def test_til_003_adjetivo_mas_sustantivo_frecuente_baja() -> None:
    hallazgos = ejecutar_regla("TIL-003", "Rompió el tenso silencio de la sala.")
    assert all(h.confianza < 0.7 for h in hallazgos)


def test_dia_001_modo_rae_quita_el_punto_y_conserva_exclamacion() -> None:
    config = Configuracion({"dialogos": {"rae_estricto": True}})
    texto = "—Hay sitio. — Añadió Bruno.\n\n—¡Fuera! — Bramó Lina."
    assert aplicar_hallazgos(ejecutar_regla("DIA-001", texto, config=config), texto) == (
        "—Hay sitio —añadió Bruno.\n\n—¡Fuera! —bramó Lina."
    )


def test_dia_003_conserva_interrogacion_exclamacion_y_suspensivos() -> None:
    config = Configuracion({"dialogos": {"rae_estricto": True}})
    assert ejecutar_regla("DIA-003", "—¿Vienes? —preguntó Lina.", config=config) == []
    assert ejecutar_regla("DIA-003", "—¡Corre! —gritó Bruno.", config=config) == []
    texto = "—Eso…— dijo ella. —Basta. —dijo él."
    assert aplicar_hallazgos(ejecutar_regla("DIA-003", texto, config=config), texto) == (
        "—Eso… —dijo ella. —Basta —dijo él."
    )

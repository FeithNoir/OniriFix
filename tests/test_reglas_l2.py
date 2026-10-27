"""Pruebas de tildes, homófonos, ortografía y consistencia."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import aplicar_hallazgos, ejecutar_regla

from onirifix.config import Configuracion
from onirifix.linguistica import CorrectorOrtografico
from onirifix.modelo import Contexto, Documento, Glosario, Nivel
from onirifix.nucleo.registro_reglas import descubrir_reglas


def test_til_001_hacia_frio() -> None:
    texto = "hacia frío en la calle"
    hallazgos = ejecutar_regla("TIL-001", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == "hacía"
    assert hallazgos[0].nivel is Nivel.L2


def test_til_001_no_confunde_preposicion() -> None:
    assert ejecutar_regla("TIL-001", "caminaba hacia el norte") == []
    assert ejecutar_regla("TIL-001", "hacia la puerta") == []


def test_til_001_preserva_mayuscula() -> None:
    hallazgos = ejecutar_regla("TIL-001", "Hacia frío aquella tarde")
    assert hallazgos[0].sugerencia == "Hacía"


def test_til_001_se_puede_desactivar() -> None:
    config = Configuracion({"tildes": {"hacia": False}})
    assert ejecutar_regla("TIL-001", "hacia frío", config=config) == []


def test_til_002_futuro_truncado() -> None:
    texto = "Mañana mirá el cielo."
    hallazgos = ejecutar_regla("TIL-002", texto)
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == "mirará"
    assert aplicar_hallazgos(hallazgos, texto) == "Mañana mirará el cielo."


def test_til_002_respeta_voseo() -> None:
    config = Configuracion({"tildes": {"permitir_voseo": True}})
    assert ejecutar_regla("TIL-002", "Mirá el cielo.", config=config) == []


def test_til_002_respeta_palabras_validas() -> None:
    assert ejecutar_regla("TIL-002", "Está aquí.") == []


def test_til_002_respeta_glosario() -> None:
    glosario = Glosario(terminos=frozenset({"Mochá"}))
    assert (
        ejecutar_regla("TIL-002", "Mochá vive aquí.", glosario=glosario) == []
    )


def test_hom_001_haber_si() -> None:
    texto = "haber si vienes"
    hallazgos = ejecutar_regla("HOM-001", texto)
    assert len(hallazgos) == 1
    assert aplicar_hallazgos(hallazgos, texto) == "a ver si vienes"


def test_hom_001_preserva_mayuscula() -> None:
    hallazgos = ejecutar_regla("HOM-001", "Haber si vienes")
    assert hallazgos[0].sugerencia == "A ver"


def test_hom_002_a_ver_participio() -> None:
    texto = "a ver sido un error"
    hallazgos = ejecutar_regla("HOM-002", texto)
    assert len(hallazgos) == 1
    assert aplicar_hallazgos(hallazgos, texto) == "haber sido un error"


def test_ort_001_correcciones_explicitas() -> None:
    texto = "q xq tmb"
    hallazgos = ejecutar_regla("ORT-001", texto)
    assert len(hallazgos) == 3
    assert aplicar_hallazgos(hallazgos, texto) == "que porque también"


def test_ort_001_mapa_vacio() -> None:
    config = Configuracion({"ortografia": {"correcciones": {}}})
    assert ejecutar_regla("ORT-001", "q", config=config) == []


def test_ort_002_sin_corrector_no_hace_nada() -> None:
    assert ejecutar_regla("ORT-002", "palabra inventada") == []


def test_ort_002_lista_de_palabras(tmp_path: Path) -> None:
    lista = tmp_path / "palabras.txt"
    lista.write_text("hola\nmundo\n", encoding="utf-8")
    corrector = CorrectorOrtografico(lista_palabras=lista)
    config = Configuracion()
    contexto = Contexto(
        config=config,
        glosario=Glosario(),
        corrector=corrector,
        documento=Documento(ruta=Path("x.md"), texto="holaa"),
    )
    reglas = {r.id: r for r in descubrir_reglas()}
    hallazgos = list(reglas["ORT-002"].aplicar("holaa", contexto))
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == "hola"


def test_ort_003_palabra_repetida() -> None:
    texto = "La la ciudad"
    hallazgos = ejecutar_regla("ORT-003", texto)
    assert len(hallazgos) == 1
    assert aplicar_hallazgos(hallazgos, texto) == "La ciudad"


def test_con_001_variante_registrada() -> None:
    glosario = Glosario(variantes={"onirium": "Oniriums"})
    texto = "Onirium es el mundo"
    hallazgos = ejecutar_regla("CON-001", texto, glosario=glosario)
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == "Oniriums"
    assert hallazgos[0].confianza == 0.97


def test_con_001_sin_variantes() -> None:
    assert ejecutar_regla("CON-001", "Onirium") == []


def test_con_002_capitalizacion() -> None:
    glosario = Glosario(nombres=frozenset({"Feith Noir"}))
    texto = "feith noir llegó."
    hallazgos = ejecutar_regla("CON-002", texto, glosario=glosario)
    assert len(hallazgos) == 1
    assert hallazgos[0].sugerencia == "Feith Noir"


def test_con_002_no_corrige_nombres_sin_senal() -> None:
    glosario = Glosario(nombres=frozenset({"Mico"}))
    assert ejecutar_regla("CON-002", "mico llegó.", glosario=glosario) == []


def test_con_002_respeta_interruptores() -> None:
    config = Configuracion({"consistencia": {"incluir_personajes": False}})
    glosario = Glosario(nombres=frozenset({"Feith Noir"}))
    assert (
        ejecutar_regla("CON-002", "feith noir", config=config, glosario=glosario)
        == []
    )

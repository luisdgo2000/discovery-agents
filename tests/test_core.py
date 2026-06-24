"""Pruebas del núcleo determinista v2 (unittest stdlib → corre en Python 3.9+ sin pytest)."""
import json
import os
import shutil
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(RAIZ, "inputs", "caso_demo")

# Workspace temporal para TODAS las pruebas (no ensuciar work/ real).
_TMP = tempfile.mkdtemp(prefix="discovery_test_")
os.environ["DISCOVERY_WORK_ROOT"] = _TMP

from mcp_server import consolidator, workspace  # noqa: E402  (tras fijar el env)
from mcp_server.artefactos.docx_export import docx_disponible, exportar_docx  # noqa: E402
from mcp_server.artefactos.mermaid import generar_diagramas  # noqa: E402
from mcp_server.artefactos.tablas import generar_tablas, matriz_trazabilidad  # noqa: E402
from mcp_server.discovery.assembler import ensamblar_discovery, recolectar_temas_faltantes  # noqa: E402
from mcp_server.discovery.fidelidad import verificar_fidelidad  # noqa: E402
from mcp_server.discovery.scorer import score_discovery  # noqa: E402
from mcp_server.discovery.template import schema_vacio  # noqa: E402
from mcp_server.extractors.excel import extract_excel  # noqa: E402
from mcp_server.extractors.manifest import build_manifest  # noqa: E402
from mcp_server.pipeline import construir_evidencia  # noqa: E402
from mcp_server.prompts import cargar_prompt, listar_prompts  # noqa: E402
from mcp_server.transcripts.cleaner import clean_transcript  # noqa: E402


def _discovery_completo():
    """Discovery tipado completo, para pruebas de Go."""
    d = schema_vacio()
    for k, v in d.items():
        if isinstance(v, str):
            d[k] = "valor de prueba [E001]"
    d["solicitante"] = {"nombre": "María Solís", "rol": "Gerente", "contacto": "msolis@x.com"}
    d["dueno_producto"] = {"nombre": "Carlos Vega", "rol": "PO", "contacto": "cvega@x.com"}
    d["equipo_desarrollador"] = [{"nombre": "Luis Mora", "rol": "Data Engineer", "contacto": "lm@x.com"}]
    d["expertos_datos"] = [{"nombre": "Juan Pérez", "especialidad": "SQL", "contacto": "jp@x.com"}]
    d["expertos_por_pais"] = [{"nombre": "Sofía Díaz", "pais": "CRI", "especialidad": "Pagos", "contacto": "sd@x.com"}]
    d["certificadores"] = [{"nombre": "Ana Rojas", "ambito": "REG"}]
    d["fuentes"] = [
        {"tabla": "TRX", "esquema": "dbo", "servidor": "SQLPROD01",
         "columnas": ["id", "monto", "fecha"], "librerias": "pyodbc",
         "volumetria": "400M/año", "frecuencia": "Diaria", "sensible": "No", "evidencia": "E001"},
    ]
    d["entidades"] = [{"nombre": "Transaccion", "descripcion": "x", "relaciones": ["Comercio"]},
                      {"nombre": "Comercio", "descripcion": "y", "relaciones": []}]
    d["dependencias"] = [{"descripcion": "Réplica", "tipo": "DBA", "responsable": "Infra", "estado": "abierta"}]
    d["impedimentos"] = [{"descripcion": "Acceso pendiente", "responsable": "TI", "plan": "RFC", "estado": "abierto"}]
    d["accesos"] = [{"recurso": "SQLREPL02", "solicitado_a": "DBA", "estado": "en curso"}]
    d["riesgos"] = [{"descripcion": "Bloqueos", "severidad": "alta", "responsable": "Equipo"}]
    d["supuestos"] = [{"descripcion": "Volumetría vigente", "validado_por": "Carlos"}]
    d["restricciones"] = [{"descripcion": "Ventana nocturna", "origen": "Operaciones"}]
    d["hipotesis"] = [{"enunciado": "H1", "criterio_validacion": "c", "experimento": "e"}]
    d["arquetipos_datamesh"] = [{"nombre": "Plazos", "dominio": "Pagos",
                                 "valor_de_negocio": "v", "reutiliza_fuentes": ["TRX"]}]
    d["brechas"] = ""
    d["veredicto"] = ""
    return d


# =============================================================================================
# P0 — Cleaner no destructivo + formatos reales de Teams
# =============================================================================================
class TestCleanerNoDestructivo(unittest.TestCase):
    def test_preserva_palabras_con_significado(self):
        casos = [
            ("Carlos Vega: Este servidor es el que tiene la réplica.", "Este servidor"),
            ("Juan Pérez: El tipo de datos de la columna es decimal.", "tipo de datos"),
            ("María Solís: Eso no es cierto, la carga ya existe en Bronce.", "no es cierto"),
            ("María Solís: Eso no es cierto, la carga ya existe en Bronce.", "ya existe"),
            ("Carlos Vega: Bueno saber que el catálogo está listo.", "Bueno saber"),
            ("María Solís: Sí, las fuentes ya están habilitadas.", "Sí,"),
        ]
        for entrada, conservar in casos:
            out = clean_transcript(entrada)["texto_limpio"]
            self.assertIn(conservar, out, f"Se perdió '{conservar}' en: {out}")

    def test_quita_interjecciones_y_muletillas_de_inicio(self):
        out = clean_transcript("Carlos Vega: Eh, bueno, este, la idea es entender mmm el flujo, ajá.")
        texto = out["segmentos"][0]["texto"]
        self.assertEqual(texto, "la idea es entender el flujo.")

    def test_original_accesible_por_segmento(self):
        r = clean_transcript("Carlos Vega: Eh, las fuentes fuentes están listas.")
        s = r["segmentos"][0]
        self.assertEqual(s["id"], "seg-001")
        self.assertIn("fuentes fuentes", s["original"])      # original intacto
        self.assertNotIn("fuentes fuentes", s["texto"])      # limpio consolidado

    def test_dedupe_solo_adyacente(self):
        texto = ("Ana: el corte es a fin de mes.\n"
                 "Ana: el corte es a fin de mes.\n"      # glitch adyacente: se elimina
                 "Luis: ok.\n"
                 "Ana: el corte es a fin de mes.\n")     # repetición legítima lejana: se conserva
        r = clean_transcript(texto)
        todo = r["texto_limpio"].lower()
        self.assertEqual(todo.count("el corte es a fin de mes"), 2)


class TestCleanerFormatosTeams(unittest.TestCase):
    def test_vtt_teams_atribuye_hablantes(self):
        vtt = ("WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n"
               "<v Carlos Vega>Las fuentes están en SQLPROD01.</v>\n\n"
               "00:00:04.500 --> 00:00:08.000\n"
               "<v Juan Pérez>Hay que replicar a otro servidor.</v>\n")
        r = clean_transcript(vtt)
        self.assertEqual(r["formato_detectado"], "vtt_teams")
        self.assertEqual(r["hablantes"], ["Carlos Vega", "Juan Pérez"])
        self.assertNotIn("<v", r["texto_limpio"])

    def test_docx_teams_no_filtra_timestamps(self):
        docx = ("Carlos Vega   0:15\nLas fuentes están en SQLPROD01.\n"
                "Juan Pérez   0:42\nPerfecto, replicamos a SQLREPL02.\n")
        r = clean_transcript(docx)
        self.assertEqual(r["formato_detectado"], "docx_teams")
        self.assertEqual(r["hablantes"], ["Carlos Vega", "Juan Pérez"])
        self.assertNotIn("0:15", r["texto_limpio"])
        self.assertNotIn("0:42", r["texto_limpio"])


# =============================================================================================
# P0 — Workspace persistente + evidencia bajo demanda
# =============================================================================================
class TestWorkspacePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(os.path.join(_TMP, "caso_demo"), ignore_errors=True)
        cls.index = construir_evidencia(DEMO)

    def test_indice_compacto_no_token_bomb(self):
        compacto = json.dumps(self.index, ensure_ascii=False)
        self.assertLess(len(compacto), 4000, "El índice debe ser compacto (~500 tokens)")
        self.assertEqual(self.index["total_items"], 3)
        self.assertEqual(len(self.index["fuentes_detectadas"]), 3)

    def test_evidencia_persistida_con_ids(self):
        ev_dir = os.path.join(_TMP, "caso_demo", "10_evidence")
        archivos = sorted(os.listdir(ev_dir))
        self.assertIn("index.json", archivos)
        self.assertTrue(any(a.startswith("E001") for a in archivos))

    def test_get_evidence_chunk(self):
        eid = next(i["id"] for i in self.index["items"] if i["tipo"] == "transcripcion")
        ch = workspace.get_evidence_chunk("caso_demo", eid, 0)
        self.assertIn("[seg-001]", ch["contenido"])
        self.assertGreaterEqual(ch["total_chunks"], 1)
        err = workspace.get_evidence_chunk("caso_demo", "E999")
        self.assertIn("error", err)

    def test_incrementalidad_destilado(self):
        pendientes = workspace.evidencias_sin_destilar("caso_demo")
        self.assertEqual(len(pendientes), 1)  # solo la transcripción
        workspace.save_state("caso_demo", f"20_destilado/D{pendientes[0]}.json",
                             json.dumps({"decisiones": []}))
        self.assertEqual(workspace.evidencias_sin_destilar("caso_demo"), [])

    def test_save_state_lista_blanca(self):
        with self.assertRaises(ValueError):
            workspace.save_state("caso_demo", "outputs/hack.md", "x")
        with self.assertRaises(ValueError):
            workspace.save_state("caso_demo", "../fuera.json", "{}")


# =============================================================================================
# P1 — Consolidador y detector de conflictos
# =============================================================================================
class TestConsolidador(unittest.TestCase):
    def test_parse_volumen(self):
        casos = [("400,000,000 / año", 400e6), ("400M", 400e6), ("300 millones", 300e6),
                 ("18M/año", 18e6), ("120,000 registros", 120e3), ("400.000.000", 400e6),
                 ("mucho", None), ("", None)]
        for texto, esperado in casos:
            self.assertEqual(consolidator.parse_volumen(texto), esperado, f"falló: {texto!r}")

    def test_detecta_conflicto_numerico(self):
        excel = [{"tabla": "TRX_ADQUIRENCIA", "volumetria": "400,000,000 / año"}]
        reunion = [{"tabla_o_fuente": "trx adquirencia", "volumetria": "300 millones",
                    "evidencia": "E003"}]
        conflictos = consolidator.detectar_conflictos(excel, reunion)
        self.assertEqual(len(conflictos), 1)
        self.assertEqual(conflictos[0]["diferencia_pct"], 25.0)

    def test_sin_conflicto_si_coincide(self):
        excel = [{"tabla": "TRX", "volumetria": "400M"}]
        reunion = [{"tabla_o_fuente": "TRX", "volumetria": "400 millones"}]
        self.assertEqual(consolidator.detectar_conflictos(excel, reunion), [])


# =============================================================================================
# P1 — Scorer tipado con validadores
# =============================================================================================
class TestScorerTipado(unittest.TestCase):
    def test_schema_vacio_da_nogo(self):
        s = score_discovery(schema_vacio())
        self.assertEqual(s["veredicto"], "No-Go")
        self.assertEqual(s["completitud_total"], 0.0)

    def test_completo_da_go(self):
        s = score_discovery(_discovery_completo())
        self.assertEqual(s["veredicto"], "Go")
        self.assertEqual(s["completitud_total"], 100.0)

    def test_volumetria_basura_no_cuenta(self):
        d = _discovery_completo()
        d["fuentes"][0]["volumetria"] = "bastante grande"   # sin números → inválida
        s = score_discovery(d)
        claves_pendientes = [b["clave"] for b in s["brechas"]]
        self.assertIn("volumetria", claves_pendientes)
        self.assertNotEqual(s["veredicto"], "Go")

    def test_persona_sin_nombre_no_cuenta(self):
        d = _discovery_completo()
        d["dueno_producto"] = {"nombre": "", "rol": "PO", "contacto": "x"}
        s = score_discovery(d)
        self.assertIn("dueno_producto", [b["clave"] for b in s["brechas"]])

    def test_fuente_sin_servidor_no_cuenta(self):
        d = _discovery_completo()
        d["fuentes"][0]["servidor"] = ""
        s = score_discovery(d)
        self.assertIn("servidor_origen", [b["clave"] for b in s["brechas"]])


# =============================================================================================
# P1/P2 — Assembler tipado, narrativa, artefactos
# =============================================================================================
class TestAssemblerArtefactos(unittest.TestCase):
    def test_renderiza_tabla_de_fuentes(self):
        res = ensamblar_discovery(_discovery_completo(), caso_de_uso="Caso X")
        self.assertIn("| Tabla |", res["markdown"])
        self.assertIn("TRX", res["markdown"])
        self.assertIn("SQLPROD01", res["markdown"])

    def test_integra_narrativa_del_redactor(self):
        res = ensamblar_discovery(_discovery_completo(), caso_de_uso="Caso X",
                                  redaccion_md="## Contexto\nNarrativa del consultor [E001].")
        self.assertIn("Narrativa del consultor", res["markdown"])
        self.assertIn("Anexos", res["markdown"])

    def test_diagramas_mermaid(self):
        diagramas = generar_diagramas(_discovery_completo(), "Caso X")
        self.assertIn("```mermaid", diagramas["flujo_datos.md"])
        self.assertIn("SQLPROD01", diagramas["flujo_datos.md"])
        self.assertIn("Pagos", diagramas["datamesh.md"])
        self.assertIn("erDiagram", diagramas["entidades_preliminar.md"])

    def test_tablas_y_trazabilidad(self):
        tablas = generar_tablas(_discovery_completo(),
                                {"decisiones_pendientes": [
                                    {"decision": "Definir corte", "decisor_sugerido": "PO",
                                     "urgencia": "alta"}]})
        self.assertIn("TRX", tablas["inventario_fuentes.md"])
        self.assertIn("Definir corte", tablas["matriz_decisiones.md"])
        self.assertIn("E001", tablas["matriz_trazabilidad.md"])


# =============================================================================================
# v3 — Dos vistas, temas faltantes, fidelidad y export docx
# =============================================================================================
class TestDosVistas(unittest.TestCase):
    def test_documento_tiene_parte_general_y_tecnica(self):
        md = ensamblar_discovery(_discovery_completo(), caso_de_uso="Caso X")["markdown"]
        self.assertIn("Parte I — Discovery inicial (general)", md)
        self.assertIn("Parte II — Discovery técnico (profundo)", md)
        self.assertIn("Cierre — Evaluación", md)

    def test_fuentes_muestran_columnas_y_librerias(self):
        md = ensamblar_discovery(_discovery_completo(), caso_de_uso="Caso X")["markdown"]
        self.assertIn("Columnas", md)       # encabezado de tabla de fuentes
        self.assertIn("Librerias", md)
        self.assertIn("pyodbc", md)


class TestTemasFaltantes(unittest.TestCase):
    def test_schema_vacio_genera_temas_faltantes(self):
        res = ensamblar_discovery(schema_vacio(), caso_de_uso="Caso X")
        self.assertGreater(len(res["temas_faltantes"]), 0)
        self.assertIn("Temas faltantes y deuda técnica", res["markdown"])

    def test_falta_objetivo_aparece_en_temas(self):
        d = _discovery_completo()
        d["objetivo"] = ""   # se desconoce el objetivo
        res = ensamblar_discovery(d, caso_de_uso="Caso X")
        puntos = " ".join(t["punto"] for t in res["temas_faltantes"]).lower()
        self.assertIn("objetivo", puntos)

    def test_supuesto_sin_validar_es_deuda(self):
        score = score_discovery(_discovery_completo())
        d = _discovery_completo()
        d["supuestos"] = [{"descripcion": "Volumetría asumida", "validado_por": ""}]
        temas = recolectar_temas_faltantes(score, d, None)
        tipos = {t["tipo"] for t in temas}
        self.assertIn("supuesto_no_validado", tipos)

    def test_inconsistencias_se_integran(self):
        score = score_discovery(_discovery_completo())
        inc = {"vacios_no_capturados_por_rubrica": ["Falta política de retención"],
               "decisiones_pendientes": [{"decision": "Definir corte", "decisor_sugerido": "PO",
                                          "urgencia": "alta"}]}
        temas = recolectar_temas_faltantes(score, _discovery_completo(), inc)
        puntos = " ".join(t["punto"] for t in temas)
        self.assertIn("retención", puntos)
        self.assertIn("Definir corte", puntos)


class TestFidelidad(unittest.TestCase):
    def test_campo_sin_cita_se_detecta(self):
        d = _discovery_completo()
        d["necesidad_negocio"] = "Resolver reportería manual"   # sin [E00x]
        fid = verificar_fidelidad(d, redaccion_md=None, index=None)
        etiquetas = " ".join(fid["campos_sin_cita"])
        self.assertIn("Problema de negocio", etiquetas)
        self.assertLess(fid["cobertura_pct"], 100.0)

    def test_cita_invalida_contra_indice(self):
        d = _discovery_completo()
        d["necesidad_negocio"] = "Algo respaldado [E999]"
        index = {"items": [{"id": "E001"}]}
        fid = verificar_fidelidad(d, redaccion_md=None, index=index)
        self.assertTrue(any(c["cita"].startswith("E999") for c in fid["citas_invalidas"]))

    def test_parrafo_narrativa_sin_cita(self):
        narr = ("Este es un párrafo largo que afirma un hecho de negocio sin citar ninguna "
                "evidencia que lo respalde, por lo que debería marcarse como no anclado.")
        fid = verificar_fidelidad(_discovery_completo(), redaccion_md=narr, index=None)
        self.assertEqual(len(fid["parrafos_sin_cita"]), 1)


class TestDocxExport(unittest.TestCase):
    def test_genera_docx_con_partes(self):
        if not docx_disponible():
            self.skipTest("python-docx no instalado")
        from docx import Document
        out = os.path.join(_TMP, "demo.docx")
        d = _discovery_completo()
        fid = verificar_fidelidad(d, redaccion_md=None, index={"items": [{"id": "E001"}]})
        ruta = exportar_docx(out, d, caso="Caso X", redaccion_md="## Contexto\nNarrativa [E001].",
                             fidelidad=fid, diagramas=generar_diagramas(d, "Caso X"))
        self.assertEqual(ruta, out)
        texto = "\n".join(p.text for p in Document(out).paragraphs)
        self.assertIn("Parte I — Discovery inicial (general)", texto)
        self.assertIn("Parte II — Discovery técnico (profundo)", texto)
        self.assertIn("Cobertura de evidencia", texto)


# =============================================================================================
# Básicos que se conservan
# =============================================================================================
class TestBasicos(unittest.TestCase):
    def test_manifest_clasifica(self):
        m = build_manifest(DEMO)
        self.assertEqual(m["total_items"], 3)
        self.assertTrue(all(i["modificado"] for i in m["items"]))  # metadatos presentes

    def test_excel_detecta_fuentes(self):
        data = extract_excel(os.path.join(DEMO, "fuentes", "fuentes_volumetria.xlsx"))
        self.assertEqual(len(data["fuentes_detectadas"]), 3)

    def test_todos_los_prompts_cargan(self):
        nombres = listar_prompts()
        self.assertIn("redactor-experto", nombres)
        for n in nombres:
            self.assertTrue(cargar_prompt(n).strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)

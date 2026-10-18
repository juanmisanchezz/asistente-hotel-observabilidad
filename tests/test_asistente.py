import unittest
from asistente import consultar_ticket, ejecutar_herramientas
from langchain_core.messages import AIMessage
from unittest.mock import patch

class TestAsistente(unittest.TestCase):
    def test_formato_invalido(self):
        resultado = consultar_ticket.invoke({"ticket_id": "hola"})
        self.assertEqual(resultado, "Formato no valido")

    def test_ticket_no_existe(self):
        resultado = consultar_ticket.invoke({"ticket_id": "T-999"})
        self.assertEqual(resultado, "Ese ticket no existe en nuestra base de datos")

    def test_limite_dos_herramientas(self):
        estado = { 
        "messages": [AIMessage(content="", tool_calls=[{"name": "consultar_ticket", "args": {"ticket_id": "T-100"}, "id": "1"}, {"name": "consultar_ticket", "args": {"ticket_id": "T-100"}, "id": "4"}, {"name": "consultar_ticket", "args": {"ticket_id": "T-100"}, "id": "2"}])],
        "llamadas_herramientas": 0,
        "errores": [],
        }
        resultado = ejecutar_herramientas(estado)
        self.assertEqual(resultado["llamadas_herramientas"], 2)
        self.assertEqual(len(resultado["messages"]), 3)
        self.assertIn("limite_agotado", resultado["errores"])

    def test_fallo_herramienta(self):
        # 1. PREPARAR: Claude pide UNA herramienta
        estado = {
            "messages": [AIMessage(content="", tool_calls=[{"name": "consultar_ticket", "args": {"ticket_id": "T-100"}, "id": "1"}])],
            "llamadas_herramientas": 0,
            "errores": [],
        }

        # 2. LLAMAR, pero con consultar_ticket cambiada por una falsa que explota
        with patch("asistente.consultar_ticket") as falsa:
            falsa.invoke.side_effect = Exception("se rompió")
            resultado = ejecutar_herramientas(estado)

        # 3. COMPARAR: no se rompió, devolvió el error controlado y lo apuntó
        self.assertIn("fallo_herramienta", resultado["errores"])
        self.assertEqual(resultado["messages"][0].content, "Error controlado. No se obtuvo información.")

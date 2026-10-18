# Asistente del hotel: chatbot que decide si contesta o usa una herramienta

import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
import json
from trazas import crear_config, enviar, cargar_prompt

# Cargar la clave y crear el modelo (igual que en la 1b)
load_dotenv()
modelo = ChatOpenRouter(model=os.environ["MODEL_ID"], temperature=0)


# ---------- HERRAMIENTAS: ----------
tickets = json.load(open("datos/tickets.json", encoding="utf-8"))
articulos = json.load(open("datos/articulos.json", encoding="utf-8"))

@tool
def consultar_ticket(ticket_id: str) -> str:
    """ "Consulta el estado de un ticket de incidencia del hotel, por ejemplo T-100", cuando un huésped pregunte "¿cómo va mi ticket T-200?","""
    codigo = ticket_id.upper()
    if not codigo.startswith("T-"):
        return (f"Formato no valido")
    
    if  len(codigo)!= 5 :
        return (f"Formato no valido")

    if not codigo[2:].isdigit():
            return (f"Formato no valido")
    
    if ticket_id.upper() not in tickets:
        return (f"Ese ticket no existe en nuestra base de datos")
    
    return tickets.get(ticket_id.upper())["estado"]

@tool
def buscar_articulo(articulo_id: str) -> str:
    """ Aqui tienes una breve ayuda del hotel: el A-50 es para desayunos, A-40 es informacion de wifi, A-30 es como llmar a recepcion, A-20 es el manual del aire acondicionado y A-10 es para problemas con la llave de la habitacion.
    """
    numero = articulo_id.upper()

    if not numero.startswith("A-"):
        return (f"Formato no valido")

    if  len(numero)!= 4 :
        return (f"Formato no valido")

    if not numero[2:].isdigit():
        return (f"Formato no valido")
    if articulo_id.upper() not in articulos:
        return (f"No tengo esa informacion, consulta con recepcion. Puedo ayudarte en algo mas?")

    return articulos.get (articulo_id.upper())["texto"]


# Le enseñamos a Claude qué herramientas existen

modelo_con_herramientas = modelo.bind_tools([buscar_articulo, consultar_ticket])


# ---------- ESTADO (la libreta, igual que antes) ----------
class Estado(TypedDict):
    messages: Annotated[list, add_messages]
    llamadas_herramientas: int
    errores: list


# ---------- NODOS (las cajas) ----------
def inicio(estado: Estado) -> dict:
    # Cada pregunta nueva empieza con el contador a 0 (la conversación NO se borra)
    return {"llamadas_herramientas": 0, "errores": []}


def chatbot(estado: Estado, config) -> dict:
    count = estado.get("llamadas_herramientas" , 0)
    instrucciones = SystemMessage(content=config["configurable"]["prompt"])

    if count >= 2:
        respuesta = modelo.invoke([instrucciones] + estado["messages"])
    else:
        respuesta = modelo_con_herramientas.invoke([instrucciones] + estado["messages"])

    return {"messages": [respuesta]}


def ejecutar_herramientas(estado: Estado) -> dict:
    # Mira qué herramientas pidió Claude en su último mensaje y las ejecuta Python
    ultimo = estado["messages"][-1]
    resultados = []
    count = estado.get("llamadas_herramientas" , 0)
    errores = estado.get("errores", [])

    for llamada in ultimo.tool_calls:
            if count >= 2:
                texto = "Error: límite de dos herramientas agotado"
                errores.append("limite_agotado")
            else:
                count += 1
                try:
                    if llamada["name"] == "consultar_ticket":
                        texto = consultar_ticket.invoke(llamada["args"])
                    else:
                        texto = buscar_articulo.invoke(llamada["args"])
                except Exception:
                    texto = "Error controlado. No se obtuvo información."
                    errores.append("fallo_herramienta")

            resultados.append(ToolMessage(content=texto, tool_call_id=llamada["id"]))
    return {
        "messages": resultados,
        "llamadas_herramientas": count,
        "errores": errores,
    }


# ---------- EL IF (no es una caja: es la función que elige la flecha) ----------
def decidir(estado: Estado) -> str:
    ultimo = estado["messages"][-1]
    if ultimo.tool_calls:          # ¿Claude ha pedido alguna herramienta?
        return "herramientas"                 # Pista: el NOMBRE de la caja que ejecuta herramientas (con comillas)
    return END                    # Pista: si no pidió nada, se termina (igual que en la 1a)


# ---------- CONSTRUIR EL GRAFO ----------
builder = StateGraph(Estado)
builder.add_node("inicio", inicio)
builder.add_node("chatbot", chatbot)
builder.add_node("herramientas", ejecutar_herramientas)

builder.add_edge(START, "inicio")
builder.add_edge("inicio", "chatbot")
builder.add_conditional_edges("chatbot", decidir)   # flecha con IF: después de chatbot, pregunta a decidir
builder.add_edge("herramientas", "chatbot")                          # Pista: la flecha de VUELTA (mira el mapa de arriba)

# Memoria en SQLite 
os.makedirs("data", exist_ok=True)
with SqliteSaver.from_conn_string("data/memoria.sqlite") as checkpointer:
    grafo = builder.compile(checkpointer=checkpointer)

    # ---------- CHAT EN LA TERMINAL (varios turnos) ----------
    if __name__ == "__main__":
        conversacion = input("Nombre de la conversación: ")
        version = input("Versión del prompt (v1/v2): ")
        fuente = input("Desde qué web (langfuse/langsmith): ")
        texto_prompt = cargar_prompt(version, fuente)

        print("Recepción del hotel. Escribe 'salir' para terminar.")
        while True:
            mensaje = input("Tú: ")
            if mensaje.lower() == "salir":
                break
            config = crear_config(conversacion, version, fuente, texto_prompt)

            resultado = grafo.invoke({"messages": [HumanMessage(content=mensaje)]}, config)
            if resultado["llamadas_herramientas"] > 0:
                ruta = "usó herramienta"
            else:
                ruta = "contestó directo"
            print("Recepción:", resultado["messages"][-1].content)
            print(f"   (ruta: {ruta})")
            enviar()

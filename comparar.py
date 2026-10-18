# Ejecuta las 10 preguntas con v1 y con v2 (mismo modelo y parámetros) y guarda las métricas en un CSV
import csv
import json
import os
import time
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from asistente import builder
from trazas import cargar_prompt, crear_config, enviar

# Precio oficial de OpenRouter para anthropic/claude-haiku-5.5 (dólares por token)
PRECIO_ENTRADA = 0.10 / 1_000_000
PRECIO_SALIDA = 0.50 / 1_000_000

# El mismo grafo del asistente, con memoria en RAM (cada pregunta empieza limpia)
grafo = builder.compile(checkpointer=InMemorySaver())

preguntas = json.load(open("datos/evaluacion.json", encoding="utf-8"))
filas = []

for version in ["v1", "v2"]:
    texto_prompt = cargar_prompt(version, "langfuse")

    for p in preguntas:
        conversacion = f"eval-{version}-{p['id']}"
        config = crear_config(conversacion, version, "langfuse", texto_prompt)

        inicio = time.time()
        resultado = grafo.invoke({"messages": [HumanMessage(content=p["pregunta"])]}, config)
        duracion = round(time.time() - inicio, 2)

        # Tokens: se suman los de todas las respuestas de Claude en esta pregunta
        entrada = 0
        total = 0
        for mensaje in resultado["messages"]:
            if isinstance(mensaje, AIMessage) and mensaje.usage_metadata:
                entrada += mensaje.usage_metadata["input_tokens"]
                total += mensaje.usage_metadata["total_tokens"]
        salida = total - entrada

        filas.append({
            "id": p["id"],
            "version": version,
            "pregunta": p["pregunta"],
            "esperado": p["esperado"],
            "herramienta_esperada": p["herramienta"],
            "respuesta": resultado["messages"][-1].content,
            "duracion_s": duracion,
            "herramientas": resultado["llamadas_herramientas"],
            "errores": ", ".join(resultado["errores"]),
            "tokens_entrada": entrada,
            "tokens_salida": salida,
            "coste_usd": round(entrada * PRECIO_ENTRADA + salida * PRECIO_SALIDA, 6),
            "query_id": config["metadata"]["query_id"],
            "valoracion": "",
        })
        print(version, p["id"], duracion, "s")
        enviar()

os.makedirs("resultados", exist_ok=True)
with open("resultados/resultados.csv", "w", newline="", encoding="utf-8") as f:
    escritor = csv.DictWriter(f, fieldnames=filas[0].keys())
    escritor.writeheader()
    escritor.writerows(filas)

print("Guardado en resultados/resultados.csv")
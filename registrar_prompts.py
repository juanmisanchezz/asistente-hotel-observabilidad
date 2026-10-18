# Sube las dos versiones del prompt a Langfuse y a LangSmith (se ejecuta UNA sola vez)
from dotenv import load_dotenv
from langfuse import Langfuse
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
langfuse = Langfuse()
langsmith = Client()

NOMBRE = "asistente-hotel"

for version in ["v1", "v2"]:
    texto = open(f"prompts/{version}.txt", encoding="utf-8").read()

    # Langfuse: el prompt como texto, con la etiqueta de su versión
    langfuse.create_prompt(name=NOMBRE, type="text", prompt=texto, labels=[version])

    # LangSmith: el prompt como plantilla de chat, con el tag de su versión
    plantilla = ChatPromptTemplate.from_messages([("system", texto)])
    langsmith.push_prompt(NOMBRE, object=plantilla, commit_tags=[version])

    print("Subida", version)

langfuse.flush()

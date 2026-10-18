# Conecta el asistente con Langfuse y LangSmith (las "cámaras")
import os
import uuid
from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langsmith import Client
from langchain_core.tracers.langchain import LangChainTracer
from privacidad import ocultar, ocultar_langfuse

load_dotenv()

# Una sola forma de grabar: los dos oyentes que ponemos a mano (así no se duplica nada)
os.environ["LANGSMITH_TRACING"] = "false"

# Langfuse: el cliente (la conexión) y su oyente
langfuse = Langfuse(mask=ocultar_langfuse)
oyente_langfuse = CallbackHandler()

# LangSmith: el cliente (la conexión) y su oyente
cliente_langsmith = Client(hide_inputs=ocultar, hide_outputs=ocultar)
oyente_langsmith = LangChainTracer(client=cliente_langsmith, project_name=os.environ["LANGSMITH_PROJECT"])


def crear_config(thread_id, prompt_version):
    query_id = str(uuid.uuid4())
    return {
        "configurable": {"thread_id": thread_id},
        "callbacks": [oyente_langfuse, oyente_langsmith],
        "run_name": "asistente-hotel",
        "tags": ["p6", prompt_version],
        "metadata": {
            "query_id": query_id,
            "thread_id": thread_id,
            "modelo": os.environ["MODEL_ID"],
            "prompt_version": prompt_version,
            "langfuse_session_id": thread_id,
        },
    }


def enviar():
    oyente_langsmith.wait_for_futures()
    cliente_langsmith.flush()
    langfuse.flush()

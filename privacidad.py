# Oculta datos personales y claves ANTES de enviar nada a Langfuse o LangSmith
import re

# Patrón de un email: algo@algo.algo
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Si un campo se llama así, su valor se oculta entero
CAMPOS_SENSIBLES = ["api_key", "password", "secret", "authorization"]


def ocultar(datos):
    # Los mensajes de LangChain se convierten primero a diccionario
    if hasattr(datos, "model_dump"):
        return ocultar(datos.model_dump())
    # Un texto: cambiar cada email por [EMAIL_OCULTO]
    if isinstance(datos, str):
        return EMAIL.sub("[EMAIL_OCULTO]", datos)
    # Un diccionario: revisar cada campo
    if isinstance(datos, dict):
        limpio = {}
        for campo, valor in datos.items():
            if any(palabra in str(campo).lower() for palabra in CAMPOS_SENSIBLES):
                limpio[campo] = "[OCULTO]"
            else:
                limpio[campo] = ocultar(valor)
        return limpio
    # Una lista: revisar cada elemento
    if isinstance(datos, list):
        return [ocultar(elemento) for elemento in datos]
    # Números, None...: se dejan igual
    return datos


# Langfuse llama a la función de otra forma (con nombre "data"), así que le hacemos un adaptador
def ocultar_langfuse(*, data, **kwargs):
    return ocultar(data)

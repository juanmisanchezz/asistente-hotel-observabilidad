# Asistente de recepción de hotel con LangGraph

Proyecto 5 del máster de AI Engineering (thePower): LangGraph ("Langchamps").

*English version below.*

Un chat en la terminal que hace de recepcionista de un hotel ficticio. El chat decide en cada mensaje si contesta directamente o si consulta una herramienta: el estado de un ticket de incidencia o un artículo de ayuda (wifi, desayuno, aire acondicionado, etc). Recuerda cada conversación aunque se cierre el programa, solo usa como mucho 2 herramientas por pregunta y si una herramienta falla, responde con un error controlado en vez de romperse. El modelo es Claude Haiku a través de OpenRouter.

## Ejemplo de uso

```
Nombre de la conversación: hola
Recepción del hotel. Escribe 'salir' para terminar.
Tú: como va mi ticket t-199?
Recepción: Lo siento, no encuentro el ticket T-199 en nuestro sistema. ¿Puede revisar si el número está bien escrito? Con gusto le ayudo a buscarlo de nuevo.
   (ruta: usó herramienta)
Tú: perdon, t-100
Recepción: El ticket T-100 está en curso, así que su incidencia se está atendiendo. No tengo más detalles sobre el avance.
   (ruta: usó herramienta)
Tú: salir
```

Capturas de cada etapa en [capturas/](capturas/).

## Esquema del grafo

```mermaid
flowchart LR
    S([START]) --> I[inicio]
    I --> C[chatbot]
    C -- "pide herramienta" --> H[herramientas]
    H --> C
    C -- "no pide nada" --> E([END])
```

- **inicio:** pone a 0 el contador de herramientas y vacía la lista de errores en cada pregunta nueva (la conversación no se borra)
- **chatbot:** llama a Claude. Si el contador ya va por 2, lo llama **sin herramientas**, así que tiene que contestar
- **herramientas:** ejecuta las herramientas que pidió Claude, suma al contador y, si ya van 2, contesta "límite agotado" sin ejecutar
- **decidir** (la flecha condicional): si el último mensaje de Claude pide herramientas va a `herramientas`; si no, termina

### Ejemplos de rutas

| Pregunta | Ruta | Resultado |
|---|---|---|
| "Hola" | inicio → chatbot → END | Contesta directo, sin herramientas |
| "¿Cómo va mi ticket T-100?" | inicio → chatbot → herramientas (`consultar_ticket`) → chatbot → END | "Está en curso" (sale del JSON, no se lo inventa) |
| "¿Cómo va mi ticket T-999?" | inicio → chatbot → herramientas → chatbot → END | "No encuentro ese ticket" |
| Claude pide 3 herramientas a la vez (probado en los tests) | inicio → chatbot → herramientas (ejecuta 2, la 3.ª recibe "límite agotado") → chatbot **sin herramientas** → END | Termina siempre, sin bucles |

## Estructura del proyecto

```
asistente-hotel-langgraph/
├── README.md
├── asistente.py            # el asistente completo (etapas 2-5)
├── etapas/
│   ├── 01_grafo_fijo.py    # etapa 1a: grafo con respuesta fija, sin modelo
│   └── 02_grafo_modelo.py  # etapa 1b: el nodo ya llama a Claude
├── datos/
│   ├── tickets.json        # tickets ficticios T-100, T-200, T-300
│   └── articulos.json      # artículos de ayuda ficticios A-10 … A-50
├── tests/
│   └── test_asistente.py   # 4 tests sin llamar a Claude
├── capturas/
├── requirements.txt        # librerías (mismas versiones que en clase)
├── requirements.lock       # versiones exactas de todo (archivo de bloqueo)
├── .env.example            # plantilla de la clave, sin clave
└── .gitignore
```

## Etapas

Cada etapa tiene su commit.

| Etapa | Qué añade | Lo que pasó al probarla |
|---|---|---|
| 0 | Entorno, dependencias bloqueadas y clave fuera del repo | Al principio pegué la clave en la plantilla que se sube; lo arreglé antes del primer commit |
| 1a | Grafo `START → recepcion → END` con respuesta fija | Pregunte lo que pregunte, contesta siempre lo mismo |
| 1b | El nodo llama a Claude (`MODEL_ID`) | Le pregunté a qué hora es el desayuno y **se lo inventó** con total seguridad |
| 2 | Chatbot de varios turnos con flecha condicional (contestar o usar herramienta) | Con la herramienta ya no se inventa el horario |
| 3 | Memoria persistente con `SqliteSaver` y `thread_id` por conversación | Sobrevive al reinicio, no mezcla conversaciones y una conversación nueva empieza vacía |
| 4 | Herramientas `consultar_ticket` y `buscar_articulo` sobre JSON ficticio | Ticket que existe → su estado; ticket que no existe → lo dice, no inventa |
| 5 | Límite de 2 herramientas, fallos controlados y tests | `python -m unittest discover -s tests` → 4 tests OK |

## Piezas

- **Estado:** `messages` (la conversación), `llamadas_herramientas` (el contador) y `errores` (`"limite_agotado"` o `"fallo_herramienta"`)
- **Herramientas de solo lectura:** `consultar_ticket` y `buscar_articulo` comprueban primero el formato (`T-` + 3 números, `A-` + 2 números) y después si existe. Con un formato malo responden "Formato no valido" y con uno que no existe lo dicen, sin romperse
- **Memoria:** `SqliteSaver` guarda cada conversación en `data/memoria.sqlite` con su `thread_id`. Al arrancar el chat se pide el nombre de la conversación
- **Freno:** el contador vive en el estado; el nodo de herramientas no ejecuta más de 2 y el chatbot, al llegar a 2, se llama sin herramientas
- **Fallos controlados:** un `try/except` alrededor de cada herramienta. Si revienta, Claude recibe "Error controlado" y el fallo se apunta en `errores`

## Decisiones

- **Primero sin IA (1a) y luego con IA (1b):** para entender las cajas, las flechas y el estado antes de meter el modelo
- **El límite va en el código, no en el prompt:** probé a poner en el prompt "si no sabes algo, no lo inventes" y siguió inventándose el desayuno (y además ofreció reservar mesa, algo que no puede hacer). Una regla en el prompt es una sugerencia; el freno y los datos tienen que venir del código y de las herramientas
- **Modelo configurable con `MODEL_ID`:** se cambia de modelo sin tocar el código
- **Datos en JSON y no en el código:** se pueden añadir tickets y artículos sin tocar el programa
- **La lista de artículos va en la descripción de `buscar_articulo`:** así Claude sabe qué identificador pedir. Con 5 artículos basta; con cientos habría que buscar por tema, y con miles, RAG (el enunciado no lo pide)
- **Tests sin red:** prueban mi código (validación, freno y `try/except`), no las respuestas de Claude, que no son predecibles. Se llama a las funciones con datos inventados y con `patch` se sustituye una herramienta por una falsa que explota. No gastan nada y tardan milésimas
- **A mano para aprender:** en un proyecto real muchas de estas piezas vienen hechas (`ToolNode`, `tools_condition`, `recursion_limit`, `pytest`). Aquí las he hecho a mano para entender qué pasa por dentro

## Limitaciones

- **El `thread_id` separa conversaciones, pero no es seguridad:** quien escriba el mismo nombre de conversación entra en ella. En una app real saldría de algo que ya identifica al cliente (su teléfono en WhatsApp, su login…), no lo escribiría él
- **Las mayúsculas cuentan:** `Conversacion-1` y `conversacion-1` son conversaciones distintas
- **El `try/except` puede esconder errores míos:** al editar se me coló `llamada["a"]` en vez de `llamada["name"]` y todas las herramientas daban "Error controlado" sin avisar. La lista `errores` es lo que me permitió verlo
- **La memoria crece sin límite:** en cada turno se le manda a Claude toda la conversación, así que una conversación muy larga cuesta más
- **Los tests no comprueban a Claude:** comprueban que mi código reacciona bien. Que Claude elija bien la herramienta lo he comprobado probando el chat (capturas)

## Ejecución

1. Crear el entorno e instalar las librerías:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.lock
   ```
2. Hacer una copia de `.env.example` como `.env` y rellenar la clave de OpenRouter y el `MODEL_ID`
3. Ejecutar el chat:
   ```
   python asistente.py
   ```
   Para salir: `salir`
4. Ejecutar los tests (no llaman a Claude, son gratis):
   ```
   python -m unittest discover -s tests
   ```

---

## English version

**Hotel front-desk assistant with LangGraph** is a terminal chat that plays the receptionist of a fictional hotel. On every message it decides whether to answer directly or to use a tool (a support-ticket status or a help article). It remembers each conversation across restarts, uses at most 2 tools per question and, if a tool fails, returns a controlled error instead of crashing. The model is Claude Haiku through OpenRouter. This is project 5 of my AI Engineering master (thePower): LangGraph.

**Graph**

`START → inicio → chatbot ⇄ herramientas → END`. `inicio` resets the tool counter for each new question; `chatbot` calls Claude (without tools once the counter reaches 2); `herramientas` runs the requested tools and refuses any beyond the second with a "limit reached" message; a conditional edge sends the flow to the tools node or to the end.

**Pieces**

- State: `messages`, `llamadas_herramientas` (tool counter) and `errores`
- Read-only tools over fictional JSON data: `consultar_ticket` and `buscar_articulo`, which validate the ID format before looking it up
- Persistent memory with `SqliteSaver` and a `thread_id` per conversation
- `try/except` around each tool: failures become a controlled error and are recorded in `errores`

**Decisions**

- Built step by step (fixed answer → model → tools → memory → limit), one commit per stage
- The limit lives in the code, not in the prompt: a "don't make things up" rule in the prompt did not stop the model from inventing the breakfast time
- Offline tests (`unittest` + `patch`) check my code, not Claude's answers: invalid format, unknown ticket, the 2-tool limit and a tool failure

**Limitations**

- `thread_id` separates conversations but is not authentication
- The whole history is sent on every turn, so long conversations cost more

**Run**

```
pip install -r requirements.lock
cp .env.example .env   # add your OpenRouter key and MODEL_ID
python asistente.py
python -m unittest discover -s tests
```

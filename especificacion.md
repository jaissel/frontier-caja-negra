# Especificación · Servicio "caja negra" (Reto 2)

Autora: Jaissel Nicol Pérez Marten · Frontier BOG/26 · 10 oct 2026
Evidencia: los números `#N` son el campo `id` de `experimentos.jsonl`. `ej.N` es la línea N de `pruebas/ejemplos.jsonl`.
Confianza: **confirmado** (lo probé y se repite), **probable** (lo vi una vez o lo infiero), **supuesto** (no lo probé; es lo que hace el reemplazo por defecto).

> **Versión vigente: v2** (desde las 15:30, ticket FR-0153). Las filas marcadas **[v2]** reemplazan el comportamiento v1 indicado. Todo lo demás es igual en las dos versiones (regresión r2: #3224–#3451).

Resumen: un mini core bancario. Recibe mensajes de texto `COMANDO;arg1;…;control` dentro de `{"m": "..."}` por `POST /msg`. El estado (cuentas, saldos y operaciones) es por token y vuelve a cero con `POST /__reset`.

---

## 1. Entrada

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| IN-01 | Solo existen 3 rutas: `GET /health`, `POST /__reset` y `POST /msg`. Las rutas son exactas: distinguen mayúsculas y no aceptan barra final. | #2469–#2478 | confirmado |
| IN-02 | Cualquier otra combinación de método y ruta responde `404 {"error":"E404","mensaje":"ruta desconocida"}`. Eso incluye `GET /msg`, `PUT /msg`, `POST /health`, `GET /__reset`, `/msg/`, `/MSG` y `/`. | #2469–#2478 | confirmado |
| IN-03 | La regla de ruta desconocida se evalúa **antes** que la autenticación: una ruta inexistente sin token da 404, no 401. | #2473 | confirmado |
| IN-04 | Las 3 rutas válidas exigen `Authorization: Bearer <token>`, incluido `/health`. Sin header, con un token inventado, sin la palabra `Bearer` o con `bearer` en minúsculas, responden `401 {"error":"E001","mensaje":"no autorizado"}`. | #2463–#2468 | confirmado |
| IN-05 | La autenticación se evalúa antes que el cuerpo: un token malo con un cuerpo válido da E001. | #2463, #2464 | confirmado |
| IN-06 | `GET /health` con token responde `200 {"ok":true}`. | #2659 | confirmado |
| IN-07 | `POST /__reset` con token responde `200 {"ok":true}` y borra cuentas, saldos, operaciones y contadores del token. | #2660; los contadores vuelven a AC-0001 y OP-0001 en cada secuencia: #2523, #2536, #2542, #2555, #2558 | confirmado |
| IN-08 | El cuerpo de `/msg` debe ser un JSON válido. Si está vacío, no es JSON o está roto: `400 E100 "json inválido"`. | #2479–#2481 | confirmado |
| IN-09 | El JSON debe ser un objeto con un campo `m` de tipo string. Si falta `m`, es número, es `null`, el cuerpo es un array o es un string JSON suelto: `400 E102 "falta m"`. | #2482–#2484, #2486, #2491 | confirmado |
| IN-10 | Los campos extra del objeto se ignoran. | #2487 | confirmado |
| IN-11 | El cuerpo de `POST /msg` puede medir hasta **8192 bytes**. Con 8193 bytes o más responde `413 {"error":"E101","mensaje":"cuerpo demasiado grande"}`. Se cuentan bytes, no caracteres: 5000 `é` son 10013 bytes y dan E101. `/__reset` ignora el cuerpo. | #4341–#4345, #4364, #4349, #4326–#4339 | confirmado |
| IN-11b | Orden de E101: ruta (E404) → token (E001) → servicio detenido (E599) → **tamaño (E101)** → JSON (E100). | #4346–#4348, #4351 | confirmado |
| IN-13 | El JSON se lee de forma estricta: un BOM al inicio da E100 y `NaN` da E100. Con claves duplicadas gana la última. El `Content-Type` no importa: un `text/plain` con JSON válido funciona. La clave debe ser `m` en minúscula (`M` da E102), y `null` o un número como cuerpo dan E102. | #3108, #3115, #3109, #3107, #3110, #3113, #3114 | confirmado |
| IN-14 | `HEAD` y `OPTIONS` dan 404. Los parámetros de la URL (`?x=1`) se ignoran. `Bearer` con doble espacio da 401. | #3102–#3106 | confirmado |
| IN-12 | Cada token tiene un estado propio. | README; mi token siempre empezó desde cero tras el reset | probable |

## 2. Integridad

El mensaje se separa por `;`. El **último segmento es el dígito de control** y el primero es el comando.

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| IG-01 | Si `m` no contiene `;` (incluido `""`), responde `400 E103 "falta control"`. | #4, #2485, #2494 | confirmado |
| IG-02 | Si algún segmento está vacío (`;`, `PING;`, `CONSULTA;;14`, `;CONSULTA;14`, `…;14;`), responde `400 E104 "segmento vacío"`. | #2492, #2493, #2495–#2498, #2525, #2549 | confirmado |
| IG-03 | El control debe tener **1 o 2 dígitos ASCII** (`[0-9]{1,2}`). Si no, responde `400 E201 "control mal formado"`. Ejemplos: `100`, `014`, `-14`, ` 14`, `14.0`, `1e1`, `5X`. | #109, #2499–#2503, #2509, ej.17 | confirmado |
| IG-04 | Con un formato correcto, el valor se compara como entero: `05` equivale a 5. Si no coincide con el calculado, responde `400 E202 "control inválido"`. | #2596, #2599, barrido #9–#118 | confirmado |
| IG-05 | **Cálculo del control (MOD 97-10, como el IBAN):** se toma todo `m` menos el último segmento. Cada letra ASCII se reemplaza por su posición en el abecedario (A=1 … Z=26, sin distinguir mayúsculas). Cada dígito queda igual. Todo lo demás (`;`, `-`, espacios, tildes) se ignora. La cadena resultante se lee como un número N y `control = 98 − (N·100 mod 97)`. Ejemplo: `CONSULTA;AC-0001` → 14. | Barridos #9–#118, #122–#834, #835–#2221 y #2222–#2462. La fórmula reproduce los 65 datos medidos: 63 aceptados, más los 2 rechazados a propósito en ej.2 y ej.17 | confirmado |
| IG-06 | Para todos los comandos salvo PING, el control se valida **antes** de reconocer el comando, la aridad o la existencia de la cuenta. | #119–#121, #2504, #2506, #2507 | confirmado |
| IG-07 | **PING no valida el control:** acepta cualquier valor no vacío (`XX`, `65`, `164`, `05`). Sí exige que exista el segmento (E103) y que no haya segmentos vacíos (E104). | #2, #3, #5, #7, #2597, #4, #2493 | confirmado |

## 3. Comandos

El comando no distingue mayúsculas (`consulta`, `CONSULTa`, `ping`). Aridad = número de argumentos entre el comando y el control.

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CM-01 | Si el comando es desconocido y el control es válido, responde `400 {"error":"E301","mensaje":"comando desconocido "}`. El mensaje termina con un **espacio**. | #2505, #2621, #2625, ej.12 | confirmado |
| CM-02 | Si el comando desconocido está a una **distancia de edición (Levenshtein) ≤ 2** de un comando real (comparando en mayúsculas), E301 agrega `"sugerencia":"<COMANDO>"`. Con distancia 3 o más no hay sugerencia. Un espacio antes o después cuenta como 1 edición. | #2513, #2514, #2609–#2627, #2643–#2653, #2658 | confirmado |
| CM-03 | La lista de sugerencias incluye el comando oculto `HALT` (`HELP`, `HOLD` y `WAIT` sugieren HALT). Si dos comandos empatan en distancia, gana el primero del orden PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA, HALT: `ALT` y `AL` empatan entre ALTA y HALT, y sugieren ALTA. | #2888, #2942, #3092, #2616, #2651 | probable |
| CM-04 | Con aridad incorrecta y control válido, responde `400 E302 "aridad inválida"`. | #2508, #2553, #2590, #2628–#2630, ej.20 | confirmado |

**PING** · `PING;<cualquiera>` (aridad 0)

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CM-P1 | Responde `200 {"pong":true}`. No cambia el estado. | #1–#3, #5–#7 | confirmado |
| CM-P2 | Con más segmentos (`PING;1;2`), responde E302 **sin validar el control**. | #2516, #2517 | confirmado |

**ALTA** · `ALTA;<nombre>;ctl`

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CM-A1 | Crea una cuenta con saldo 0 y responde `201 {"cuentaId":"AC-NNNN"}`, con un contador de 4 dígitos que empieza en 0001. | #2523, #2534 | confirmado |
| CM-A2 | El nombre no se valida: acepta repetidos, espacios, tildes, dígitos y 200 caracteres. Cada alta crea una cuenta nueva. | #2524, #2526–#2533 | confirmado |
| CM-A3 | Después de AC-9999 el formato sería `AC-10000`. | — | supuesto |

**CONSULTA** · `CONSULTA;<cuenta>;ctl`

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CM-C1 | [v1] Responde `200 {"cuenta_id":"AC-0001","saldo":<entero>}`. Ojo: la clave es `cuenta_id`, mientras que ALTA usa `cuentaId`. | #2534, #2550, ej.5 | confirmado |
| CM-C1b | **[v2]** El saldo es un **string en pesos con 2 decimales**: los montos se guardan en centavos y se muestran ÷100. Ejemplos: 0 → `"0.00"`, 5 → `"0.05"`, 100 → `"1.00"`, -5 → `"-0.05"`, -3000 → `"-30.00"`. Las demás respuestas no cambian. | #3224, #3270, #3519, #3521, #3523, #3526, #3528 | confirmado |
| CM-C2 | El id de cuenta debe coincidir exactamente: `ac-0001`, `AC-1` o ` AC-0001` dan `404 E401 "cuenta inexistente"`. | #2593–#2595 | confirmado |

**DEPOSITO** · `DEPOSITO;<cuenta>;<monto>;ctl`

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CM-D1 | El monto válido es un entero de 1 a 10 dígitos, sin ceros a la izquierda ni signo (`[1-9][0-9]{0,9}`, máximo 9999999999). Si no, responde `400 E303 "monto inválido"`. Casos: `0`, `-5`, `10.5`, `abc`, `007`, `1e3`, ` 5`, `+5` y valores de 11 o más dígitos. | #2538–#2548, #2632–#2641, #2655, #2656 | confirmado |
| CM-D2 | El monto se valida **antes** que la cuenta. | #2554 | confirmado |
| CM-D3 | Si la cuenta no existe, responde `404 E401`. | #2551, #2552 | confirmado |
| CM-D4 | Si todo está bien, suma el monto al saldo y responde `200 {"status":"recieved","operacionId":"OP-NNNN"}`. `recieved` está mal escrito en el original. | #2542, #2550, ej.6 | confirmado |

**TRANSFER** · `TRANSFER;<origen>;<destino>;<monto>;ctl`

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CM-T1 | Orden de validación: monto (E303) → origen = destino (`400 E304 "origen y destino iguales"`) → existencia de ambas cuentas (E401) → **[v2] cuenta bloqueada (E510)** → límite (E506) → saldo (E507). | #2600, #2657, #2601, #2602, #2573, #2572 | confirmado |
| CM-T2 | [v1] El límite es **por operación**: monto > 100000 da `422 E506 "límite excedido"`, y 100000 exacto pasa. No es acumulado ni por destino. | #2559–#2563, ej.9, ej.10 | confirmado |
| CM-T2b | **[v2]** El límite bajó a **50000**: 50000 pasa y 50001 da E506. Sigue siendo por operación. | #3250, #3251, #3456, #3516, búsqueda #3457–#3516 | confirmado |
| CM-T5 | **[v2] Bloqueo:** 3 rechazos de negocio **seguidos** (E506 o E507, mezclados o no) en TRANSFER desde una cuenta la dejan **bloqueada**. El 3er rechazo responde normal (E506/E507) y bloquea a partir del siguiente. El contador es por cuenta de origen. | #3537–#3543, #3556–#3559, #3594–#3597, #3624–#3629, #3571 | confirmado |
| CM-T6 | [v2] La racha se reinicia con una transferencia exitosa desde la cuenta o con cualquier depósito a ella. E303, E304 y E401 no cuentan para la racha ni la cortan. | #3539–#3542, #3617–#3621, #3566–#3570, #3624–#3629 | confirmado |
| CM-T7 | [v2] Toda TRANSFER desde una cuenta bloqueada que pase E303, E304 y E401 responde `423 {"error":"E510","mensaje":"cuenta bloqueada","intentos":N}`, con N = 1, 2, 3… sin máximo. El bloqueo gana sobre E506 y E507. Los errores anteriores no suben N. | #3543, #3544, #3578–#3585, #3598, #3611–#3614 | confirmado |
| CM-T8 | [v2] El bloqueo no expira con el tiempo (12 s probados). Solo lo levanta un **DEPOSITO a esa cuenta**, de cualquier monto (1 centavo basta). ANULA o un depósito a otra cuenta no lo levantan. CONSULTA, DEPOSITO y ANULA siguen funcionando con la cuenta bloqueada. | #3585–#3587, #3600–#3605, #3545, #3546 | confirmado |
| CM-T8b | [v2] Una cuenta bloqueada puede recibir transferencias (el bloqueo solo afecta al origen), y recibir una **no** la desbloquea: solo un DEPOSITO lo hace. | #3637–#3639 | confirmado |
| CM-T9 | [v2] Si la cuenta se vuelve a bloquear después de un desbloqueo, `intentos` empieza de nuevo en 1. | #4314–#4325 | confirmado |
| CM-T3 | Si el saldo del origen es menor que el monto, responde `422 E507 "saldo insuficiente"`. Se puede transferir el saldo exacto. | #2603–#2605, ej.16 | confirmado |
| CM-T4 | Si todo está bien, mueve el saldo y responde `200 {"status":"recieved","operacionId":"OP-NNNN"}`. | #2560, #2564, #2565, ej.7 | confirmado |

**ANULA** · `ANULA;<operación>;ctl`

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CM-N1 | Revierte la operación y responde `200 {"ok":true,"anulada":"OP-NNNN"}`. En un depósito resta el monto de la cuenta. En una transferencia devuelve al origen y resta al destino. | #2579–#2583, ej.13 | confirmado |
| CM-N2 | La reversión **no revisa el saldo**: puede dejar saldos negativos (-3000). | #2580 | confirmado |
| CM-N3 | Anular algo ya anulado responde `200 {"ok":false,"motivo":"ya anulada"}`, sin error HTTP. | #2589, ej.14 | confirmado |
| CM-N4 | Si la operación no existe (incluidos `op-0002` en minúsculas o un id de cuenta), responde `404 E402 "operación inexistente"`. | #2584–#2586 | confirmado |

**HALT (comando oculto)** · `HALT;<confirmación>;ctl` (aridad 1). No aparece en los ejemplos: lo descubrí porque `HELP` sugería `HALT`.

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CM-H1 | Con aridad distinta de 1 responde E302. El control se valida antes (`HALT;0` da E202). | #2925, #2928, #2929, #2930 | confirmado |
| CM-H2 | Con cualquier argumento distinto de exactamente `1` responde `409 {"error":"E520","mensaje":"operación destructiva: detiene el servicio; reenvía con confirmación"}`. Ni reenviar el mensaje ni un campo `confirm` en el JSON cuentan como confirmación. | #2927, #2972, #2973, #2977–#2985, #3005–#3008, #3010, #3011 | confirmado |
| CM-H3 | `HALT;1` **detiene el servicio** y responde `503 {"error":"E599","mensaje":"service halted"}`. | #2986, #2997 | confirmado |

## 4. Memoria entre requests

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| ME-01 | Se recuerdan las cuentas, sus saldos y las operaciones con su estado de anulación. | #2550, #2564, #2589 | confirmado |
| ME-02 | Los contadores AC y OP son secuenciales, independientes entre sí y vuelven a 1 con el reset. | #2536–#2542, #2555–#2558 | confirmado |
| ME-03 | Una operación rechazada no consume número de OP. Anular tampoco: la siguiente operación sigue la secuencia. | #2559, #2560, #2587 | confirmado |
| ME-05 | Después de `HALT;1`, **todo** `POST /msg` responde `503 E599`, incluidos un JSON roto, PING y los errores de control. `/health` sigue en 200, las rutas inexistentes dan 404 y sin token da 401. Solo `POST /__reset` lo repara. | #2995, #2998–#3004, #2996 | confirmado |
| ME-06 | [v2] Por cada cuenta se recuerda además la racha de rechazos, si está bloqueada y cuántos intentos lleva bloqueada (CM-T5 a CM-T8). Todo vuelve a cero con `/__reset`. | #3537–#3629 | confirmado |
| ME-04 | El header `X-Req` es un contador de requests del token que **no** vuelve a cero con el reset (en #2631 vale 2615). Los headers no se comparan, así que el reemplazo no lo replica. | campo `x_req` del log | probable |

## 5. Errores (orden de evaluación)

Para cada request se aplica el **primer** error de esta lista que corresponda:

| Orden | Código | Status | Cuerpo exacto | Evidencia |
|---|---|---|---|---|
| 1 | E404 | 404 | `{"error":"E404","mensaje":"ruta desconocida"}` | #2469–#2478 |
| 2 | E001 | 401 | `{"error":"E001","mensaje":"no autorizado"}` | #2463–#2468 |
| 2b | E599 | 503 | `{"error":"E599","mensaje":"service halted"}` (solo si el servicio está detenido por HALT) | #3001–#3004 |
| 2c | E101 | 413 | `{"error":"E101","mensaje":"cuerpo demasiado grande"}` (cuerpo de más de 8192 bytes) | #4345, #4348 |
| 3 | E100 | 400 | `{"error":"E100","mensaje":"json inválido"}` | #2479–#2481 |
| 4 | E102 | 400 | `{"error":"E102","mensaje":"falta m"}` | #2482–#2486 |
| 5 | E103 | 400 | `{"error":"E103","mensaje":"falta control"}` | #4, #2494 |
| 6 | E104 | 400 | `{"error":"E104","mensaje":"segmento vacío"}` | #2492–#2498 |
| 7 | (PING) | — | si el comando es PING: E302 si hay más de 2 segmentos, si no `{"pong":true}` | #2516 |
| 8 | E201 | 400 | `{"error":"E201","mensaje":"control mal formado"}` | #2510, #2511 |
| 9 | E202 | 400 | `{"error":"E202","mensaje":"control inválido"}` | #2504, #2506, #2507 |
| 10 | E301 | 400 | `{"error":"E301","mensaje":"comando desconocido "}` (+ `sugerencia`) | #2505, #2609 |
| 11 | E302 | 400 | `{"error":"E302","mensaje":"aridad inválida"}` | #2508 |
| 12 | E303 | 400 | `{"error":"E303","mensaje":"monto inválido"}` | #2554, #2600 |
| 13 | E304 | 400 | `{"error":"E304","mensaje":"origen y destino iguales"}` | #2601, #2602 |
| 14 | E401 / E402 | 404 | `{"error":"E401","mensaje":"cuenta inexistente"}` / `{"error":"E402","mensaje":"operación inexistente"}` | #2573, #2584 |
| 14b | E520 / E599 | 409 / 503 | HALT: `{"error":"E520","mensaje":"operación destructiva: detiene el servicio; reenvía con confirmación"}` / `{"error":"E599","mensaje":"service halted"}` | #2927, #2997 |
| 14c | E510 [v2] | 423 | `{"error":"E510","mensaje":"cuenta bloqueada","intentos":N}` (solo TRANSFER desde una cuenta bloqueada) | #3598, #3611–#3614 |
| 15 | E506 | 422 | `{"error":"E506","mensaje":"límite excedido"}` | #2572 |
| 16 | E507 | 422 | `{"error":"E507","mensaje":"saldo insuficiente"}` | #2603 |

## 6. Cambios durante el día

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CD-01 | Hasta las 11:45 no hubo diferencias con la versión de la mañana: los 20 ejemplos, grabados en la mañana, se reproducen idénticos en el reemplazo, que fue construido con datos de 11:00 a 11:45. | replay de ej.1–20 y del log: 2671/2671 pasos idénticos | confirmado |
| CD-03 | Regresión de las 13:08: volví a mandar al original 211 requests de las secuencias de comportamiento (ejemplos y e1–e11). Las 211 respondieron igual que a las 11:00–11:45. | #2661–#2871 | confirmado |
| CD-04 | **15:30 · v2 (ticket FR-0153).** Lo detecté repitiendo contra el original 313 requests ya grabados (regresión r2): 34 respuestas cambiaron y todas se explican con **3 cambios**: |  #3224–#3451 | confirmado |
| CD-04a | Cambio 1 · Formato del saldo en CONSULTA: de entero a string en pesos con 2 decimales (CM-C1b). | #3224, #3240, #3270, #3519–#3528 | confirmado |
| CD-04b | Cambio 2 · El límite de TRANSFER bajó de 100000 a 50000 (CM-T2b). | #3250, #3293, #3456, #3516 | confirmado |
| CD-04c | Cambio 3 · Bloqueo de la cuenta de origen tras 3 rechazos seguidos, con E510 y `intentos` (CM-T5 a CM-T8). | #3252, #3253, #3537–#3629 | confirmado |
| CD-04d | Las otras 279 respuestas de la regresión, incluidos los 20 ejemplos públicos, HALT, los errores y el JSON, quedaron iguales. Los cambios en ANULA de la regresión son consecuencia del cambio 2 (la operación no se creó), no un cambio de ANULA. | #3224–#3451, #3446, #3451 | confirmado |
| CD-05 | Validación del reemplazo v2 con 2 sets aleatorios nuevos con la forma del set oculto (40 de 1 request, 45 de 2–5 y 15 de 6–12), grabados contra el original a las 16:49: 200/200 tests y 674/674 respuestas idénticas. | #3640–#4313 | confirmado |
| CD-06 | Tercer set aleatorio, enfocado en estado (30 secuencias de 8–12 con bloqueos, ANULA, HALT y cuerpos de ~8 KB): 30/30 y 295/295 idénticos contra el original v2. | #4365–#4659 | confirmado |
| CD-07 | Explorador asistido por LLM (`llm_tests.py`, OpenRouter): el modelo leyó esta especificación y propuso 20 casos difíciles, cada uno con su hipótesis (en el log aparecen como `[LLM] …`). Contra el original v2: 20/20 casos y 117/117 respuestas idénticas al reemplazo. | #4660–#4776 | confirmado |
| CD-02 | Método de detección: `regresion.py` repite contra el original secuencias ya grabadas y muestra cada diferencia. Cada cambio se aisló después con experimentos dirigidos (búsqueda binaria del límite, secuencias de bloqueo). | regresion.py, #3457–#3629 | confirmado |

## 7. Riesgos

| ID | Riesgo heredado | Cómo lo cerraría |
|---|---|---|
| RI-01 | `ANULA` deja saldos negativos (CM-N2): permite sacar dinero que ya no existe. | Rechazar la anulación si el saldo resultante es negativo, o pasarla a revisión manual. |
| RI-02 | El límite de transferencia es solo por operación (CM-T2): 10 transferencias de 100000 pasan. | Agregar un límite acumulado diario por cuenta de origen. |
| RI-03 | El dígito de control es un checksum público, no una firma (IG-05): cualquiera lo calcula, así que solo detecta errores de tipeo, no fraude. | Firmar los mensajes con HMAC con una clave por cliente. |
| RI-04 | PING ignora el control (IG-07): es una inconsistencia que un cliente podría usar para sondear. | Validar el control en todos los comandos. |
| RI-05 | La `sugerencia` de E301 (CM-02) revela los comandos internos a quien adivine. | Quitarla en producción o mostrarla solo con un modo debug. |
| RI-06 | Los depósitos no tienen límite salvo 10 dígitos (CM-D1), y ALTA no valida el nombre (CM-A2). | Límites de depósito y validación del nombre (longitud, caracteres). |
| RI-07 | Rarezas de contrato: `recieved`, `cuentaId` vs `cuenta_id`, el espacio final en E301 y la anulación repetida que da 200 con `ok:false`. | Versionar la API (v2) con nombres coherentes y mantener v1 por compatibilidad. |
| RI-09 | **Comando oculto `HALT`** (CM-H3): cualquier cliente con token puede detener el servicio. La "confirmación" es solo mandar `1`. | Quitarlo de la API pública. Si hace falta, moverlo a un endpoint de administración con otra credencial y doble confirmación (un token de un solo uso). |
| RI-10 | [v2] El bloqueo se levanta con un depósito de 1 centavo (CM-T8): no protege nada, cualquiera lo desbloquea. | Desbloqueo solo por un canal verificado (soporte, segundo factor) o con expiración temporal. |
| RI-11 | [v2] El formato del saldo cambió de número a string sin versionar la API (CM-C1b): rompe a los clientes existentes. | Publicar la v2 en una ruta o header de versión y mantener la v1 durante una migración. |
| RI-08 | El límite de 8 KB (IN-11) existe, pero no está documentado y responde con un código propio (E101). | Documentarlo en el contrato y mandar `Retry`/tamaño máximo en la respuesta. |

# Especificación · Servicio "caja negra" (Reto 2)

Autora: Jaissel Nicol Pérez Marten · Frontier BOG/26 · 10 oct 2026
Evidencia: los números `#N` son el campo `id` de `experimentos.jsonl`. `ej.N` es la línea N de `pruebas/ejemplos.jsonl`.
Confianza: **confirmado** (lo probé y se repite), **probable** (lo vi una vez o lo infiero), **supuesto** (no lo probé; es lo que hace el reemplazo por defecto).

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
| IN-11 | No se observó un límite de longitud para `m`: se aceptaron 300 y 2000 caracteres. | #2489, #2490 | probable |
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
| CM-03 | Si dos comandos empatan en distancia, se sugiere el primero en el orden PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA. | — | supuesto |
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
| CM-C1 | Responde `200 {"cuenta_id":"AC-0001","saldo":<entero>}`. Ojo: la clave es `cuenta_id`, mientras que ALTA usa `cuentaId`. | #2534, #2550, ej.5 | confirmado |
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
| CM-T1 | Orden de validación: monto (E303) → origen = destino (`400 E304 "origen y destino iguales"`) → existencia de ambas cuentas (E401) → límite (E506) → saldo (E507). | #2600, #2657, #2601, #2602, #2573, #2572 | confirmado |
| CM-T2 | El límite es **por operación**: monto > 100000 da `422 E506 "límite excedido"`, y 100000 exacto pasa. No es acumulado ni por destino. | #2559–#2563, ej.9, ej.10 | confirmado |
| CM-T3 | Si el saldo del origen es menor que el monto, responde `422 E507 "saldo insuficiente"`. Se puede transferir el saldo exacto. | #2603–#2605, ej.16 | confirmado |
| CM-T4 | Si todo está bien, mueve el saldo y responde `200 {"status":"recieved","operacionId":"OP-NNNN"}`. | #2560, #2564, #2565, ej.7 | confirmado |

**ANULA** · `ANULA;<operación>;ctl`

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CM-N1 | Revierte la operación y responde `200 {"ok":true,"anulada":"OP-NNNN"}`. En un depósito resta el monto de la cuenta. En una transferencia devuelve al origen y resta al destino. | #2579–#2583, ej.13 | confirmado |
| CM-N2 | La reversión **no revisa el saldo**: puede dejar saldos negativos (-3000). | #2580 | confirmado |
| CM-N3 | Anular algo ya anulado responde `200 {"ok":false,"motivo":"ya anulada"}`, sin error HTTP. | #2589, ej.14 | confirmado |
| CM-N4 | Si la operación no existe (incluidos `op-0002` en minúsculas o un id de cuenta), responde `404 E402 "operación inexistente"`. | #2584–#2586 | confirmado |

## 4. Memoria entre requests

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| ME-01 | Se recuerdan las cuentas, sus saldos y las operaciones con su estado de anulación. | #2550, #2564, #2589 | confirmado |
| ME-02 | Los contadores AC y OP son secuenciales, independientes entre sí y vuelven a 1 con el reset. | #2536–#2542, #2555–#2558 | confirmado |
| ME-03 | Una operación rechazada no consume número de OP. Anular tampoco: la siguiente operación sigue la secuencia. | #2559, #2560, #2587 | confirmado |
| ME-04 | El header `X-Req` es un contador de requests del token que **no** vuelve a cero con el reset (en #2631 vale 2615). Los headers no se comparan, así que el reemplazo no lo replica. | campo `x_req` del log | probable |

## 5. Errores (orden de evaluación)

Para cada request se aplica el **primer** error de esta lista que corresponda:

| Orden | Código | Status | Cuerpo exacto | Evidencia |
|---|---|---|---|---|
| 1 | E404 | 404 | `{"error":"E404","mensaje":"ruta desconocida"}` | #2469–#2478 |
| 2 | E001 | 401 | `{"error":"E001","mensaje":"no autorizado"}` | #2463–#2468 |
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
| 15 | E506 | 422 | `{"error":"E506","mensaje":"límite excedido"}` | #2572 |
| 16 | E507 | 422 | `{"error":"E507","mensaje":"saldo insuficiente"}` | #2603 |

## 6. Cambios durante el día

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CD-01 | Hasta las 11:45 no hubo diferencias con la versión de la mañana: los 20 ejemplos, grabados en la mañana, se reproducen idénticos en el reemplazo, que fue construido con datos de 11:00 a 11:45. | replay de ej.1–20 y del log: 2671/2671 pasos idénticos | confirmado |
| CD-02 | Está anunciado un incidente a las 15:30. Plan de detección: volver a correr las secuencias del log contra el original (`replay.py` apuntando al original con el token personal) y comparar con lo grabado. Cada diferencia se anota aquí con hora, ids nuevos y cambio. | (pendiente) | — |

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
| RI-08 | `m` sin límite de longitud (IN-11): riesgo de abuso de memoria y CPU. | Rechazar cuerpos de más de N KB con 413. |

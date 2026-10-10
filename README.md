# Reto 2 · La caja negra: reemplazo

Clon del servicio "caja negra" (Frontier BOG/26). Responde igual que el original: mismo status y mismo cuerpo, errores incluidos.

| Archivo | Qué es |
|---|---|
| `app.py` | El reemplazo (FastAPI, estado en memoria, 1 proceso) |
| `control.py` | Cálculo del dígito de control (MOD 97-10) |
| `enviar.py` / `explorar.py` | Explorador: manda experimentos al original y los anota en `experimentos.jsonl` |
| `replay.py` | Repite las secuencias grabadas contra el clon y mide el % de coincidencia |
| `especificacion.md` | Especificación del servicio, con evidencia |
| `experimentos.jsonl` | Log de experimentos |
| `RETO.md` | Enunciado original |

## Correr localmente

```bash
pip install -r requirements.txt
TOKEN_EQUIPO=<token> uvicorn app:app --port 8000
python replay.py http://127.0.0.1:8000
```

## Desplegar (Railway)

Variable de entorno `TOKEN_EQUIPO`. El inicio y las réplicas (1) están en `railway.json`.

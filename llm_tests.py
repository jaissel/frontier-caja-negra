"""Explorador asistido por LLM (OpenRouter): el modelo lee la especificación y propone casos difíciles.

Cada caso se manda al original (queda en experimentos.jsonl con la hipótesis del LLM) y al clon, y se compara.
El LLM no calcula el dígito de control: lo calcula control.py.

Uso: python llm_tests.py <url_clon> [n_casos]
"""
import json
import os
import sys

import httpx2 as httpx
from dotenv import load_dotenv
from openai import OpenAI

from control import firmar
from enviar import crudo, reset

load_dotenv()
CLON = sys.argv[1].rstrip("/")
N = int(sys.argv[2]) if len(sys.argv) > 2 else 30
MODELO = os.environ.get("MODELO_LLM", "anthropic/claude-sonnet-5.5")
HC = {"Authorization": f"Bearer {os.environ['TOKEN_EQUIPO'].strip()}"}
cli = httpx.Client(timeout=10)
llm = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"].strip())

INSTRUCCIONES = f"""Eres un tester experto en ingeniería inversa. Abajo está la especificación de un servicio HTTP.
Propón {N} casos de prueba (secuencias que empiezan tras un reset) que tengan alta probabilidad de revelar
comportamientos que la especificación NO describe o describe mal: combinaciones raras de comandos, órdenes
de errores no probados, interacciones de estado (bloqueos, anulaciones, HALT, saldos negativos), bordes de
formato. Mezcla casos de 1 request, de 2-5 y de 6-12.

Responde en formato JSONL: UNA línea por caso, cada línea un objeto JSON válido, sin texto extra ni ```:
{{"hipotesis": "qué comportamiento pruebas", "pasos": [PASO, ...]}}
donde PASO es uno de:
  {{"cuerpo": "COMANDO;arg1;arg2"}}             -> se le agrega el dígito de control correcto
  {{"cuerpo": "COMANDO;arg1", "control": "77"}} -> se manda con ese control literal (para probar controles malos)
  {{"m_literal": "texto exacto de m"}}          -> m tal cual, sin agregar nada
No inventes campos. No uses textos de más de 200 caracteres. Los ids de cuenta son AC-0001, AC-0002... en orden de ALTA; los de operación OP-0001...

ESPECIFICACIÓN:
"""


def pedir_casos():
    spec = open("especificacion.md", encoding="utf-8").read()
    r = llm.chat.completions.create(model=MODELO, messages=[{"role": "user", "content": INSTRUCCIONES + spec}],
                                    max_tokens=8000)
    texto = r.choices[0].message.content
    with open("llm_respuesta.txt", "w", encoding="utf-8") as f:
        f.write(texto)
    casos = []
    for linea in texto.splitlines():
        linea = linea.strip().rstrip(",")
        if not linea.startswith("{"):
            continue
        try:
            casos.append(json.loads(linea))
        except ValueError:
            print("  (línea inválida del LLM, se salta)")
    return casos


def a_mensaje(paso):
    if "m_literal" in paso:
        return paso["m_literal"]
    if "control" in paso:
        return f"{paso['cuerpo']};{paso['control']}"
    return firmar(paso["cuerpo"])


def main():
    casos = pedir_casos()
    print(f"El LLM ({MODELO}) propuso {len(casos)} casos")
    ok = pasos = pasos_ok = 0
    for n, caso in enumerate(casos, 1):
        seq = f"llm-{n:03d}"
        reset()
        cli.post(CLON + "/__reset", headers=HC)
        bien = True
        for paso in caso.get("pasos", []):
            try:
                m = a_mensaje(paso)
            except (KeyError, TypeError):
                continue
            lo = crudo("POST", "/msg", seq, f"[LLM] {caso.get('hipotesis', '')}", json_body={"m": m})
            rc = cli.post(CLON + "/msg", headers=HC, json={"m": m})
            try:
                bc = rc.json()
            except ValueError:
                bc = rc.text
            pasos += 1
            if (rc.status_code, bc) == (lo["status"], lo["response"]):
                pasos_ok += 1
            else:
                bien = False
                print(f"FALLA {seq} #{lo['id']} m={m!r}\n   hipótesis: {caso.get('hipotesis')}\n"
                      f"   original: {lo['status']} {json.dumps(lo['response'], ensure_ascii=False)}\n"
                      f"   clon:     {rc.status_code} {json.dumps(bc, ensure_ascii=False)}")
        ok += bien
    print(f"\nCasos que pasan: {ok}/{len(casos)}   Pasos idénticos: {pasos_ok}/{pasos}")


if __name__ == "__main__":
    main()

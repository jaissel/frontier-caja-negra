"""Corre un lote de experimentos contra el original. Uso: python explorar.py <lote>"""
import sys

from control import firmar
from enviar import crudo, mostrar, msg, reset, HEADERS


def f(seq, cuerpo, hip):
    """Manda el cuerpo con su control correcto."""
    mostrar(msg(seq, firmar(cuerpo), hip))


def m(seq, texto, hip):
    """Manda el texto tal cual."""
    mostrar(msg(seq, texto, hip))


def lote_entrada():
    S = "e1"; reset()
    mostrar(crudo("POST", "/msg", S, "sin header Authorization", headers={}, json_body={"m": "PING;1"}))
    mostrar(crudo("POST", "/msg", S, "token inventado", headers={"Authorization": "Bearer xxx"}, json_body={"m": "PING;1"}))
    mostrar(crudo("POST", "/msg", S, "Authorization sin Bearer", headers={"Authorization": HEADERS["Authorization"][7:]}, json_body={"m": "PING;1"}))
    mostrar(crudo("POST", "/msg", S, "esquema bearer en minúsculas", headers={"Authorization": "bearer " + HEADERS["Authorization"][7:]}, json_body={"m": "PING;1"}))
    mostrar(crudo("GET", "/health", S, "health sin token", headers={}))
    mostrar(crudo("POST", "/__reset", S, "reset sin token", headers={}))
    mostrar(crudo("GET", "/msg", S, "GET a /msg"))
    mostrar(crudo("PUT", "/msg", S, "PUT a /msg", json_body={"m": "PING;1"}))
    mostrar(crudo("GET", "/no-existe", S, "ruta inexistente GET con token"))
    mostrar(crudo("POST", "/no-existe", S, "ruta inexistente POST con token", json_body={"m": "PING;1"}))
    mostrar(crudo("GET", "/no-existe", S, "ruta inexistente sin token", headers={}))
    mostrar(crudo("GET", "/", S, "raíz con token"))
    mostrar(crudo("POST", "/health", S, "POST a /health"))
    mostrar(crudo("GET", "/__reset", S, "GET a /__reset"))
    mostrar(crudo("POST", "/msg/", S, "/msg con barra final", json_body={"m": "PING;1"}))
    mostrar(crudo("POST", "/MSG", S, "/MSG en mayúsculas", json_body={"m": "PING;1"}))


def lote_cuerpo():
    S = "e2"; reset()
    mostrar(crudo("POST", "/msg", S, "cuerpo vacío", cuerpo=b""))
    mostrar(crudo("POST", "/msg", S, "cuerpo no JSON", cuerpo=b"PING;1"))
    mostrar(crudo("POST", "/msg", S, "JSON roto", cuerpo=b'{"m": "PING;1"'))
    mostrar(crudo("POST", "/msg", S, "JSON sin campo m", json_body={"x": "PING;1"}))
    mostrar(crudo("POST", "/msg", S, "m numérico", json_body={"m": 5}))
    mostrar(crudo("POST", "/msg", S, "m null", json_body={"m": None}))
    mostrar(crudo("POST", "/msg", S, "m vacío", json_body={"m": ""}))
    mostrar(crudo("POST", "/msg", S, "JSON array", json_body=["PING;1"]))
    mostrar(crudo("POST", "/msg", S, "campos extra", json_body={"m": "PING;1", "z": 1}))
    mostrar(crudo("POST", "/msg", S, "m con espacios alrededor", json_body={"m": " PING;1 "}))
    mostrar(crudo("POST", "/msg", S, "m muy largo (300)", json_body={"m": "PING;" + "1" * 300}))
    mostrar(crudo("POST", "/msg", S, "m muy largo (2000)", json_body={"m": "PING;" + "1" * 2000}))
    mostrar(crudo("POST", "/msg", S, "string JSON plano", json_body="PING;1"))


def lote_parseo():
    S = "e3"; reset()
    m(S, ";", "solo separador")
    m(S, "PING;", "control vacío en PING")
    m(S, "CONSULTA", "comando sin nada")
    m(S, "CONSULTA;", "control vacío")
    m(S, "CONSULTA;;14", "argumento vacío")
    m(S, ";CONSULTA;14", "campo vacío al inicio")
    m(S, "CONSULTA;AC-0001;14;", "separador final")
    m(S, "CONSULTA;AC-0001;-14", "control negativo")
    m(S, "CONSULTA;AC-0001; 14", "control con espacio")
    m(S, "CONSULTA;AC-0001;14.0", "control decimal")
    m(S, "CONSULTA;AC-0001;014", "control con cero a la izquierda")
    m(S, "CONSULTA;AC-0001;1e1", "control notación científica")
    m(S, "XXX;1", "comando desconocido con control inválido")
    f(S, "XXX", "comando desconocido con control válido")
    m(S, "SALDOS;AC-0001;0", "comando desconocido, control incorrecto: ¿E301 o E202?")
    m(S, "CONSULTA;AC-0001;AC-0002;0", "aridad mala y control malo: ¿E302 o E202?")
    f(S, "CONSULTA;AC-0001;AC-0002", "aridad mala con control válido")
    m(S, "CONSULTA;AC-0001;5X", "control mal formado")
    m(S, "XXX;5X", "comando desconocido + control mal formado")
    m(S, "CONSULTA;A;B;5X", "aridad + control mal formado")
    f(S, "consulta;AC-0001", "comando todo en minúsculas")
    f(S, " CONSULTA;AC-0001", "espacio antes del comando")
    f(S, "CONSULTA ;AC-0001", "espacio después del comando")
    f(S, "PING", "PING sin argumentos con control (PING;n)")
    m(S, "PING;1;2", "PING con argumento extra")
    m(S, "PING;a;b;c", "PING con muchos campos")
    f(S, "CONSULTA;ac-0001", "id de cuenta en minúsculas")
    f(S, "CONSULTA;AC-1", "id de cuenta corto")
    f(S, "CONSULTA;AC-00001", "id con 5 dígitos")
    f(S, "CONSULTA;XX-0001", "prefijo distinto")
    f(S, "CONSULTA;AC0001", "id sin guion")


def lote_alta():
    S = "e4"; reset()
    f(S, "ALTA;Ana", "ALTA simple")
    f(S, "ALTA;Ana", "ALTA mismo nombre repetido")
    f(S, "ALTA;", "ALTA nombre vacío")
    f(S, "ALTA;A", "nombre de 1 letra")
    f(S, "ALTA;Ana Maria", "nombre con espacio")
    f(S, "ALTA;José", "nombre con tilde")
    f(S, "ALTA;Ana2", "nombre con número")
    f(S, "ALTA;123", "nombre numérico")
    f(S, "ALTA;" + "A" * 40, "nombre de 40 letras")
    f(S, "ALTA;" + "A" * 200, "nombre de 200 letras")
    f(S, "ALTA;Ana-Lu", "nombre con guion")
    f(S, "CONSULTA;AC-0001", "saldo inicial de cuenta nueva")
    f(S, "CONSULTA;AC-0002", "cuenta duplicada existe?")


def lote_deposito():
    S = "e5"; reset()
    f(S, "ALTA;Ana", "crear AC-0001")
    f(S, "ALTA;Beto", "crear AC-0002")
    for monto, h in [("0", "monto cero"), ("-5", "monto negativo"), ("10.5", "monto decimal"), ("abc", "monto no numérico"),
                     ("1", "monto 1"), ("007", "monto con ceros a la izquierda"), ("999999999", "monto enorme"),
                     ("1000000", "un millón"), ("1e3", "notación científica"), (" 5", "monto con espacio"), ("+5", "monto con signo +"),
                     ("", "monto vacío")]:
        f(S, f"DEPOSITO;AC-0001;{monto}", h)
    f(S, "CONSULTA;AC-0001", "saldo tras depósitos")
    f(S, "DEPOSITO;AC-0099;100", "depósito a cuenta inexistente")
    f(S, "DEPOSITO;ZZ;100", "depósito a id mal formado")
    f(S, "DEPOSITO;AC-0002", "depósito sin monto (aridad)")
    f(S, "DEPOSITO;AC-0099;-5", "cuenta inexistente + monto inválido: orden")


def lote_transfer():
    S = "e6"; reset()
    f(S, "ALTA;Ana", "AC-0001"); f(S, "ALTA;Beto", "AC-0002"); f(S, "ALTA;Caro", "AC-0003")
    f(S, "DEPOSITO;AC-0001;1000000", "fondear AC-0001")
    f(S, "TRANSFER;AC-0001;AC-0002;100001", "límite por operación justo arriba de 100000")
    f(S, "TRANSFER;AC-0001;AC-0002;100000", "límite exacto 100000")
    f(S, "TRANSFER;AC-0001;AC-0002;100000", "segunda de 100000: ¿límite acumulado?")
    f(S, "TRANSFER;AC-0001;AC-0003;50000", "otra cuenta destino: ¿límite por origen?")
    f(S, "TRANSFER;AC-0001;AC-0002;1", "tras 250000 transferidos")
    f(S, "CONSULTA;AC-0001", "saldo origen")
    f(S, "CONSULTA;AC-0002", "saldo destino")
    f(S, "TRANSFER;AC-0001;AC-0001;10", "transferencia a la misma cuenta")
    f(S, "TRANSFER;AC-0001;AC-0099;10", "destino inexistente")
    f(S, "TRANSFER;AC-0099;AC-0001;10", "origen inexistente")
    f(S, "TRANSFER;AC-0099;AC-0098;10", "ambos inexistentes")
    f(S, "TRANSFER;AC-0001;AC-0002;0", "monto cero")
    f(S, "TRANSFER;AC-0001;AC-0002;-1", "monto negativo")
    f(S, "TRANSFER;AC-0002;AC-0003;999999", "saldo insuficiente y límite: orden")
    f(S, "TRANSFER;AC-0099;AC-0002;999999", "inexistente y límite: orden")
    f(S, "TRANSFER;AC-0001;AC-0002;abc", "monto no numérico")


def lote_anula():
    S = "e7"; reset()
    f(S, "ALTA;Ana", "AC-0001"); f(S, "ALTA;Beto", "AC-0002")
    f(S, "DEPOSITO;AC-0001;5000", "OP-0001 depósito")
    f(S, "TRANSFER;AC-0001;AC-0002;3000", "OP-0002 transfer")
    f(S, "ANULA;OP-0001", "anular depósito cuando el saldo ya se usó")
    f(S, "CONSULTA;AC-0001", "saldo tras anular depósito (¿negativo?)")
    f(S, "ANULA;OP-0002", "anular transfer")
    f(S, "CONSULTA;AC-0001", "saldo tras anular ambos")
    f(S, "CONSULTA;AC-0002", "saldo destino tras anular transfer")
    f(S, "ANULA;OP-0099", "anular operación inexistente")
    f(S, "ANULA;AC-0001", "anular con id de cuenta")
    f(S, "ANULA;op-0002", "id op en minúsculas")
    f(S, "DEPOSITO;AC-0001;10", "¿el contador OP sigue en 3 tras anular?")
    f(S, "ANULA;OP-0003", "anular el nuevo")
    f(S, "ANULA;OP-0002", "re-anular anulada")
    f(S, "ANULA", "ANULA sin argumentos")



def lote_extra():
    S = "e8"; reset()
    f(S, "ALTA;Ana", "AC-0001"); f(S, "ALTA;Beto", "AC-0002")
    f(S, "CONSULTA;ac-0001", "id en minúsculas con cuenta existente")
    f(S, "CONSULTA;AC-1", "id corto con cuenta existente")
    f(S, "CONSULTA; AC-0001", "id con espacio con cuenta existente")
    b = "CONSULTA;AC-0001"
    m(S, b + ";5", "control de 1 dígito incorrecto (bien formado?)")
    m(S, "PING;05", "PING con 05")
    f(S, "DEPOSITO;AC-0001;5", "OP-0001")
    m(S, "CONSULTA;AC-0001;05", "control con cero a la izquierda 05 (el correcto es 14)")
    f(S, "TRANSFER;AC-0001;AC-0001;-1", "E304 vs E303: misma cuenta y monto inválido")
    f(S, "TRANSFER;AC-0099;AC-0099;10", "E304 vs E401: misma cuenta inexistente")
    f(S, "TRANSFER;AC-0001;AC-0001;200000", "E304 vs E506")
    f(S, "TRANSFER;AC-0001;AC-0002;100000", "saldo insuficiente con monto en el límite")
    f(S, "TRANSFER;AC-0001;AC-0002;5", "transferir todo el saldo exacto")
    f(S, "TRANSFER;AC-0001;AC-0002;1", "saldo 0 insuficiente")
    f(S, "DEPOSITO;AC-0001;100000000000000000000", "monto gigante (1e20)")
    f(S, "DEPOSITO;AC-0001;200000", "depósito mayor al límite de transfer")
    f(S, "TRANSFER;AC-0001;AC-0002;" + "9" * 25, "transfer gigante")
    for cmd in ["CONSULT", "CONSULTAS", "CONSULTAA", "DEPOSIT", "DEPOSITOS", "TRANSFERIR", "TRANSFE", "ALT", "ALTAS", "ANUL", "PIN", "PINGG", "SALDO", "CONSUL", "XONSULTA", "ANULAR", "TRANSFERENCIA", "DEPÓSITO", "consult"]:
        f(S, f"{cmd};AC-0001", f"sugerencia de E301 para {cmd}")
    f(S, "ANULA;OP-0001;X", "ANULA con argumento extra")
    f(S, "ALTA;Ana;Lopez", "ALTA aridad 2")
    f(S, "CONSULTA", "CONSULTA sin argumento con control válido")


def lote_limites():
    S = "e9"; reset()
    f(S, "ALTA;Ana", "AC-0001")
    for mt in ["999999999", "1000000000", "2147483647", "2147483648", "4294967296", "9007199254740991", "9007199254740992", "99999999999", "999999999999999999", "1000000000000000000"]:
        f(S, f"DEPOSITO;AC-0001;{mt}", f"monto máximo: {mt}")
    f(S, "CONSULTA;AC-0001", "saldo acumulado tras montos grandes")
    for cmd in ["CONSU", "CONSULTAXYZ", "CONSULTAXY", "ANU", "AN", "PI", "P", "ABCD", "AL", "TRANSF", "DEPOS"]:
        f(S, f"{cmd};AC-0001", f"umbral de sugerencia E301: {cmd}")


if __name__ == "__main__":
    globals()["lote_" + sys.argv[1]]()

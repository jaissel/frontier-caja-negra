"""Dígito de control de la caja negra (estilo IBAN, MOD 97-10).

Se toma el mensaje SIN el último campo. Cada letra se reemplaza por su posición en el
abecedario (A=1 ... Z=26, sin importar mayúsculas), los dígitos quedan igual y todo lo
demás (; - espacios ...) se ignora. Con esa cadena de dígitos N:
    control = 98 - (N * 100 mod 97)
"""


def digitos(texto):
    out = []
    for ch in texto:
        if ch.isascii() and ch.isdigit():
            out.append(ch)
        elif ch.isascii() and ch.isalpha():
            out.append(str(ord(ch.upper()) - 64))
    return "".join(out)


def control(cuerpo):
    n = int(digitos(cuerpo) or "0")
    return 98 - (n * 100) % 97


def firmar(cuerpo):
    """'CONSULTA;AC-0001' -> 'CONSULTA;AC-0001;14'"""
    return f"{cuerpo};{control(cuerpo)}"

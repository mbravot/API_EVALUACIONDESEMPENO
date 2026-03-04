import re

def validar_rut(rut: str) -> bool:
    rut = rut.replace(".", "").replace("-", "").upper()

    if not re.match(r'^\d{7,8}[0-9K]$', rut):
        return False

    cuerpo = rut[:-1]
    dv_ingresado = rut[-1]

    suma = 0
    multiplicador = 2

    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador += 1
        if multiplicador > 7:
            multiplicador = 2

    resto = suma % 11
    dv_calculado = 11 - resto
    if dv_calculado == 11:
        dv_calculado = "0"
    elif dv_calculado == 10:
        dv_calculado = "K"
    else:
        dv_calculado = str(dv_calculado)

    return dv_ingresado == dv_calculado

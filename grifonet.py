import socket
import ipaddress
import subprocess
import concurrent.futures
import json
import os
import platform
import re
from datetime import datetime


# ============================================================
# GRIFONET v3.0
# Herramienta sencilla de diagnóstico de red para Windows
# ============================================================

VERSION = "3.0"


# ============================================================
# COLORES
# ============================================================

RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"


# ============================================================
# UTILIDADES
# ============================================================

def limpiar():
    os.system("cls" if os.name == "nt" else "clear")


def pausa():
    print()
    input("  Pulsa ENTER para volver al menú...")


def linea(caracter="─", largo=60):
    print(GRAY + caracter * largo + RESET)


def titulo():
    print(CYAN + r"""
╔══════════════════════════════════════════════════════╗
║                                                      ║
║                    GRIFONET                          ║
║              NETWORK DIAGNOSTIC TOOL                 ║
║                                                      ║
║                      v3.0                            ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
""" + RESET)


def encabezado(texto):
    print()
    print(CYAN + "╔" + "═" * 56 + "╗" + RESET)
    print(CYAN + "║" + RESET + f" {texto:<55}" + CYAN + "║" + RESET)
    print(CYAN + "╚" + "═" * 56 + "╝" + RESET)
    print()


# ============================================================
# INFORMACIÓN LOCAL
# ============================================================

def obtener_ip_local():

    try:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        sock.connect(("8.8.8.8", 80))

        ip = sock.getsockname()[0]

        sock.close()

        return ip

    except Exception:

        try:

            return socket.gethostbyname(
                socket.gethostname()
            )

        except Exception:

            return "127.0.0.1"


def obtener_nombre_equipo():

    try:
        return socket.gethostname()

    except Exception:
        return "-"


def obtener_hostname(ip):

    try:

        return socket.gethostbyaddr(ip)[0]

    except Exception:

        return "-"


# ============================================================
# DATOS DE WINDOWS
# ============================================================

def obtener_datos_red_windows():

    datos = {
        "ip": obtener_ip_local(),
        "mascara": "-",
        "gateway": "-",
        "adaptador": "-",
        "ssid": "-",
        "estado": "DESCONOCIDO"
    }

    try:

        resultado = subprocess.run(
            ["ipconfig", "/all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        texto = resultado.stdout

        ip_local = datos["ip"]

        lineas = texto.splitlines()

        nombre_adaptador = "-"

        for linea_texto in lineas:

            # ------------------------------------------------
            # ADAPTADOR
            # ------------------------------------------------

            if (
                "adapter" in linea_texto.lower()
                or "adaptador" in linea_texto.lower()
            ):

                partes = re.split(
                    r":\s*$",
                    linea_texto.strip()
                )

                if partes:

                    nombre_adaptador = partes[0]

            # ------------------------------------------------
            # IPv4
            # ------------------------------------------------

            if (
                "IPv4" in linea_texto
                or "Dirección IPv4" in linea_texto
            ):

                match = re.search(
                    r"(\d{1,3}(?:\.\d{1,3}){3})",
                    linea_texto
                )

                if match:

                    ip_encontrada = match.group(1)

                    if ip_encontrada == ip_local:

                        datos["ip"] = ip_encontrada

                        datos["adaptador"] = (
                            nombre_adaptador
                        )

            # ------------------------------------------------
            # MÁSCARA
            # ------------------------------------------------

            if (
                "Subnet Mask" in linea_texto
                or "Máscara de subred" in linea_texto
            ):

                match = re.search(
                    r"(\d{1,3}(?:\.\d{1,3}){3})",
                    linea_texto
                )

                if match:

                    datos["mascara"] = match.group(1)

            # ------------------------------------------------
            # GATEWAY
            # ------------------------------------------------

            if (
                "Default Gateway" in linea_texto
                or "Puerta de enlace predeterminada"
                in linea_texto
            ):

                match = re.search(
                    r"(\d{1,3}(?:\.\d{1,3}){3})",
                    linea_texto
                )

                if match:

                    datos["gateway"] = match.group(1)

    except Exception:

        pass


    # ========================================================
    # WIFI
    # ========================================================

    try:

        resultado_wifi = subprocess.run(
            [
                "netsh",
                "wlan",
                "show",
                "interfaces"
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        texto_wifi = resultado_wifi.stdout

        for linea_texto in texto_wifi.splitlines():

            limpia = linea_texto.strip()

            # ------------------------------------------------
            # SSID
            # ------------------------------------------------

            if re.match(
                r"^SSID\s*:",
                limpia,
                re.IGNORECASE
            ):

                valor = limpia.split(
                    ":",
                    1
                )[1].strip()

                if valor:

                    datos["ssid"] = valor

            # ------------------------------------------------
            # ESTADO INGLES
            # ------------------------------------------------

            if re.match(
                r"^State\s*:",
                limpia,
                re.IGNORECASE
            ):

                valor = limpia.split(
                    ":",
                    1
                )[1].strip()

                datos["estado"] = valor.upper()

            # ------------------------------------------------
            # ESTADO ESPAÑOL
            # ------------------------------------------------

            if re.match(
                r"^Estado\s*:",
                limpia,
                re.IGNORECASE
            ):

                valor = limpia.split(
                    ":",
                    1
                )[1].strip()

                datos["estado"] = valor.upper()

    except Exception:

        pass

    return datos


# ============================================================
# RED LOCAL
# ============================================================

def detectar_red_local():

    ip = obtener_ip_local()

    try:

        partes = ip.split(".")

        red = (
            f"{partes[0]}."
            f"{partes[1]}."
            f"{partes[2]}."
            "0/24"
        )

        return red

    except Exception:

        return "192.168.1.0/24"


# ============================================================
# PING
# ============================================================

def ping(ip):

    try:

        resultado = subprocess.run(
            [
                "ping",
                "-n",
                "1",
                "-w",
                "500",
                str(ip)
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return resultado.returncode == 0

    except Exception:

        return False


# ============================================================
# ESCANEAR HOST
# ============================================================

def escanear_host(ip):

    ip = str(ip)

    if ping(ip):

        return {
            "ip": ip,
            "estado": "ONLINE",
            "hostname": obtener_hostname(ip)
        }

    return None


# ============================================================
# ESCANEAR RED
# ============================================================

def escanear_red(red):

    try:

        red_obj = ipaddress.ip_network(
            red,
            strict=False
        )

    except ValueError:

        print(
            RED +
            "Red no válida." +
            RESET
        )

        return []

    hosts = list(red_obj.hosts())

    resultados = []

    total = len(hosts)

    completados = 0

    print(
        YELLOW +
        f"Escaneando {red}" +
        RESET
    )

    print(
        GRAY +
        f"Direcciones: {total}" +
        RESET
    )

    print()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=50
    ) as executor:

        tareas = [
            executor.submit(
                escanear_host,
                ip
            )
            for ip in hosts
        ]

        for tarea in concurrent.futures.as_completed(
            tareas
        ):

            completados += 1

            resultado = tarea.result()

            porcentaje = int(
                completados / total * 100
            )

            bloques = int(
                porcentaje / 5
            )

            barra = (
                GREEN +
                "█" * bloques +
                GRAY +
                "░" * (20 - bloques) +
                RESET
            )

            print(
                f"\r  [{barra}] "
                f"{porcentaje:3d}%",
                end="",
                flush=True
            )

            if resultado:

                resultados.append(
                    resultado
                )

    print("\n")

    resultados.sort(
        key=lambda x: ipaddress.ip_address(
            x["ip"]
        )
    )

    return resultados


# ============================================================
# MOSTRAR RED
# ============================================================

def mostrar_hosts(resultados):

    encabezado(
        "RESULTADOS DE LA RED LOCAL"
    )

    if not resultados:

        print(
            RED +
            "  No se encontraron equipos." +
            RESET
        )

        print()

        print(
            YELLOW +
            "  Un dispositivo puede estar conectado "
            "y no responder al ping." +
            RESET
        )

        return

    print(
        WHITE +
        f"  {'IP':<18}"
        f"{'ESTADO':<14}"
        f"{'HOSTNAME'}" +
        RESET
    )

    linea(largo=60)

    for host in resultados:

        print(
            f"  {host['ip']:<16}"
            f"{GREEN}{host['estado']:<14}{RESET}"
            f"{host['hostname']}"
        )

    linea(largo=60)

    print(
        WHITE +
        f"\n  Equipos encontrados: "
        f"{len(resultados)}" +
        RESET
    )

    print()

    print(
        GRAY +
        "  Puedes seleccionar y copiar las IP "
        "directamente desde esta pantalla." +
        RESET
    )


# ============================================================
# PUERTOS
# ============================================================

PUERTOS_COMUNES = {

    21: "FTP",
    22: "SSH",
    23: "TELNET",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    135: "MSRPC",
    139: "NETBIOS",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    8080: "HTTP-ALT"
}


def comprobar_puerto(
    ip,
    puerto,
    timeout=0.5
):

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    sock.settimeout(timeout)

    try:

        resultado = sock.connect_ex(
            (ip, puerto)
        )

        if resultado == 0:

            return "OPEN"

        return "CLOSED"

    except Exception:

        return "ERROR"

    finally:

        sock.close()


def escanear_puertos_comunes(ip):

    encabezado(
        f"PUERTOS DE {ip}"
    )

    abiertos = []

    for puerto, servicio in PUERTOS_COMUNES.items():

        estado = comprobar_puerto(
            ip,
            puerto
        )

        if estado == "OPEN":

            print(
                GREEN +
                f"  [+] {puerto:<6}"
                f"OPEN       {servicio}" +
                RESET
            )

            abiertos.append({
                "puerto": puerto,
                "servicio": servicio,
                "estado": "OPEN"
            })

        else:

            print(
                GRAY +
                f"  [-] {puerto:<6}"
                f"CLOSED     {servicio}" +
                RESET
            )

    linea()

    print(
        f"\n  Puertos abiertos: "
        f"{len(abiertos)}"
    )

    return abiertos


# ============================================================
# ESCANEO PERSONALIZADO
# ============================================================

def escaneo_personalizado():

    encabezado(
        "ESCANEO PERSONALIZADO"
    )

    ip = input(
        "  IP del equipo: "
    ).strip()

    try:

        ipaddress.ip_address(ip)

    except ValueError:

        print(
            RED +
            "\n  IP no válida." +
            RESET
        )

        pausa()

        return []

    inicio_txt = input(
        "  Puerto inicial [1]: "
    ).strip()

    fin_txt = input(
        "  Puerto final [1024]: "
    ).strip()

    try:

        inicio = (
            int(inicio_txt)
            if inicio_txt
            else 1
        )

        fin = (
            int(fin_txt)
            if fin_txt
            else 1024
        )

    except ValueError:

        print(
            RED +
            "\n  Los puertos deben ser números." +
            RESET
        )

        pausa()

        return []

    if (
        inicio < 1
        or fin > 65535
        or inicio > fin
    ):

        print(
            RED +
            "\n  Rango incorrecto." +
            RESET
        )

        pausa()

        return []

    print()

    print(
        YELLOW +
        f"  Escaneando {ip}:"
        f"{inicio}-{fin}" +
        RESET
    )

    print()

    abiertos = []

    def revisar(puerto):

        estado = comprobar_puerto(
            ip,
            puerto,
            0.4
        )

        if estado == "OPEN":

            return puerto

        return None

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=100
    ) as executor:

        tareas = [
            executor.submit(
                revisar,
                puerto
            )
            for puerto in range(
                inicio,
                fin + 1
            )
        ]

        for tarea in concurrent.futures.as_completed(
            tareas
        ):

            resultado = tarea.result()

            if resultado is not None:

                abiertos.append(
                    resultado
                )

    abiertos.sort()

    encabezado(
        "PUERTOS ABIERTOS"
    )

    if not abiertos:

        print(
            YELLOW +
            "  No se encontraron puertos abiertos." +
            RESET
        )

    else:

        for puerto in abiertos:

            servicio = PUERTOS_COMUNES.get(
                puerto,
                "Desconocido"
            )

            print(
                GREEN +
                f"  [+] {puerto:<6}"
                f"OPEN       {servicio}" +
                RESET
            )

    return abiertos


# ============================================================
# ALERTA DE UBICACIÓN
# ============================================================

def mostrar_alerta_ubicacion():

    print()

    print(
        YELLOW +
        "╔════════════════════════════════════════════════════════════╗"
        + RESET
    )

    print(
        YELLOW +
        "║ PERMISO DE UBICACIÓN NECESARIO                             ║"
        + RESET
    )

    print(
        YELLOW +
        "╚════════════════════════════════════════════════════════════╝"
        + RESET
    )

    print()

    print(
        WHITE +
        "  Windows está bloqueando la consulta de redes Wi-Fi "
        "cercanas." +
        RESET
    )

    print()

    print(
        CYAN +
        "  Para permitir que GrifoNet consulte las redes Wi-Fi:"
        + RESET
    )

    print()

    print(
        "  1. Pulsa: "
        + WHITE +
        "WIN + R" +
        RESET
    )

    print()

    print(
        "  2. Copia y pega:"
    )

    print(
        "     " +
        GREEN +
        "ms-settings:privacy-location" +
        RESET
    )

    print()

    print(
        "  3. Pulsa "
        + WHITE +
        "ENTER" +
        RESET
        + "."
    )

    print()

    print(
        "  4. Activa los "
        + GREEN +
        "servicios de ubicación" +
        RESET
        + "."
    )

    print()

    print(
        GRAY +
        "  Después vuelve a GrifoNet y ejecuta nuevamente "
        "el escaneo Wi-Fi." +
        RESET
    )

    print()

    print(
        CYAN +
        "  ─────────────────────────────────────────────────────"
        + RESET
    )

    print()

    input(
        "  Pulsa ENTER para volver al menú..."
    )


# ============================================================
# ESCANEAR WI-FI
# ============================================================

def escanear_wifi():

    limpiar()

    titulo()

    encabezado(
        "REDES WI-FI CERCANAS"
    )

    print(
        YELLOW +
        "  Buscando redes disponibles..." +
        RESET
    )

    print()

    try:

        resultado = subprocess.run(
            [
                "netsh",
                "wlan",
                "show",
                "networks",
                "mode=bssid"
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        texto = (
            resultado.stdout +
            "\n" +
            resultado.stderr
        )

        # ====================================================
        # DETECTAR BLOQUEO DE UBICACIÓN
        # ====================================================

        texto_lower = texto.lower()

        if (
            "permiso de ubicación" in texto_lower
            or
            "permission" in texto_lower
            and "location" in texto_lower
            or
            "servicios de ubicación" in texto_lower
            or
            "location service" in texto_lower
        ):

            mostrar_alerta_ubicacion()

            return

        # ====================================================
        # SIN RESULTADOS
        # ====================================================

        if not resultado.stdout.strip():

            print(
                RED +
                "  Windows no devolvió redes Wi-Fi." +
                RESET
            )

            print()

            print(
                YELLOW +
                "  Si estás usando Windows 11, comprueba "
                "que los servicios de ubicación estén activos."
                + RESET
            )

            mostrar_alerta_ubicacion()

            return

        # ====================================================
        # PROCESAMIENTO
        # ====================================================

        redes = []

        red_actual = None

        for linea_texto in resultado.stdout.splitlines():

            limpia = linea_texto.strip()

            # ------------------------------------------------
            # SSID
            # ------------------------------------------------

            match_ssid = re.match(
                r"^SSID\s+\d+\s*:\s*(.*)$",
                limpia,
                re.IGNORECASE
            )

            if match_ssid:

                ssid = match_ssid.group(1).strip()

                red_actual = {
                    "ssid": ssid if ssid else "<OCULTA>",
                    "senal": "-",
                    "seguridad": "-",
                    "bssid": "-"
                }

                redes.append(
                    red_actual
                )

                continue

            if red_actual is None:
                continue

            # ------------------------------------------------
            # SEÑAL
            # ------------------------------------------------

            match_signal = re.match(
                r"^(Signal|Señal)\s*:\s*(.*)$",
                limpia,
                re.IGNORECASE
            )

            if match_signal:

                red_actual["senal"] = (
                    match_signal.group(2).strip()
                )

                continue

            # ------------------------------------------------
            # AUTENTICACIÓN
            # ------------------------------------------------

            match_auth = re.match(
                r"^(Authentication|Autenticación)\s*:\s*(.*)$",
                limpia,
                re.IGNORECASE
            )

            if match_auth:

                red_actual["seguridad"] = (
                    match_auth.group(2).strip()
                )

                continue

            # ------------------------------------------------
            # BSSID
            # ------------------------------------------------

            match_bssid = re.match(
                r"^BSSID\s+\d+\s*:\s*(.*)$",
                limpia,
                re.IGNORECASE
            )

            if match_bssid:

                red_actual["bssid"] = (
                    match_bssid.group(1).strip()
                )

        # ====================================================
        # SI NO SE ENCONTRARON REDES
        # ====================================================

        if not redes:

            print(
                YELLOW +
                "  No se encontraron redes Wi-Fi cercanas."
                + RESET
            )

            print()

            print(
                GRAY +
                "  Si la ubicación está desactivada en Windows 11,"
                + RESET
            )

            print(
                GRAY +
                "  Windows puede impedir que aparezcan las redes."
                + RESET
            )

            print()

            mostrar_alerta_ubicacion()

            return

        # ====================================================
        # MOSTRAR RESULTADOS
        # ====================================================

        print(
            WHITE +
            f"  {'#':<4}"
            f"{'SSID':<30}"
            f"{'SEÑAL':<10}"
            f"{'SEGURIDAD'}" +
            RESET
        )

        linea(largo=75)

        for numero, red in enumerate(
            redes,
            start=1
        ):

            ssid = red["ssid"]

            print(
                f"  {numero:<4}"
                f"{ssid[:28]:<30}"
                f"{red['senal']:<10}"
                f"{red['seguridad']}"
            )

        linea(largo=75)

        print(
            f"\n  Redes encontradas: "
            f"{len(redes)}"
        )

        # ====================================================
        # BSSID
        # ====================================================

        print()

        print(
            CYAN +
            "  BSSID detectados" +
            RESET
        )

        linea(largo=75)

        for numero, red in enumerate(
            redes,
            start=1
        ):

            print(
                f"  {numero}. "
                f"{red['ssid']:<25} "
                f"{red['bssid']}"
            )

        linea(largo=75)

    except FileNotFoundError:

        print(
            RED +
            "  No se encontró NETSH." +
            RESET
        )

        print(
            GRAY +
            "  Esta función requiere Windows." +
            RESET
        )

    except Exception as error:

        print(
            RED +
            f"  Error: {error}" +
            RESET
        )

    pausa()


# ============================================================
# INFORMACIÓN DE RED
# ============================================================

def informacion_red():

    limpiar()

    titulo()

    datos = obtener_datos_red_windows()

    ip = datos["ip"]

    try:

        red = str(
            ipaddress.ip_network(
                ip + "/24",
                strict=False
            )
        )

    except Exception:

        red = "-"

    encabezado(
        "INFORMACIÓN DE RED"
    )

    # ========================================================
    # EQUIPO
    # ========================================================

    print(
        MAGENTA +
        "  ┌─ EQUIPO" +
        RESET
    )

    print(
        f"  │  Nombre       : "
        f"{obtener_nombre_equipo()}"
    )

    print(
        f"  │  Sistema      : "
        f"{platform.system()}"
    )

    print(
        f"  │  Versión      : "
        f"{platform.release()}"
    )

    print(
        f"  │  Arquitectura : "
        f"{platform.machine()}"
    )

    print(
        "  └────────────────────────────────────────"
    )

    print()

    # ========================================================
    # CONEXIÓN
    # ========================================================

    print(
        CYAN +
        "  ┌─ CONEXIÓN" +
        RESET
    )

    print(
        f"  │  Adaptador    : "
        f"{datos['adaptador']}"
    )

    estado = datos["estado"]

    if (
        "CONNECTED" in estado
        or "CONECTADO" in estado
    ):

        estado_mostrar = (
            GREEN +
            estado +
            RESET
        )

    else:

        estado_mostrar = (
            YELLOW +
            estado +
            RESET
        )

    print(
        f"  │  Estado       : "
        f"{estado_mostrar}"
    )

    print(
        f"  │  SSID         : "
        f"{datos['ssid']}"
    )

    print(
        f"  │  IP local     : "
        f"{datos['ip']}"
    )

    print(
        f"  │  Máscara      : "
        f"{datos['mascara']}"
    )

    print(
        f"  │  Gateway      : "
        f"{datos['gateway']}"
    )

    print(
        "  └────────────────────────────────────────"
    )

    print()

    # ========================================================
    # RED
    # ========================================================

    print(
        GREEN +
        "  ┌─ RED" +
        RESET
    )

    print(
        f"  │  Red detectada: "
        f"{red}"
    )

    try:

        red_obj = ipaddress.ip_network(
            red,
            strict=False
        )

        hosts = red_obj.num_addresses - 2

    except Exception:

        hosts = "-"

    print(
        f"  │  Hosts        : "
        f"{hosts}"
    )

    print(
        "  └────────────────────────────────────────"
    )

    print()

    print(
        GRAY +
        "  Información obtenida directamente de Windows."
        + RESET
    )

    pausa()


# ============================================================
# BLOQUEAR / DESBLOQUEAR IP
# ============================================================

def validar_ip(ip):

    try:

        ipaddress.ip_address(ip)

        return True

    except ValueError:

        return False


def bloquear_ip():

    limpiar()

    titulo()

    encabezado(
        "BLOQUEAR IP"
    )

    print(
        GRAY +
        "  Crea una regla de Firewall para bloquear "
        "la comunicación saliente con la IP indicada."
        + RESET
    )

    print()

    ip = input(
        "  IP que deseas bloquear: "
    ).strip()

    if not validar_ip(ip):

        print()

        print(
            RED +
            "  ✗ La IP introducida no es válida."
            + RESET
        )

        pausa()

        return

    nombre_regla = (
        "GrifoNet_Block_" +
        ip.replace(".", "_").replace(":", "_")
    )

    comando = [
        "netsh",
        "advfirewall",
        "firewall",
        "add",
        "rule",
        f"name={nombre_regla}",
        "dir=out",
        "action=block",
        f"remoteip={ip}",
        "enable=yes"
    ]

    try:

        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        print()

        if resultado.returncode == 0:

            print(
                GREEN +
                "  ✓ IP bloqueada correctamente."
                + RESET
            )

            print()

            print(
                f"  IP     : {ip}"
            )

            print(
                f"  Regla  : {nombre_regla}"
            )

            print()

            print(
                GRAY +
                "  El bloqueo fue realizado mediante "
                "el Firewall de Windows."
                + RESET
            )

        else:

            print(
                RED +
                "  ✗ Windows no permitió crear la regla."
                + RESET
            )

            print()

            print(
                YELLOW +
                "  Esta función necesita ejecutar Python "
                "como administrador."
                + RESET
            )

            if resultado.stderr.strip():

                print()

                print(
                    GRAY +
                    resultado.stderr.strip() +
                    RESET
                )

    except Exception as error:

        print(
            RED +
            f"\n  Error: {error}" +
            RESET
        )

    pausa()


def desbloquear_ip():

    limpiar()

    titulo()

    encabezado(
        "DESBLOQUEAR IP"
    )

    print(
        GRAY +
        "  Elimina la regla de GrifoNet creada "
        "para esa IP."
        + RESET
    )

    print()

    ip = input(
        "  IP que deseas desbloquear: "
    ).strip()

    if not validar_ip(ip):

        print()

        print(
            RED +
            "  ✗ La IP introducida no es válida."
            + RESET
        )

        pausa()

        return

    nombre_regla = (
        "GrifoNet_Block_" +
        ip.replace(".", "_").replace(":", "_")
    )

    comando = [
        "netsh",
        "advfirewall",
        "firewall",
        "delete",
        "rule",
        f"name={nombre_regla}"
    ]

    try:

        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        print()

        if resultado.returncode == 0:

            print(
                GREEN +
                "  ✓ IP desbloqueada correctamente."
                + RESET
            )

            print()

            print(
                f"  IP     : {ip}"
            )

            print(
                f"  Regla  : {nombre_regla}"
            )

        else:

            print(
                YELLOW +
                "  No se encontró una regla de GrifoNet "
                "para esa IP."
                + RESET
            )

            print()

            print(
                GRAY +
                "  Si la regla existe pero Windows no permite "
                "modificarla, ejecuta Python como administrador."
                + RESET
            )

    except Exception as error:

        print(
            RED +
            f"\n  Error: {error}" +
            RESET
        )

    pausa()


# ============================================================
# GUARDAR RESULTADOS
# ============================================================

def guardar_resultados(resultados):

    limpiar()

    titulo()

    encabezado(
        "GUARDAR RESULTADOS"
    )

    if not resultados:

        print(
            YELLOW +
            "  No hay resultados para guardar."
            + RESET
        )

        pausa()

        return

    nombre = (
        "GrifoNet_" +
        datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        ) +
        ".json"
    )

    datos = {
        "herramienta": "GrifoNet",
        "version": VERSION,
        "fecha": datetime.now().isoformat(),
        "resultados": resultados
    }

    try:

        with open(
            nombre,
            "w",
            encoding="utf-8"
        ) as archivo:

            json.dump(
                datos,
                archivo,
                indent=4,
                ensure_ascii=False
            )

        print(
            GREEN +
            "  ✓ Resultados guardados correctamente."
            + RESET
        )

        print()

        print(
            f"  Archivo: {nombre}"
        )

    except Exception as error:

        print(
            RED +
            f"  Error: {error}" +
            RESET
        )

    pausa()


# ============================================================
# MENÚ PRINCIPAL
# ============================================================

def menu():

    ultimo_resultado = []

    while True:

        limpiar()

        titulo()

        ip_local = obtener_ip_local()

        print(
            GRAY +
            f"  IP local: {ip_local}" +
            RESET
        )

        print()

        # ====================================================
        # ESCANEO
        # ====================================================

        print(
            CYAN +
            "  ┌─ ESCANEO" +
            RESET
        )

        print(
            "  │  1. Escanear mi red local"
        )

        print(
            "  │  2. Escanear puertos comunes"
        )

        print(
            "  │  3. Escaneo personalizado"
        )

        print(
            "  │"
        )

        # ====================================================
        # INFORMACIÓN
        # ====================================================

        print(
            CYAN +
            "  ├─ INFORMACIÓN" +
            RESET
        )

        print(
            "  │  4. Información de red"
        )

        print(
            "  │  5. Escanear redes Wi-Fi cercanas"
        )

        print(
            "  │"
        )

        # ====================================================
        # CONTROL DE RED
        # ====================================================

        print(
            CYAN +
            "  ├─ CONTROL DE RED" +
            RESET
        )

        print(
            "  │  6. Bloquear IP"
        )

        print(
            "  │  7. Desbloquear IP"
        )

        print(
            "  │"
        )

        # ====================================================
        # RESULTADOS
        # ====================================================

        print(
            CYAN +
            "  ├─ RESULTADOS" +
            RESET
        )

        print(
            "  │  8. Guardar último resultado"
        )

        print(
            "  │"
        )

        print(
            CYAN +
            "  └─ 0. Salir" +
            RESET
        )

        print()

        opcion = input(
            "  GrifoNet > "
        ).strip()

        # ====================================================
        # 1 - RED LOCAL
        # ====================================================

        if opcion == "1":

            limpiar()

            titulo()

            red = detectar_red_local()

            print(
                f"  Red detectada: "
                f"{GREEN}{red}{RESET}"
            )

            print()

            resultados = escanear_red(
                red
            )

            ultimo_resultado = resultados

            mostrar_hosts(
                resultados
            )

            print()

            print(
                YELLOW +
                "  Los resultados quedan en pantalla."
                + RESET
            )

            print(
                GRAY +
                "  Selecciona y copia las IP que necesites."
                + RESET
            )

            pausa()

        # ====================================================
        # 2 - PUERTOS COMUNES
        # ====================================================

        elif opcion == "2":

            limpiar()

            titulo()

            encabezado(
                "ESCANEAR PUERTOS COMUNES"
            )

            ip = input(
                "  IP del equipo: "
            ).strip()

            try:

                ipaddress.ip_address(ip)

            except ValueError:

                print(
                    RED +
                    "\n  IP no válida." +
                    RESET
                )

                pausa()

                continue

            puertos = escanear_puertos_comunes(
                ip
            )

            ultimo_resultado = [{
                "ip": ip,
                "puertos": puertos
            }]

            pausa()

        # ====================================================
        # 3 - PERSONALIZADO
        # ====================================================

        elif opcion == "3":

            limpiar()

            titulo()

            resultado = escaneo_personalizado()

            ultimo_resultado = resultado

            pausa()

        # ====================================================
        # 4 - INFORMACIÓN
        # ====================================================

        elif opcion == "4":

            informacion_red()

        # ====================================================
        # 5 - WI-FI
        # ====================================================

        elif opcion == "5":

            escanear_wifi()

        # ====================================================
        # 6 - BLOQUEAR IP
        # ====================================================

        elif opcion == "6":

            bloquear_ip()

        # ====================================================
        # 7 - DESBLOQUEAR IP
        # ====================================================

        elif opcion == "7":

            desbloquear_ip()

        # ====================================================
        # 8 - GUARDAR
        # ====================================================

        elif opcion == "8":

            guardar_resultados(
                ultimo_resultado
            )

        # ====================================================
        # 0 - SALIR
        # ====================================================

        elif opcion == "0":

            limpiar()

            print()

            print(
                CYAN +
                "  ╔════════════════════════════════════╗"
                + RESET
            )

            print(
                CYAN +
                "  ║       GrifoNet finalizado         ║"
                + RESET
            )

            print(
                CYAN +
                "  ╚════════════════════════════════════╝"
                + RESET
            )

            print()

            break

        else:

            print()

            print(
                RED +
                "  Opción no válida." +
                RESET
            )

            pausa()


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":

    try:

        menu()

    except KeyboardInterrupt:

        print()

        print(
            YELLOW +
            "\n  Programa cancelado." +
            RESET
        )

        print()
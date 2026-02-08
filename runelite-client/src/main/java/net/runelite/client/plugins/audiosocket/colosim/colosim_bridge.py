#!/usr/bin/env python3
"""
Colosim Audio Bridge

Receives sound events from the Colosim Tampermonkey userscript (via HTTP POST)
and re-broadcasts them on TCP port 5150 in the same JSON format as the RuneLite
AudioSocket plugin.

This lets you use the same audio_socket_client.py with both:
  - RuneLite (real game) via the AudioSocket plugin
  - colosim.com (practice) via this bridge + userscript

Usage:
    python colosim_bridge.py [--http-port 5151] [--tcp-port 5150]

Setup:
    1. Install Tampermonkey in your browser
    2. Add colosim_userscript.js as a new userscript
    3. Run this bridge: python colosim_bridge.py
    4. Run the client: python audio_socket_client.py
    5. Open https://colosim.com/ and start a fight
"""

import argparse
import json
import socket
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor


class BridgeState:
    """Shared state between the HTTP server and TCP server."""
    def __init__(self):
        self.tcp_clients = []
        self.lock = threading.Lock()
        self.event_count = 0

    def add_client(self, writer):
        with self.lock:
            self.tcp_clients.append(writer)

    def remove_client(self, writer):
        with self.lock:
            if writer in self.tcp_clients:
                self.tcp_clients.remove(writer)

    def broadcast(self, message):
        with self.lock:
            dead = []
            for sock in self.tcp_clients:
                try:
                    sock.sendall((message + '\n').encode('utf-8'))
                except (BrokenPipeError, ConnectionResetError, OSError):
                    dead.append(sock)
            for sock in dead:
                self.tcp_clients.remove(sock)
                try:
                    sock.close()
                except OSError:
                    pass


state = BridgeState()


class BridgeHTTPHandler(BaseHTTPRequestHandler):
    """Handles POST /sound from the Tampermonkey userscript."""

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # Send CORS + OK response immediately
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

        try:
            event = json.loads(body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        state.event_count += 1

        # Normalize to match RuneLite AudioSocket format
        out = {
            'type': event.get('type', 'AREA_SOUND_EFFECT'),
            'soundId': event.get('soundId', state.event_count),
            'delay': event.get('delay', 0),
            'timestamp': event.get('timestamp', 0),
            'sceneX': event.get('sceneX', 0),
            'sceneY': event.get('sceneY', 0),
            'range': event.get('range', 15),
        }

        # Pass through source info
        if event.get('sourceName'):
            out['sourceName'] = event['sourceName']
        if event.get('sourceAnimation') and event['sourceAnimation'] != -1:
            out['sourceAnimation'] = event['sourceAnimation']

        # Add colosim-specific fields that the client can use
        if event.get('soundFile'):
            out['soundFile'] = event['soundFile']
        if event.get('soundUrl'):
            out['soundUrl'] = event['soundUrl']
        if event.get('attackType'):
            out['attackType'] = event['attackType']
        if event.get('source'):
            out['source'] = event['source']

        json_line = json.dumps(out)

        # Print to bridge console
        attack = event.get('attackType', '')
        filename = event.get('soundFile', 'unknown')
        tag = f"[SOL {attack}]" if attack else "[SOUND]"
        print(f"{tag} #{state.event_count} {filename}")

        # Broadcast to TCP clients
        state.broadcast(json_line)

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress default HTTP logging
        pass


def run_tcp_server(port):
    """TCP server that clients (audio_socket_client.py) connect to."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('127.0.0.1', port))
    server_sock.listen(5)
    print(f"TCP server listening on port {port} (for audio_socket_client.py)")

    while True:
        client_sock, addr = server_sock.accept()
        print(f"Client connected: {addr}")
        state.add_client(client_sock)

        # Monitor for disconnect in a background thread
        def monitor(sock, address):
            try:
                while True:
                    data = sock.recv(1024)
                    if not data:
                        break
            except (ConnectionResetError, OSError):
                pass
            finally:
                state.remove_client(sock)
                print(f"Client disconnected: {address}")
                try:
                    sock.close()
                except OSError:
                    pass

        t = threading.Thread(target=monitor, args=(client_sock, addr), daemon=True)
        t.start()


def main():
    parser = argparse.ArgumentParser(description="Colosim Audio Bridge")
    parser.add_argument('--http-port', type=int, default=5151,
                        help='HTTP port for userscript to POST to (default: 5151)')
    parser.add_argument('--tcp-port', type=int, default=5150,
                        help='TCP port for audio_socket_client.py to connect to (default: 5150)')
    args = parser.parse_args()

    print("=" * 60)
    print("Colosim Audio Bridge")
    print("=" * 60)
    print(f"HTTP server: http://localhost:{args.http_port}/sound")
    print(f"  (userscript sends sound events here)")
    print(f"TCP server:  localhost:{args.tcp_port}")
    print(f"  (audio_socket_client.py connects here)")
    print()
    print("Setup:")
    print("  1. Install colosim_userscript.js in Tampermonkey")
    print("  2. Run: python audio_socket_client.py")
    print("  3. Open https://colosim.com/ and start a fight")
    print("=" * 60)
    print()

    # Start TCP server in background thread
    tcp_thread = threading.Thread(target=run_tcp_server, args=(args.tcp_port,), daemon=True)
    tcp_thread.start()

    # Run HTTP server in main thread
    httpd = HTTPServer(('127.0.0.1', args.http_port), BridgeHTTPHandler)
    print(f"Bridge running. Waiting for sounds from colosim.com...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBridge stopped.")
        httpd.server_close()


if __name__ == '__main__':
    main()

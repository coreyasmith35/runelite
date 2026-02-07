#!/usr/bin/env python3
"""
RuneLite Audio Socket Client

Connects to the AudioSocket RuneLite plugin and receives real-time
sound effect events as JSON.

Usage:
    python audio_socket_client.py [--host HOST] [--port PORT]
"""

import argparse
import json
import socket
import sys


# Well-known sound effect IDs from RuneLite's SoundEffectID.java
SOUND_NAMES = {
    60: "CLOSE_DOOR",
    62: "OPEN_DOOR",
    200: "TELEPORT_VWOOP",
    227: "MAGIC_SPLASH_BOING",
    510: "TAKE_DAMAGE_SPLAT",
    511: "ZERO_DAMAGE_SPLAT",
    2266: "UI_BOOP",
    2498: "ATTACK_HIT",
    2577: "COOK_WOOSH",
    2581: "PICK_PLANT_BLOOP",
    2582: "ITEM_PICKUP",
    2596: "FIRE_WOOSH",
    2597: "TINDER_STRIKE",
    2734: "TREE_FALLING",
    2735: "TREE_CHOP",
    2738: "BURY_BONES",
    2739: "ITEM_DROP",
    3220: "MINING_TINK",
    3790: "SMITH_ANVIL_TINK",
    3791: "SMITH_ANVIL_TONK",
    3813: "TOWN_CRIER_BELL_DING",
    3816: "TOWN_CRIER_SHOUT_SQUEAK",
    3817: "TOWN_CRIER_BELL_DONG",
    3924: "GE_COIN_TINKLE",
    3925: "GE_ADD_OFFER_DINGALING",
    3928: "GE_COLLECT_BLOOP",
    3929: "GE_INCREMENT_PLOP",
    3930: "GE_DECREMENT_PLOP",
}


def on_sound_event(event):
    """
    Called for each sound event received from RuneLite.

    Override or modify this function to handle sound events in your application.

    Args:
        event: dict with keys:
            - type: "SOUND_EFFECT" or "AREA_SOUND_EFFECT"
            - soundId: int, the sound effect ID
            - delay: int, delay before the sound plays
            - timestamp: int, epoch millis when the event fired
            - sourceName: str or None, name of the actor that caused the sound
            For AREA_SOUND_EFFECT:
            - sceneX, sceneY: int, location in the scene
            - range: int, audible range in tiles
    """
    sound_id = event["soundId"]
    sound_name = SOUND_NAMES.get(sound_id, f"UNKNOWN({sound_id})")
    event_type = event["type"]

    if event_type == "AREA_SOUND_EFFECT":
        source = event.get("sourceName", "unknown")
        print(f"[AREA] {sound_name} (id={sound_id}) at ({event['sceneX']},{event['sceneY']}) "
              f"range={event['range']} source={source}")
    else:
        source = event.get("sourceName")
        source_str = f" source={source}" if source else ""
        print(f"[SFX]  {sound_name} (id={sound_id}) delay={event['delay']}{source_str}")


def connect(host="localhost", port=5150):
    """Connect to the RuneLite AudioSocket plugin and stream events."""
    print(f"Connecting to RuneLite AudioSocket at {host}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except ConnectionRefusedError:
        print(f"Connection refused. Make sure RuneLite is running with the "
              f"Audio Socket plugin enabled on port {port}.")
        sys.exit(1)

    print("Connected! Listening for sound events...\n")
    buffer = ""
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                print("Server disconnected.")
                break
            buffer += data.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line:
                    try:
                        event = json.loads(line)
                        on_sound_event(event)
                    except json.JSONDecodeError as e:
                        print(f"Invalid JSON: {e}")
    except KeyboardInterrupt:
        print("\nDisconnected.")
    finally:
        sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RuneLite Audio Socket Client")
    parser.add_argument("--host", default="localhost", help="Host to connect to (default: localhost)")
    parser.add_argument("--port", type=int, default=5150, help="Port to connect to (default: 5150)")
    args = parser.parse_args()
    connect(args.host, args.port)

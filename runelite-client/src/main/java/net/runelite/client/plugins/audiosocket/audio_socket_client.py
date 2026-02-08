#!/usr/bin/env python3
"""
RuneLite Audio Socket Client

Connects to the AudioSocket RuneLite plugin and receives real-time
sound effect events as JSON.

Usage:
    python audio_socket_client.py [--host HOST] [--port PORT]
    python audio_socket_client.py --discover        # Log all unique sound IDs
"""

import argparse
import json
import socket
import sys
from collections import defaultdict


# Well-known sound effect IDs from RuneLite's SoundEffectID.java
SOUND_NAMES = {
    60: "CLOSE_DOOR",
    62: "OPEN_DOOR",
    200: "TELEPORT_VWOOP",
    227: "MAGIC_SPLASH_BOING",
    510: "TAKE_DAMAGE_SPLAT",
    511: "ZERO_DAMAGE_SPLAT",
    1930: "NPC_TELEPORT_WOOSH",
    2266: "UI_BOOP",
    2498: "ATTACK_HIT",
    2577: "COOK_WOOSH",
    2581: "PICK_PLANT_BLOOP",
    2582: "ITEM_PICKUP",
    2596: "FIRE_WOOSH",
    2597: "TINDER_STRIKE",
    2663: "PRAYER_DEACTIVATE_VWOOP",
    2664: "PRAYER_ACTIVATE_CLARITY_OF_THOUGHT",
    2675: "PRAYER_ACTIVATE_PROTECT_FROM_MAGIC",
    2676: "PRAYER_ACTIVATE_PROTECT_FROM_MELEE",
    2677: "PRAYER_ACTIVATE_PROTECT_FROM_MISSILES",
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

# Sol Heredit (Fortis Colosseum final boss) animation IDs from RuneLite's AnimationID.java.
# Sol Heredit's attack sounds are AREA SOUND EFFECTS. The source actor name will be
# "Sol Heredit" and sourceAnimation will be one of these IDs.
#
# To discover Sol Heredit sound IDs:
#   1. Run this script with --discover during a Sol Heredit fight
#   2. Note which sound IDs fire alongside each animation ID
#   3. Add those sound IDs to SOL_HEREDIT_SOUNDS below
SOL_HEREDIT_ANIMATIONS = {
    10874: "SOL_HEREDIT_IDLE",
    10875: "SOL_HEREDIT_SITTING_IDLE",
    10876: "SOL_HEREDIT_ARENA_JUMP",
    10877: "SOL_HEREDIT_ARENA_LAND",
    10878: "SOL_HEREDIT_WALK",
    10882: "SOL_HEREDIT_SPEAR_ATTACK",           # Melee/spear attack
    10883: "SOL_HEREDIT_SPEAR_ATTACK_TELEGRAPH",  # Spear telegraph (react to this!)
    10884: "SOL_HEREDIT_GRAPPLE_TELEGRAPH",       # Grapple attack telegraph (<75% HP)
    10885: "SOL_HEREDIT_SHIELD_SLAM_TELEGRAPH",   # Shield slam telegraph (react to this!)
    10886: "SOL_HEREDIT_TRIPLE_ATTACK",           # Triple parry attack (<90% HP)
    10887: "SOL_HEREDIT_TRIPLE_ATTACK_FAST",      # Triple parry (faster, <50% HP)
    10888: "SOL_HEREDIT_DEATH",
}

# Sol Heredit sound effect IDs.
# These need to be discovered in-game using --discover mode or RuneLite DevTools.
# Once found, add them here as: sound_id: "description"
#
# Sol's attacks are area sounds. During the fight, you should see area sound events
# from source "Sol Heredit" with sourceAnimation matching the animation IDs above.
# The sound IDs that fire with animation 10883 are spear sounds, and 10885 are shield sounds.
SOL_HEREDIT_SOUNDS = {
    # To discover: run with --discover during a Sol Heredit fight, then fill in:
    # <sound_id>: "SOL_HEREDIT_SPEAR_ATTACK",
    # <sound_id>: "SOL_HEREDIT_SHIELD_SLAM",
    # <sound_id>: "SOL_HEREDIT_GRAPPLE",
    # <sound_id>: "SOL_HEREDIT_TRIPLE_ATTACK",
    # <sound_id>: "SOL_HEREDIT_ARENA_LAND",
    # <sound_id>: "SOL_HEREDIT_DEATH",
}

# Merge Sol Heredit sounds into main lookup
SOUND_NAMES.update(SOL_HEREDIT_SOUNDS)

# Colosseum-related NPC IDs (for reference)
SOL_HEREDIT_NPC_IDS = {
    12821: "SOL_HEREDIT_P1",
    12827: "SOL_HEREDIT_SEATED",
    15554: "SOL_HEREDIT_DEADMAN",
}


def on_sound_event(event):
    """
    Called for each sound event received from RuneLite.

    Args:
        event: dict with keys:
            - type: "SOUND_EFFECT" or "AREA_SOUND_EFFECT"
            - soundId: int, the sound effect ID
            - delay: int, delay before the sound plays
            - timestamp: int, epoch millis when the event fired
            - sourceName: str or None, name of the actor that caused the sound
            - sourceAnimation: int or None, current animation ID of the source actor
            For AREA_SOUND_EFFECT:
            - sceneX, sceneY: int, location in the scene
            - range: int, audible range in tiles
    """
    sound_id = event["soundId"]
    sound_name = SOUND_NAMES.get(sound_id, f"UNKNOWN({sound_id})")
    event_type = event["type"]

    if event_type == "AREA_SOUND_EFFECT":
        source = event.get("sourceName", "unknown")
        anim = event.get("sourceAnimation", -1)
        anim_name = SOL_HEREDIT_ANIMATIONS.get(anim, "")
        anim_str = f" anim={anim}" if anim and anim != -1 else ""
        if anim_name:
            anim_str = f" anim={anim_name}({anim})"
        print(f"[AREA] {sound_name} (id={sound_id}) at ({event['sceneX']},{event['sceneY']}) "
              f"range={event['range']} source={source}{anim_str}")
    else:
        source = event.get("sourceName")
        anim = event.get("sourceAnimation", -1)
        source_str = f" source={source}" if source else ""
        anim_str = f" anim={anim}" if anim and anim != -1 else ""
        print(f"[SFX]  {sound_name} (id={sound_id}) delay={event['delay']}{source_str}{anim_str}")


# Track unique sound IDs seen during discovery mode
_discovered = defaultdict(lambda: {"count": 0, "sources": set(), "animations": set()})


def on_discover_event(event):
    """Discovery mode: track all unique sound IDs and their sources/animations."""
    sound_id = event["soundId"]
    source = event.get("sourceName", "")
    anim = event.get("sourceAnimation", -1)
    event_type = event["type"]

    entry = _discovered[sound_id]
    entry["count"] += 1
    entry["type"] = event_type
    if source:
        entry["sources"].add(source)
    if anim and anim != -1:
        entry["animations"].add(anim)

    # Print live updates
    anim_name = SOL_HEREDIT_ANIMATIONS.get(anim, "")
    known_name = SOUND_NAMES.get(sound_id, "")
    label = known_name or f"sound {sound_id}"
    prefix = "[AREA]" if event_type == "AREA_SOUND_EFFECT" else "[SFX] "
    anim_str = f" anim={anim_name}({anim})" if anim_name else (f" anim={anim}" if anim and anim != -1 else "")
    print(f"{prefix} {label} (id={sound_id}) source={source or 'none'}{anim_str} [seen {entry['count']}x]")


def print_discovery_summary():
    """Print a summary of all discovered sound IDs."""
    print("\n" + "=" * 70)
    print("DISCOVERY SUMMARY - All unique sound IDs observed:")
    print("=" * 70)

    sol_sounds = []
    other_sounds = []

    for sound_id, info in sorted(_discovered.items()):
        known = SOUND_NAMES.get(sound_id, "UNKNOWN")
        sources = ", ".join(info["sources"]) if info["sources"] else "none"
        anims = ", ".join(
            f"{SOL_HEREDIT_ANIMATIONS.get(a, '')}({a})" if a in SOL_HEREDIT_ANIMATIONS else str(a)
            for a in sorted(info["animations"])
        ) if info["animations"] else "none"

        line = f"  {sound_id:>6}: {known:<30} count={info['count']:<5} type={info['type']:<20} sources=[{sources}] anims=[{anims}]"

        if "Sol Heredit" in (info.get("sources") or set()):
            sol_sounds.append(line)
        else:
            other_sounds.append(line)

    if sol_sounds:
        print("\n--- Sol Heredit sounds ---")
        for line in sol_sounds:
            print(line)
        print("\nPaste these into SOL_HEREDIT_SOUNDS in this script:")
        print("SOL_HEREDIT_SOUNDS = {")
        for sound_id, info in sorted(_discovered.items()):
            if "Sol Heredit" in (info.get("sources") or set()):
                anims = sorted(info["animations"])
                anim_label = SOL_HEREDIT_ANIMATIONS.get(anims[0], f"anim_{anims[0]}") if anims else "UNKNOWN"
                print(f'    {sound_id}: "{anim_label}",')
        print("}")

    if other_sounds:
        print("\n--- Other sounds ---")
        for line in other_sounds:
            print(line)

    print("=" * 70)


def connect(host="localhost", port=5150, discover=False):
    """Connect to the RuneLite AudioSocket plugin and stream events."""
    handler = on_discover_event if discover else on_sound_event

    if discover:
        print("DISCOVERY MODE: All unique sound IDs will be tracked.")
        print("Fight Sol Heredit, then press Ctrl+C to see the summary.\n")

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
                        handler(event)
                    except json.JSONDecodeError as e:
                        print(f"Invalid JSON: {e}")
    except KeyboardInterrupt:
        if discover:
            print_discovery_summary()
        else:
            print("\nDisconnected.")
    finally:
        sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RuneLite Audio Socket Client")
    parser.add_argument("--host", default="localhost", help="Host to connect to (default: localhost)")
    parser.add_argument("--port", type=int, default=5150, help="Port to connect to (default: 5150)")
    parser.add_argument("--discover", action="store_true",
                        help="Discovery mode: track all unique sound IDs and print summary on exit")
    args = parser.parse_args()
    connect(args.host, args.port, args.discover)

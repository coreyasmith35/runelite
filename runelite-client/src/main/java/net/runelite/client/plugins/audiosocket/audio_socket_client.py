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

# Sol Heredit sound effect IDs from the OSRS Wiki List of sound IDs (8047-8337).
# All are area sound effects. Categorized by attack type for easy filtering.
# Source: https://oldschool.runescape.wiki/w/List_of_sound_IDs

# --- Spear / Melee Attack Telegraph ---
SOL_HEREDIT_SPEAR_SOUNDS = {
    8047: "SOL_SPEAR_TELEGRAPH_STAB_08",
    8051: "SOL_SPEAR_TELEGRAPH_FOOTSTEP_09",
    8055: "SOL_SPEAR_TELEGRAPH_DISLODGE_02",
    8056: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_05",
    8057: "SOL_SPEAR_TELEGRAPH_STAB_IMPACT_05",
    8058: "SOL_SPEAR_TELEGRAPH_STAB_IMPACT_02",
    8073: "SOL_SPEAR_TELEGRAPH_CHARGE_13",
    8078: "SOL_SPEAR_TELEGRAPH_CHARGE_05",
    8079: "SOL_SPEAR_TELEGRAPH_FOOTSTEP_08",
    8086: "SOL_SPEAR_TELEGRAPH_CHARGE_03",
    8087: "SOL_SPEAR_TELEGRAPH_STAB_01",
    8088: "SOL_SPEAR_TELEGRAPH_LUNGE_03",
    8092: "SOL_SPEAR_TELEGRAPH_STAB_02",
    8096: "SOL_SPEAR_TELEGRAPH_DISLODGE_01",
    8097: "SOL_SPEAR_TELEGRAPH_BASS_02",
    8099: "SOL_SPEAR_TELEGRAPH_CHARGE_01",
    8102: "SOL_SPEAR_TELEGRAPH_CHARGE_06",
    8103: "SOL_SPEAR_TELEGRAPH_BASS_01",
    8109: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_03",
    8120: "SOL_SPEAR_TELEGRAPH_CHARGE_02",
    8121: "SOL_SPEAR_TELEGRAPH_STAB_IMPACT_01",
    8123: "SOL_SPEAR_TELEGRAPH_STAB_03",
    8127: "SOL_SPEAR_TELEGRAPH_LUNGE_01",
    8131: "SOL_SPEAR_TELEGRAPH_DISLODGE_06",
    8135: "SOL_SPEAR_TELEGRAPH_FOOTSTEP_03",
    8137: "SOL_SPEAR_TELEGRAPH_BACK_FOOTSTEP_01",
    8139: "SOL_SPEAR_TELEGRAPH_BASS_STEP_01",
    8147: "SOL_SPEAR_TELEGRAPH_CHARGE_16",
    8153: "SOL_SPEAR_TELEGRAPH_CHARGE_08",
    8155: "SOL_SPEAR_TELEGRAPH_STAB_IMPACT_03",
    8160: "SOL_SPEAR_TELEGRAPH_FOOTSTEP_02",
    8162: "SOL_SPEAR_TELEGRAPH_STAB_IMPACT_04",
    8163: "SOL_SPEAR_TELEGRAPH_CHARGE_15",
    8165: "SOL_SPEAR_TELEGRAPH_BACK_FOOTSTEP_02",
    8168: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_02",
    8169: "SOL_SPEAR_TELEGRAPH_FOOTSTEP_06",
    8170: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_14",
    8195: "SOL_SPEAR_TELEGRAPH_FOOTSTEP_01",
    8206: "SOL_SPEAR_TELEGRAPH_BASS_03",
    8207: "SOL_SPEAR_TELEGRAPH_CHARGE_04",
    8208: "SOL_SPEAR_TELEGRAPH_FOOTSTEP_07",
    8215: "SOL_SPEAR_TELEGRAPH_FOOTSTEP_04",
    8221: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_07",
    8222: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_06",
    8224: "SOL_SPEAR_TELEGRAPH_STAB_METAL_02",
    8232: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_01",
    8238: "SOL_SPEAR_TELEGRAPH_CHARGE_07",
    8240: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_10",
    8264: "SOL_SPEAR_TELEGRAPH_DISLODGE_04",
    8267: "SOL_SPEAR_TELEGRAPH_CHARGE_12",
    8272: "SOL_SPEAR_TELEGRAPH_DISLODGE_03",
    8285: "SOL_SPEAR_TELEGRAPH_CHARGE_10",
    8288: "SOL_SPEAR_TELEGRAPH_STAB_METAL_01",
    8291: "SOL_SPEAR_TELEGRAPH_LUNGE_04",
    8294: "SOL_SPEAR_TELEGRAPH_CHARGE_09",
    8302: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_09",
    8303: "SOL_SPEAR_TELEGRAPH_CHARGE_14",
    8308: "SOL_SPEAR_TELEGRAPH_STAB_IMPACT_06",
    8315: "SOL_SPEAR_TELEGRAPH_DISLODGE_05",
    8319: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_11",
    8320: "SOL_SPEAR_TELEGRAPH_STAB_04",
    8325: "SOL_SPEAR_TELEGRAPH_LUNGE_02",
    8328: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_08",
    8331: "SOL_SPEAR_TELEGRAPH_LUNGE_05",
    8333: "SOL_SPEAR_TELEGRAPH_TRIDENT_END_MOVE_04",
    8335: "SOL_SPEAR_TELEGRAPH_CHARGE_11",
    8336: "SOL_SPEAR_TELEGRAPH_FOOTSTEP_05",
}

# --- Shield Slam ---
SOL_HEREDIT_SHIELD_SOUNDS = {
    8054: "SOL_SHIELD_ARM_PREP_03",
    8063: "SOL_SHIELD_DROP_IMPACT_02",
    8148: "SOL_SHIELD_SLAM_CHARGE_05",
    8150: "SOL_SHIELD_SLAM_CHARGE_06",
    8154: "SOL_SHIELD_SLAM_CHARGE_01",
    8174: "SOL_SHIELD_DROP_IMPACT_01",
    8145: "SOL_SHIELD_DROP_IMPACT_03",
    8189: "SOL_SHIELD_SLAM_CHARGE_03",
    8233: "SOL_SHIELD_SLAM_CHARGE_04",
    8260: "SOL_SHIELD_SLAM_02",
    8282: "SOL_SHIELD_SLAM_01",
    8310: "SOL_SHIELD_ARM_PREP_02",
    8318: "SOL_SHIELD_SLAM_CHARGE_02",
    8322: "SOL_SHIELD_ARM_PREP_04",
    8326: "SOL_SHIELD_ARM_PREP_01",
}

# --- Grapple Attack ---
SOL_HEREDIT_GRAPPLE_SOUNDS = {
    8052: "SOL_GRAPPLE_ARM_LUNGE_02",
    8065: "SOL_GRAPPLE_ARM_IMPACT_STEP_01",
    8066: "SOL_GRAPPLE_ARM_LUNGE_03",
    8075: "SOL_GRAPPLE_FIRST_SHIELD_DROP_01",
    8081: "SOL_GRAPPLE_ARM_RETURN_BASS_02",
    8084: "SOL_GRAPPLE_ARM_FOOTSTEP_04",
    8094: "SOL_GRAPPLE_ARM_SHIELD_FLOOR_IMPACT_03",
    8114: "SOL_GRAPPLE_ARM_RETURN_BASS_01",
    8129: "SOL_GRAPPLE_ARM_SHIELD_FLOOR_IMPACT_05",
    8146: "SOL_GRAPPLE_ARM_LUNGE_01",
    8156: "SOL_GRAPPLE_ARM_FOOTSTEP_02",
    8159: "SOL_GRAPPLE_ARM_FOOTSTEP_0",
    8186: "SOL_GRAPPLE_ARM_SHIELD_FLOOR_IMPACT_06",
    8194: "SOL_GRAPPLE_ARM_FOOTSTEP_03",
    8219: "SOL_GRAPPLE_ARM_SHIELD_FLOOR_IMPACT_01",
    8226: "SOL_GRAPPLE_ARM_SHIELD_FLOOR_IMPACT_02",
    8241: "SOL_GRAPPLE_ARM_BASS_01",
    8257: "SOL_GRAPPLE_ARM_FOOTSTEP_01",
    8266: "SOL_GRAPPLE_ARM_BASS_02",
    8269: "SOL_GRAPPLE_ARM_SHIELD_FLOOR_IMPACT_04",
    8277: "SOL_GRAPPLE_ARM_FOOTSTEP_06",
    8278: "SOL_GRAPPLE_ARM_RETURN_01",
    8290: "SOL_GRAPPLE_SHIELD_DROP_01",
    8298: "SOL_GRAPPLE_ARM_FOOTSTEP_07",
    8329: "SOL_GRAPPLE_CHARGE_01",
}

# --- Triple Attack ---
SOL_HEREDIT_TRIPLE_SOUNDS = {
    8060: "SOL_TRIPLE_FIRST_RUMBLE_02",
    8072: "SOL_TRIPLE_FINAL_STAB_WHOOSH_01",
    8074: "SOL_TRIPLE_SHORTER_IMPACT_03",
    8076: "SOL_TRIPLE_FIRST_RUMBLE_01",
    8077: "SOL_TRIPLE_FINAL_DISLODGE_01",
    8082: "SOL_TRIPLE_TRIDENT_STAB_02",
    8083: "SOL_TRIPLE_CHARGE_05",
    8091: "SOL_TRIPLE_SHORTER_METAL_IMPACT_01",
    8112: "SOL_TRIPLE_CHARGE_04",
    8113: "SOL_TRIPLE_MID_CHARGE_01",
    8116: "SOL_TRIPLE_FIRST_IMPACT_01",
    8124: "SOL_TRIPLE_END_WHOOSH_01",
    8125: "SOL_TRIPLE_END_RUMBLE_01",
    8134: "SOL_TRIPLE_TRIDENT_2ND_WHOOSH_02",
    8140: "SOL_TRIPLE_SHORTER_IMPACT_02",
    8141: "SOL_TRIPLE_FINAL_DISLODGE_05",
    8158: "SOL_TRIPLE_SHORTER_BASS_RIPPLES_01",
    8166: "SOL_TRIPLE_END_WHOOSH_02",
    8171: "SOL_TRIPLE_SHORTER_END_IMPACT_01",
    8173: "SOL_TRIPLE_FINAL_DISLODGE_04",
    8178: "SOL_TRIPLE_CHARGE_07",
    8181: "SOL_TRIPLE_TRIDENT_STAB_01",
    8182: "SOL_TRIPLE_FINAL_DISLODGE_06",
    8183: "SOL_TRIPLE_SHORTER_END_RUMBLE_02",
    8187: "SOL_TRIPLE_INTRO_01",
    8188: "SOL_TRIPLE_SHORTER_END_RUMBLE_01",
    8190: "SOL_TRIPLE_TRIDENT_STAB_03",
    8191: "SOL_TRIPLE_LONG_END_IMPACT_02",
    8196: "SOL_TRIPLE_FINAL_DISLODGE_02",
    8197: "SOL_TRIPLE_METAL_INTRO_03",
    8198: "SOL_TRIPLE_FIRST_WHOOSH_02",
    8210: "SOL_TRIPLE_FINAL_DISLODGE_03",
    8211: "SOL_TRIPLE_METAL_INTRO_01",
    8217: "SOL_TRIPLE_CHARGE_03",
    8218: "SOL_TRIPLE_MID_CHARGE_02",
    8229: "SOL_TRIPLE_FINAL_STAB_WHOOSH_05",
    8242: "SOL_TRIPLE_METALLIC_ENDING_STAB_01",
    8251: "SOL_TRIPLE_CHARGE_01",
    8261: "SOL_TRIPLE_TRIDENT_2ND_WHOOSH_01",
    8265: "SOL_TRIPLE_CHARGE_02",
    8270: "SOL_TRIPLE_LONG_END_IMPACT_01",
    8274: "SOL_TRIPLE_SMALL_CHARGE_01",
    8275: "SOL_TRIPLE_TRIDENT_2ND_WHOOSH_03",
    8283: "SOL_TRIPLE_FOOTSTEP_01",
    8287: "SOL_TRIPLE_FIRST_WHOOSH_01",
    8293: "SOL_TRIPLE_SHORTER_END_RUMBLE_03",
    8305: "SOL_TRIPLE_TRIDENT_WHOOSH_03",
    8307: "SOL_TRIPLE_SHORTER_IMPACT_01",
    8311: "SOL_TRIPLE_INTRO_02",
    8312: "SOL_TRIPLE_METAL_INTRO_02",
    8314: "SOL_TRIPLE_FINAL_STAB_01",
    8317: "SOL_TRIPLE_CHARGE_06",
    8321: "SOL_TRIPLE_TRIDENT_WHOOSH_02",
    8327: "SOL_TRIPLE_FOOTSTEP_02",
    8330: "SOL_TRIPLE_TRIDENT_WHOOSH_01",
    8334: "SOL_TRIPLE_FINAL_STAB_WHOOSH_04",
}

# --- Death ---
SOL_HEREDIT_DEATH_SOUNDS = {
    8048: "SOL_DEATH_METALLIC_IMPACT_10",
    8068: "SOL_DEATH_FIRST_SHIELD_DROP_02",
    8069: "SOL_DEATH_SECOND_FALL_02",
    8090: "SOL_DEATH_SECOND_FALL_01",
    8098: "SOL_DEATH_METALLIC_IMPACT_03",
    8105: "SOL_DEATH_FIRST_FALL_03",
    8115: "SOL_DEATH_RINGING_02",
    8119: "SOL_DEATH_METALLIC_IMPACT_09",
    8122: "SOL_DEATH_METALLIC_IMPACT_02",
    8126: "SOL_DEATH_SECOND_FALL_03",
    8130: "SOL_DEATH_METALLIC_IMPACT_08",
    8132: "SOL_DEATH_METALLIC_IMPACT_04",
    8133: "SOL_DEATH_WHOOSH_01",
    8138: "SOL_DEATH_METALLIC_IMPACT_06",
    8175: "SOL_DEATH_METALLIC_IMPACT_05",
    8177: "SOL_DEATH_METALLIC_IMPACT_07",
    8212: "SOL_DEATH_METALLIC_IMPACT_01",
    8214: "SOL_DEATH_FIRST_FALL_02",
    8243: "SOL_DEATH_SECOND_FALL_05",
    8244: "SOL_DEATH_SECOND_FALL_06",
    8255: "SOL_DEATH_FIRST_SHIELD_DROP_01",
    8263: "SOL_DEATH_RINGING_01",
    8280: "SOL_DEATH_SECOND_FALL_04",
    8284: "SOL_DEATH_LAND_RUMBLE_01",
    8300: "SOL_DEATH_FIRST_SHIELD_DROP_03",
    8316: "SOL_DEATH_WHOOSH_02",
    8323: "SOL_DEATH_FIRST_FALL_01",
    8324: "SOL_DEATH_FIRST_SHIELD_DROP_04",
    8337: "SOL_DEATH_FIRST_WHOOSH_01",
    8157: "SOL_DEATH_WHOOSH_03",
}

# --- Arena (Jump / Land) ---
SOL_HEREDIT_ARENA_SOUNDS = {
    8049: "SOL_ARENA_JUMP_METAL_02",
    8064: "SOL_ARENA_LAND_RUMBLE_01",
    8067: "SOL_ARENA_JUMP_HIGH_WIND_03",
    8071: "SOL_ARENA_LAND_METAL_IMPACT2_02",
    8080: "SOL_ARENA_JUMP_HIGH_WIND_01",
    8089: "SOL_ARENA_GROUND_RUMBLE_01",
    8101: "SOL_ARENA_JUMP_TAKE_OFF_02",
    8106: "SOL_ARENA_LAND_METAL_IMPACT_01",
    8128: "SOL_ARENA_JUMP_SPEED_WIND_01",
    8142: "SOL_ARENA_JUMP_BASS_01",
    8149: "SOL_ARENA_LAND_METAL_IMPACT2_01",
    8161: "SOL_ARENA_JUMP_LOW_WIND_03",
    8167: "SOL_ARENA_LAND_METAL_IMPACT_02",
    8172: "SOL_ARENA_JUMP_LOW_WIND_05",
    8176: "SOL_ARENA_JUMP_HIGH_WIND_04",
    8185: "SOL_ARENA_JUMP_LOW_WIND_04",
    8192: "SOL_ARENA_JUMP_TAKE_OFF_01",
    8200: "SOL_ARENA_JUMP_LOW_WIND_01",
    8202: "SOL_ARENA_JUMP_HIGH_WIND_02",
    8203: "SOL_ARENA_LAND_METAL_IMPACT2_03",
    8237: "SOL_ARENA_JUMP_WHOOSH_01",
    8254: "SOL_ARENA_DELAYED_TAKE_OFF_01",
    8256: "SOL_ARENA_LAND_IMPACT_01",
    8258: "SOL_ARENA_GROUND_RUMBLE_02",
    8262: "SOL_ARENA_LAND_IMPACT_02",
    8276: "SOL_ARENA_JUMP_SPEED_WIND_02",
    8279: "SOL_ARENA_GROUND_RUMBLE_04",
    8281: "SOL_ARENA_GROUND_RUMBLE_03",
    8289: "SOL_ARENA_GROUND_RUMBLE_05",
    8295: "SOL_ARENA_JUMP_LOW_WIND_02",
    8297: "SOL_ARENA_JUMP_METAL_01",
}

# --- Boss Ambient (Footsteps / Hiss / Misc) ---
SOL_HEREDIT_AMBIENT_SOUNDS = {
    8085: "SOL_HISS_02",
    8107: "SOL_FOOTSTEPS_03",
    8117: "SOL_SHORT_HISS_02",
    8118: "SOL_FOOTSTEPS_02",
    8143: "SOL_FOOTSTEPS_06",
    8180: "SOL_HISS_03",
    8184: "SOL_SHORT_HISS_01",
    8204: "SOL_FOOTSTEPS_05",
    8216: "SOL_FOOTSTEPS_07",
    8220: "SOL_HISS_03B",
    8234: "SOL_FOOTSTEPS_01",
    8248: "SOL_FOOTSTEPS_08",
    8271: "SOL_HISS_01",
    8286: "SOL_SHORT_HISS_04",
    8304: "SOL_HISS_04",
    8332: "SOL_FOOTSTEPS_04",
    8061: "SOL_TRIDENT_RELEASE_01",
    8095: "SOL_BACK_BREAK_02",
    8225: "SOL_BACK_BREAK_01",
}

# --- Crystal Beam / Totem / Colosseum Environment ---
SOL_HEREDIT_ENVIRONMENT_SOUNDS = {
    8050: "SOL_TOTEM_FIRST_BEAM_09",
    8053: "SOL_CRYSTAL_BEAM_CIRCLE_SPAWN_05",
    8059: "SOL_CRYSTAL_BEAM_TOP_PROJ_01",
    8062: "SOL_BOSS_CLAP_ATTACK_01",
    8070: "SOL_CRYSTAL_BEAM_CRYSTAL_SPAWN_01",
    8093: "SOL_CRYSTAL_BEAM_TOP_PROJ_11",
    8104: "SOL_CRYSTAL_BEAM_CIRCLE_SPAWN_03",
    8108: "SOL_TOTEM_FIRST_BEAM_05",
    8110: "SOL_CRYSTAL_BEAM_SPAWN_01",
    8111: "SOL_CRYSTAL_BEAM_TOP_PROJ_03",
    8136: "SOL_TOTEM_LINE_FUSE_HISS_EXPLOSION_06",
    8144: "SOL_CRYSTAL_BEAM_TOP_PROJ_04",
    8151: "SOL_TOTEM_FIRST_BEAM_07",
    8152: "SOL_TOTEM_LINE_FUSE_HISS_02",
    8164: "SOL_CRYSTAL_PROJ_SPAWN_01",
    8179: "SOL_CRYSTAL_BEAM_CIRCLE_SPAWN_01",
    8193: "SOL_CRYSTAL_BEAM_TOP_PROJ_06",
    8199: "SOL_CRYSTAL_BEAM_TOP_PROJ_09",
    8201: "SOL_CRYSTAL_BEAM_TOP_PROJ_10",
    8205: "SOL_CRYSTAL_BEAM_CIRCLE_SPAWN_04",
    8209: "SOL_CRYSTAL_BEAM_TOP_PROJ_05",
    8213: "SOL_TOTEM_LINE_FUSE_HISS_EXPLOSION_07",
    8227: "SOL_CRYSTAL_BEAM_TOP_PROJ_07",
    8228: "SOL_CRYSTAL_BEAM_TOP_PROJ_08",
    8230: "SOL_TOTEM_BEAM_EXPLOSION_01",
    8231: "SOL_TOTEM_FIRST_BEAM_06",
    8235: "SOL_TOTEM_FIRST_BEAM_02",
    8236: "SOL_CRYSTAL_BEAM_TOP_PROJ_02",
    8239: "SOL_CRYSTAL_PROJ_SPAWN_02",
    8246: "SOL_CRYSTAL_PROJ_SPAWN_BASS_01",
    8247: "SOL_TOTEM_FIRST_BEAM_03",
    8249: "SOL_TOTEM_LINE_FUSE_HISS_01",
    8253: "SOL_TOTEM_FIRST_BEAM_10",
    8259: "SOL_TOTEM_FIRST_BEAM_01",
    8268: "SOL_TOTEM_LINE_FUSE_HISS_EXPLOSION_01",
    8292: "SOL_CRYSTAL_BEAM_CIRCLE_SPAWN_02",
    8299: "SOL_TOTEM_FIRST_BEAM_04",
    8301: "SOL_TOTEM_FIRST_BEAM_08",
    8306: "SOL_TOTEM_LINE_FUSE_HISS_EXPLOSION_05",
    8313: "SOL_TOTEM_LINE_FUSE_HISS_EXPLOSION_04",  # Note: wiki has typo _04 vs _05
}

# --- Explosions / Generic (shared with other content) ---
SOL_HEREDIT_EXPLOSION_SOUNDS = {
    8100: "EXPLOSION_05",
    8223: "EXPLOSION_04",
    8245: "EXPLOSION_07",
    8250: "METALIC_IMPACT_01",
    8252: "EXPLOSION_01",
    8273: "EXPLOSION_03",
    8296: "EXPLOSION_06",
    8309: "EXPLOSION_02",
}

# Combined dict of ALL Sol Heredit / Colosseum boss sounds (8047-8337)
SOL_HEREDIT_SOUNDS = {}
SOL_HEREDIT_SOUNDS.update(SOL_HEREDIT_SPEAR_SOUNDS)
SOL_HEREDIT_SOUNDS.update(SOL_HEREDIT_SHIELD_SOUNDS)
SOL_HEREDIT_SOUNDS.update(SOL_HEREDIT_GRAPPLE_SOUNDS)
SOL_HEREDIT_SOUNDS.update(SOL_HEREDIT_TRIPLE_SOUNDS)
SOL_HEREDIT_SOUNDS.update(SOL_HEREDIT_DEATH_SOUNDS)
SOL_HEREDIT_SOUNDS.update(SOL_HEREDIT_ARENA_SOUNDS)
SOL_HEREDIT_SOUNDS.update(SOL_HEREDIT_AMBIENT_SOUNDS)
SOL_HEREDIT_SOUNDS.update(SOL_HEREDIT_ENVIRONMENT_SOUNDS)
SOL_HEREDIT_SOUNDS.update(SOL_HEREDIT_EXPLOSION_SOUNDS)

# Convenience sets for quick attack-type filtering
SOL_SPEAR_IDS = frozenset(SOL_HEREDIT_SPEAR_SOUNDS.keys())
SOL_SHIELD_IDS = frozenset(SOL_HEREDIT_SHIELD_SOUNDS.keys())
SOL_GRAPPLE_IDS = frozenset(SOL_HEREDIT_GRAPPLE_SOUNDS.keys())
SOL_TRIPLE_IDS = frozenset(SOL_HEREDIT_TRIPLE_SOUNDS.keys())
SOL_DEATH_IDS = frozenset(SOL_HEREDIT_DEATH_SOUNDS.keys())

# Merge Sol Heredit sounds into main lookup
SOUND_NAMES.update(SOL_HEREDIT_SOUNDS)

# Colosseum-related NPC IDs (for reference)
SOL_HEREDIT_NPC_IDS = {
    12821: "SOL_HEREDIT_P1",
    12827: "SOL_HEREDIT_SEATED",
    15554: "SOL_HEREDIT_DEADMAN",
}


def get_sol_attack_type(sound_id):
    """Return the Sol Heredit attack type for a sound ID, or None."""
    if sound_id in SOL_SPEAR_IDS:
        return "SPEAR"
    if sound_id in SOL_SHIELD_IDS:
        return "SHIELD"
    if sound_id in SOL_GRAPPLE_IDS:
        return "GRAPPLE"
    if sound_id in SOL_TRIPLE_IDS:
        return "TRIPLE"
    if sound_id in SOL_DEATH_IDS:
        return "DEATH"
    return None


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

        # Tag Sol Heredit attack type
        attack_type = get_sol_attack_type(sound_id)
        tag = f"[SOL {attack_type}]" if attack_type else "[AREA]"

        print(f"{tag} {sound_name} (id={sound_id}) at ({event['sceneX']},{event['sceneY']}) "
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

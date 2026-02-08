// ==UserScript==
// @name         Colosim Audio Bridge
// @namespace    https://colosim.com/
// @version      1.0
// @description  Intercepts sounds played on colosim.com and sends them to a local bridge server
// @match        https://colosim.com/*
// @match        http://colosim.com/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      127.0.0.1
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    const BRIDGE_URL = 'http://localhost:5151/sound';
    let soundCounter = 0;

    function sendToBridge(data) {
        // Use GM_xmlhttpRequest to bypass CORS restrictions
        if (typeof GM_xmlhttpRequest !== 'undefined') {
            GM_xmlhttpRequest({
                method: 'POST',
                url: BRIDGE_URL,
                headers: { 'Content-Type': 'application/json' },
                data: JSON.stringify(data),
                onerror: function () { /* bridge not running, ignore */ }
            });
        } else {
            // Fallback to fetch (may fail due to CORS if bridge doesn't send headers)
            fetch(BRIDGE_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
                mode: 'cors'
            }).catch(function () { /* bridge not running, ignore */ });
        }
    }

    function extractSoundInfo(src) {
        if (!src) return { url: '', filename: '' };
        const url = String(src);
        const parts = url.split('/');
        const filename = parts[parts.length - 1].split('?')[0].split('#')[0];
        return { url: url, filename: filename };
    }

    function classifySound(filename) {
        const lower = filename.toLowerCase();
        // Try to classify based on filename patterns
        if (lower.includes('spear') || lower.includes('stab') || lower.includes('lunge') || lower.includes('trident')) {
            return 'SPEAR';
        }
        if (lower.includes('shield') && (lower.includes('slam') || lower.includes('charge') || lower.includes('prep'))) {
            return 'SHIELD';
        }
        if (lower.includes('grapple')) {
            return 'GRAPPLE';
        }
        if (lower.includes('triple') || lower.includes('parry')) {
            return 'TRIPLE';
        }
        if (lower.includes('death')) {
            return 'DEATH';
        }
        if (lower.includes('arena') || lower.includes('jump') || lower.includes('land')) {
            return 'ARENA';
        }
        return null;
    }

    // --- Hook HTMLAudioElement ---
    const OriginalAudio = window.Audio;
    const origPlay = HTMLAudioElement.prototype.play;

    HTMLAudioElement.prototype.play = function () {
        const info = extractSoundInfo(this.src || this.currentSrc);
        const attackType = classifySound(info.filename);
        soundCounter++;

        console.log('[ColosimBridge] Audio.play:', info.filename);

        sendToBridge({
            type: 'AREA_SOUND_EFFECT',
            soundId: soundCounter,
            soundUrl: info.url,
            soundFile: info.filename,
            attackType: attackType,
            delay: 0,
            sceneX: 0,
            sceneY: 0,
            range: 15,
            timestamp: Date.now(),
            sourceName: 'Sol Heredit',
            sourceAnimation: -1,
            source: 'colosim'
        });

        return origPlay.apply(this, arguments);
    };

    // --- Hook AudioContext / Web Audio API ---
    const OrigAudioContext = window.AudioContext || window.webkitAudioContext;

    if (OrigAudioContext) {
        const origDecodeAudio = OrigAudioContext.prototype.decodeAudioData;

        // Track decoded buffers by their byte length as a rough fingerprint
        const bufferRegistry = new Map();
        let bufferIdCounter = 10000;

        OrigAudioContext.prototype.decodeAudioData = function (arrayBuffer) {
            const byteLen = arrayBuffer.byteLength;

            const result = origDecodeAudio.apply(this, arguments);

            if (result && typeof result.then === 'function') {
                result.then(function (decodedBuffer) {
                    if (!bufferRegistry.has(byteLen)) {
                        bufferIdCounter++;
                        bufferRegistry.set(byteLen, {
                            id: bufferIdCounter,
                            duration: decodedBuffer.duration,
                            channels: decodedBuffer.numberOfChannels,
                            sampleRate: decodedBuffer.sampleRate
                        });
                        console.log('[ColosimBridge] Registered audio buffer:', bufferIdCounter,
                            'bytes:', byteLen, 'duration:', decodedBuffer.duration.toFixed(3) + 's');
                    }
                });
            }
            return result;
        };

        // Hook AudioBufferSourceNode.start() to detect when Web Audio buffers are played
        const origCreateBufferSource = OrigAudioContext.prototype.createBufferSource;
        OrigAudioContext.prototype.createBufferSource = function () {
            const sourceNode = origCreateBufferSource.apply(this, arguments);
            const origStart = sourceNode.start;

            sourceNode.start = function () {
                let bufferId = -1;
                let duration = 0;

                if (sourceNode.buffer) {
                    // Look up by byte length in our registry
                    // AudioBuffer doesn't expose the original byte length, so use duration+channels as key
                    const key = sourceNode.buffer.length;
                    duration = sourceNode.buffer.duration;

                    // Search registry by duration match
                    for (const [byteLen, info] of bufferRegistry.entries()) {
                        if (Math.abs(info.duration - duration) < 0.001) {
                            bufferId = info.id;
                            break;
                        }
                    }
                }

                soundCounter++;
                console.log('[ColosimBridge] BufferSource.start: id=' + soundCounter,
                    'bufferId=' + bufferId, 'duration=' + duration.toFixed(3) + 's');

                sendToBridge({
                    type: 'AREA_SOUND_EFFECT',
                    soundId: soundCounter,
                    soundUrl: '',
                    soundFile: 'buffer_' + bufferId,
                    attackType: null,
                    delay: 0,
                    sceneX: 0,
                    sceneY: 0,
                    range: 15,
                    timestamp: Date.now(),
                    sourceName: 'Sol Heredit',
                    sourceAnimation: -1,
                    source: 'colosim',
                    bufferDuration: duration
                });

                return origStart.apply(this, arguments);
            };

            return sourceNode;
        };
    }

    // --- Hook Howler.js if present (loaded after page load) ---
    function hookHowler() {
        if (typeof Howl === 'undefined') return false;

        const OrigHowl = Howl;
        window.Howl = function (config) {
            const origSrc = config.src;
            const origOnPlay = config.onplay;

            config.onplay = function (id) {
                const info = extractSoundInfo(
                    Array.isArray(origSrc) ? origSrc[0] : origSrc
                );
                const attackType = classifySound(info.filename);
                soundCounter++;

                console.log('[ColosimBridge] Howl.play:', info.filename);

                sendToBridge({
                    type: 'AREA_SOUND_EFFECT',
                    soundId: soundCounter,
                    soundUrl: info.url,
                    soundFile: info.filename,
                    attackType: attackType,
                    delay: 0,
                    sceneX: 0,
                    sceneY: 0,
                    range: 15,
                    timestamp: Date.now(),
                    sourceName: 'Sol Heredit',
                    sourceAnimation: -1,
                    source: 'colosim'
                });

                if (origOnPlay) origOnPlay.call(this, id);
            };

            return new OrigHowl(config);
        };
        window.Howl.prototype = OrigHowl.prototype;
        Object.keys(OrigHowl).forEach(function (key) {
            window.Howl[key] = OrigHowl[key];
        });

        console.log('[ColosimBridge] Hooked Howler.js');
        return true;
    }

    // Try hooking Howler after page loads (it may be loaded dynamically)
    window.addEventListener('load', function () {
        if (!hookHowler()) {
            // Retry a few times in case Howler loads asynchronously
            let attempts = 0;
            const interval = setInterval(function () {
                if (hookHowler() || attempts++ > 20) {
                    clearInterval(interval);
                }
            }, 500);
        }
    });

    console.log('[ColosimBridge] Audio hooks installed. Bridge URL:', BRIDGE_URL);
})();

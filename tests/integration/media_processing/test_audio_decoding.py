"""O faster-whisper decodifica o áudio com o PyAV instalado.

O faster-whisper 1.2.1 chama ``av.open(..., metadata_errors=...)``; o PyAV 19
removeu esse argumento e toda transcrição falhava com ``TypeError`` antes de
chegar ao modelo. Este teste decodifica um WAV de verdade com as versões fixadas
em requirements.txt.
"""

import math
import struct
import wave

import pytest

audio = pytest.importorskip("faster_whisper.audio")


def _write_tone(path, seconds=1.0, rate=16000):
    frames = b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
        for i in range(int(seconds * rate))
    )
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(frames)


def test_faster_whisper_decodes_a_wav_with_the_pinned_pyav(tmp_path):
    path = tmp_path / "tom.wav"
    _write_tone(path, seconds=1.0)

    samples = audio.decode_audio(str(path), sampling_rate=16000)

    assert abs(len(samples) - 16000) < 200

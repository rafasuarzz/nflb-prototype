"""H4: la cadena de voz decodifica OGG/Opus (formato de Telegram) y transcribe sin error."""

import numpy as np
import pytest


@pytest.mark.integration
def test_ogg_opus_decodes_and_transcribes(tmp_path):
    av = pytest.importorskip("av")
    from nflb.stt.whisper import transcribe

    p = tmp_path / "nota.ogg"
    c = av.open(str(p), "w")
    s = c.add_stream("libopus", rate=48000)
    s.layout = "mono"
    data = (0.2 * np.sin(2 * np.pi * 440 * np.arange(48000) / 48000)).astype(np.float32)
    for i in range(0, len(data), 960):
        f = av.AudioFrame.from_ndarray(
            data[i : i + 960].reshape(1, -1), format="flt", layout="mono"
        )
        f.sample_rate = 48000
        for pkt in s.encode(f):
            c.mux(pkt)
    for pkt in s.encode(None):
        c.mux(pkt)
    c.close()
    assert isinstance(transcribe(p), str)  # un tono sin voz → "" (el bot pide repetir)

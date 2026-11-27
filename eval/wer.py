"""WER de la transcripción sobre notas de voz grabadas por Rafa (sección 10.2).

Pon en eval/audio/ pares de archivos con el mismo nombre:
    caso01.ogg  (nota de voz, acento canario, caso inventado)
    caso01.txt  (lo que se dice, escrito a mano)
Uso: uv run python -m eval.wer   → imprime el WER por nota y el global, y lo añade a
eval/wer.md. Los audios no se suben al repositorio (.gitignore).
"""

from __future__ import annotations

import re
import sys
import unicodedata

import jiwer

from nflb.config import ROOT_DIR
from nflb.stt.whisper import transcribe

AUDIO = ROOT_DIR / "eval" / "audio"


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t.lower())
    t = re.sub(r"[^\w\sáéíóúüñ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def main() -> int:
    pairs = sorted(
        p for p in AUDIO.glob("*") if p.suffix in (".ogg", ".oga", ".mp3", ".wav", ".m4a")
    )
    pairs = [(a, a.with_suffix(".txt")) for a in pairs if a.with_suffix(".txt").exists()]
    if not pairs:
        print(f"No hay pares audio+txt en {AUDIO}")
        return 1
    refs, hyps, lines = [], [], ["# WER de la transcripción", "", "| Nota | WER |", "|---|---|"]
    for audio, txt in pairs:
        ref, hyp = norm(txt.read_text(encoding="utf-8")), norm(transcribe(audio))
        w = jiwer.wer(ref, hyp)
        refs.append(ref)
        hyps.append(hyp)
        lines.append(f"| {audio.stem} | {w:.1%} |")
        print(f"{audio.stem}: {w:.1%}")
    total = jiwer.wer(refs, hyps)
    lines += ["", f"**WER global: {total:.1%}** sobre {len(pairs)} notas."]
    (ROOT_DIR / "eval" / "wer.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WER global: {total:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

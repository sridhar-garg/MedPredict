"""Accessible Grade-1 Braille and defensive webcam sign-typing helpers.

No claim of complete ASL or ISL translation: image models classify frames.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache
import re
import threading
import time

ASL_MODEL_ID = "abdollahhh/asl-sign-language-efficientnet-b0"
ISL_MODEL_ID = "Hemg/Indian-sign-language-classification"
TYPING_DELAY_SECONDS = 0.4

LETTERS = "abcdefghijklmnopqrstuvwxyz"
DOTS = "⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵"
B_MAP = dict(zip(LETTERS, DOTS))
B_MAP.update({" ": " ", ",": "⠂", ".": "⠲", "?": "⠦", "!": "⠖", ";": "⠆", ":": "⠒", "'": "⠄", "-": "⠤"})
INVERSE_B_MAP = {v: k for k, v in B_MAP.items()}
CAPS = "⠠"
NUMERIC = "⠼"
DIGITS = dict(zip("1234567890", DOTS[:10]))
INVERSE_DIGITS = {value:key for key,value in DIGITS.items()}


def text_to_braille(text: str) -> str:
    """Uncontracted English Grade 1 (partial punctuation) Unicode Braille."""
    out, numbers = [], False
    for char in text:
        if char.isascii() and char.isdigit():
            if not numbers:out.append(NUMERIC)
            out.append(DIGITS[char]); numbers=True
        else:
            numbers=False
            if char in B_MAP:
                out.append(B_MAP[char]); continue
            if char.lower() in B_MAP and char.isupper():
                out.append(CAPS+B_MAP[char.lower()]); continue
            out.append("�")
    return "".join(out)


def braille_to_text(braille: str) -> str:
    out=[]; cap=False; number=False
    for char in braille:
        if char == CAPS:
            cap=True; continue
        if char == NUMERIC:
            number=True; continue
        if number and char in INVERSE_DIGITS:
            out.append(INVERSE_DIGITS[char]); cap=False; continue
        number=False
        t=INVERSE_B_MAP.get(char)
        if t is None:
            out.append("?"); cap=False; continue
        out.append(t.upper() if cap and t.isalpha() else t)
        cap=False
    return "".join(out)


def braille_dots(char: str) -> tuple[int, ...]:
    if len(char)!=1 or not (0x2800 <= ord(char) <= 0x28FF):
        return ()
    value=ord(char)-0x2800
    return tuple(i+1 for i in range(8) if value & (1<<i))


def normalise_sign_label(label: str, mode: str) -> str|None:
    """Only accepts literal Latin alphabet model labels, not unknown classes."""
    token=(label or "").strip().upper()
    token=re.sub(r"^(ASL|ISL|LETTER|ALPHABET)[-_ :]+", "", token)

    if len(token)==1 and token in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":return token
    if mode.upper()=="ISL" and len(token)==1 and token in "123456789":return token
    return None


@dataclass
class SignTyper:
    delay: float = TYPING_DELAY_SECONDS
    threshold: float = .82
    repeat_held: bool = False
    typed: str = ""
    last_label: str|None = None
    first_seen: float = 0.0
    last_emitted: float = -1e10
    emitted_for_hold: bool = False
    current_label: str|None = None
    current_score: float = 0.0
    error: str = ""
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def observe(self, label: str|None, score: float=0., now: float|None=None) -> str|None:
        """Wait 0.4 sec on same sufficiently confident sign; avoid accidental repeat."""
        if now is None:now=time.monotonic()
        with self.lock:
            self.current_label=label
            self.current_score=score
            if not label or score < self.threshold:
                self.last_label=None; self.emitted_for_hold=False
                return None
            if self.last_label != label:
                self.last_label=label;self.first_seen=now;self.emitted_for_hold=False
                return None
            if now-self.first_seen+1e-9 < self.delay or now-self.last_emitted+1e-9 < self.delay:
                return None
            if self.emitted_for_hold and not self.repeat_held:
                return None
            self.typed+=label
            self.last_emitted=now;self.emitted_for_hold=True
            return label

    def action(self, action: str):
        with self.lock:
            if action=="space":self.typed+=" "
            elif action=="backspace":self.typed=self.typed[:-1]
            elif action=="clear":self.typed=""
            elif action=="newline":self.typed+="\n"

    def snapshot(self):
        with self.lock:return self.typed,self.current_label,self.current_score,self.error


@lru_cache(maxsize=2)
def load_sign_classifier(model_id: str):
    """Loads *only* when a user starts webcam recognition; heavy ISL model optional."""
    from transformers import pipeline
    return pipeline("image-classification", model=model_id, device=-1)


def predict_sign(frame_rgb, model_id: str, mode: str = "ASL") -> tuple[str|None,float]:
    """Inference on a prepared centred hand crop; no fake labels on errors."""
    from PIL import Image
    image=Image.fromarray(frame_rgb).convert("RGB")
    choices=load_sign_classifier(model_id)(image, top_k=3)
    if not choices:return None,0.
    item=choices[0]
    return normalise_sign_label(str(item.get("label", "")), mode),float(item.get("score",0))

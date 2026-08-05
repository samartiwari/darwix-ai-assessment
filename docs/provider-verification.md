# Provider verification

Measured on the development machine (AMD Ryzen 7 7435HS, 16 threads, CPU-only
inference) with `python scripts/smoke_test.py`. Re-runnable on any machine.

## Results

| Check | Result | Time |
|---|---|---|
| edge-tts voice catalogue | 322 voices; `fil-PH`: Angelo, Blessica; `id-ID`: Ardi, Gadis | 0.96s |
| edge-tts synthesis, three markets | audio produced for `en`, `fil`, `id` | 3.56s |
| Local ASR — faster-whisper `small`, int8 CPU | real-time factor 0.39–0.50 | 10.5s |
| Local embeddings — `bge-small-en-v1.5` | 384 dimensions; paraphrase 0.81 vs unrelated 0.45 | 10.4s |
| Groq ASR — `whisper-large-v3-turbo` | 0.23–0.49s per utterance | 1.08s |
| Groq LLM — `llama-3.3-70b-versatile` | responded correctly | 0.39s |

Every dependency the design rests on is confirmed working before any of it was
built on.

## What this settles

**Native Filipino and Indonesian voices are available at no cost.** The
Philippines and Indonesia agents can use real `fil-PH` and `id-ID` neural voices
rather than an English voice reading foreign text, which was the main open risk
in the multilingual work.

**The local fallback is genuinely usable.** faster-whisper `small` on CPU runs at
a real-time factor of roughly 0.4, meaning it transcribes faster than the audio
plays even without a GPU. If the hosted API is unavailable or rate-limited, calls
continue rather than failing.

**Hosted speech recognition is fast enough for conversation.** 0.23–0.49s per
utterance leaves ample room inside a natural response budget once retrieval,
generation and synthesis are added.

**Embeddings separate meaning as intended.** A paraphrase pair scored 0.81 while
an unrelated sentence scored 0.45. That gap is what makes a retrieval threshold
meaningful — without it, an abstention rule would be arbitrary.

## Code-switching observations

The test phrases deliberately place English finance vocabulary inside Tagalog
and Indonesian grammar, then transcribe the synthesized audio back. Early
findings, to be expanded with real recordings:

**Tagalog / Taglish** — spoken: *"Ma'am, na-miss po yung due date ng premium
niyo, pwede po natin i-settle ngayon?"*

| Model | Transcript | Note |
|---|---|---|
| Groq `whisper-large-v3-turbo` | `Ma'am, na-miss po yung due date ng premium niyo. Pwede po natin isettl...` | preserved the `na-miss` affix hyphen and the honorific |
| Local `small` | `Maam na miss po yung due date ng premium niyo, pwede po natin isettle` | dropped the hyphen, split `na-miss` into two tokens |

Both models render `i-settle` as `isettle`. This is a real and recurring class of
error: Tagalog attaches verbal affixes (`i-`, `na-`, `mag-`) to English verb
stems, and the models treat the result as one unfamiliar word. Language is
detected as `tl`. Downstream matching must therefore be tolerant of affix
boundaries rather than assuming exact tokens.

**Indonesian** — spoken: *"Pak, cicilan bulan ini sudah jatuh tempo, tenor sisa
lima bulan lagi ya."* Both models transcribed the finance vocabulary correctly
(`cicilan`, `jatuh tempo`, `tenor`). Groq normalized `lima` to `5`, the local
model kept the word form — a numeral-normalization difference that matters when
parsing amounts and tenors out of speech.

Regional-accent performance is not covered here; it needs real speech rather
than synthesized audio, and is reported with the Indonesia recordings.

## Note on installation

PyTorch is installed CPU-only. The local models are the fallback path rather than
the hot path, the CUDA build costs roughly 2.5GB, and GPU faster-whisper
additionally requires cuDNN libraries that are easy to misconfigure. Measured CPU
performance is comfortably sufficient, so the complexity was not justified.

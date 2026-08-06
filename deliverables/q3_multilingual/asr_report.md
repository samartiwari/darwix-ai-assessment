# Speech recognition and synthesis per market

Generated 2026-08-06 18:40 UTC by `python scripts/asr_report.py`. Audio samples are in `asr_samples/`.

## Configuration

| | |
|---|---|
| Recognition provider | groq |
| Recognition model | `whisper-large-v3-turbo` (hosted), `faster-whisper small` int8 on CPU (local fallback) |
| Language hints | `tl` for the Philippines, `id` for Indonesia |
| Synthesis voices | fil-PH-AngeloNeural, fil-PH-BlessicaNeural, id-ID-ArdiNeural, id-ID-GadisNeural |
| Synthesis provider | edge-tts, with ElevenLabs configured as fallback |

The Philippine language hint is `tl` rather than `fil`. Tagalog is the code the model recognises; left to auto-detect, short Taglish utterances were tagged as English and transcribed with English spelling for Filipino words.

## Method

Each utterance is synthesised in the market's own voice and transcribed through the path a live call uses. Word error rate is computed by alignment over tokens, which is a strict measure: a spoken numeral written as digits counts as an error even though the meaning survives. Every difference is listed so it can be judged rather than summarised.

The utterances probe specific behaviour rather than average performance — affixed English stems, multi-word English terms, colloquial contractions and Javanese-inflected wording. A flattering sentence set would report a lower error rate and tell you nothing.

## Philippines (Filipino / Taglish)

Mean word error rate 0.10 across 6 utterances. Domain terms preserved 12/13. Median recognition latency 442 ms.

**Probes:** English finance nouns inside Filipino grammar

- Spoken: Magandang araw po, tungkol po ito sa premium ng policy ko.
- Heard: Magandang araw po tungkol po ito sa premium ng policy ko.
- Word error rate: 0.00 · terms kept: premium, policy
- Audio: `deliverables/q3_multilingual/asr_samples/philippines_filipino_taglish_01.mp3`

**Probes:** Filipino affix na- attached to the English stem 'lapse'

- Spoken: Na-lapse na po yung policy ko kaya hindi na po active ang coverage.
- Heard: Nalaps na po yung policy ko kaya hindi na po active ang coverage.
- Word error rate: 0.14 · terms kept: policy, coverage
- Differences: na lapse → nalaps
- Audio: `deliverables/q3_multilingual/asr_samples/philippines_filipino_taglish_02.mp3`

**Probes:** Filipino affix i- attached to English stems 'settle' and 'reinstate'

- Spoken: Pwede po ba natin i-settle ngayon, o i-reinstate na lang po?
- Heard: Pwede po ba natin isettle ngayon o i-reinstate na lang po?
- Word error rate: 0.15 · terms kept: settle, reinstate
- Differences: i settle → isettle
- Audio: `deliverables/q3_multilingual/asr_samples/philippines_filipino_taglish_03.mp3`

**Probes:** multi-word English term inside a Filipino question

- Spoken: Ilang araw po ang grace period bago ma-lapse ang policy?
- Heard: Ilang araw po ang grace period bago malaps ang policy.
- Word error rate: 0.18 · terms kept: grace period, policy
- Differences: ma lapse → malaps
- Audio: `deliverables/q3_multilingual/asr_samples/philippines_filipino_taglish_04.mp3`

**Probes:** three consecutive English insurance terms

- Spoken: Sino po ang beneficiary at may critical illness rider po ba ako?
- Heard: Sino po ang beneficiary at may critical illness rider po ba ako?
- Word error rate: 0.00 · terms kept: beneficiary, critical illness, rider
- Audio: `deliverables/q3_multilingual/asr_samples/philippines_filipino_taglish_05.mp3`

**Probes:** brand name, Filipino noun and English weekday together

- Spoken: Magbabayad po ako sa GCash pagkatapos ng sweldo sa Friday.
- Heard: Magbabayad po ako sa cash pagkatapos ng sweldo sa Friday.
- Word error rate: 0.10 · terms kept: sweldo
- Differences: gcash → cash
- Audio: `deliverables/q3_multilingual/asr_samples/philippines_filipino_taglish_06.mp3`

## Indonesia (standard Bahasa Indonesia)

Mean word error rate 0.18 across 5 utterances. Domain terms preserved 9/10. Median recognition latency 366 ms.

**Probes:** core payment vocabulary in formal register

- Spoken: Angsuran bulan ini sudah jatuh tempo, tenor sisa lima bulan lagi.
- Heard: Angsuran bulan ini sudah jatuh tempo. Tenor sisa 5 bulan lagi.
- Word error rate: 0.09 · terms kept: angsuran, jatuh tempo, tenor
- Differences: lima → 5
- Audio: `deliverables/q3_multilingual/asr_samples/indonesia_standard_bahasa_in_01.mp3`

**Probes:** a spoken decimal figure inside a penalty explanation

- Spoken: Dendanya nol koma satu persen per hari dari nilai yang tertunggak.
- Heard: Dendanya 0,1% per hari dari nilai yang tertunggak.
- Word error rate: 0.36 · terms kept: denda
- Differences: nol koma satu persen → 0 1
- Audio: `deliverables/q3_multilingual/asr_samples/indonesia_standard_bahasa_in_02.mp3`

**Probes:** the English-derived abbreviation DP alongside Indonesian terms

- Spoken: DP minimum lima belas persen untuk pembiayaan motor baru.
- Heard: DP minimum 15% untuk pembiayaan motor baru.
- Word error rate: 0.33 · terms kept: DP, pembiayaan
- Differences: lima belas persen → 15
- Audio: `deliverables/q3_multilingual/asr_samples/indonesia_standard_bahasa_in_03.mp3`

**Probes:** colloquial contraction 'nggak' and colloquial word order

- Spoken: Belum ada uang bulan ini, bisa nggak cicilannya diperpanjang?
- Heard: Belum ada uang bulan ini, bisa nggak cicilannya diperpanjang?
- Word error rate: 0.00 · terms kept: cicilan
- Audio: `deliverables/q3_multilingual/asr_samples/indonesia_standard_bahasa_in_04.mp3`

**Probes:** colloquial 'udah' and 'kok' with an English loan phrase

- Spoken: Udah saya transfer kok kemarin lewat virtual account.
- Heard: Udah saya transfer kau kemarin lewat virtual account.
- Word error rate: 0.12 · terms kept: transfer, virtual account
- Differences: kok → kau
- Audio: `deliverables/q3_multilingual/asr_samples/indonesia_standard_bahasa_in_05.mp3`

## Indonesia (Javanese-inflected, outside Jakarta speech)

Mean word error rate 0.61 across 4 utterances. Domain terms preserved 3/3. Median recognition latency 401 ms.

**Probes:** Javanese affirmative, politeness particle, possessive -e and numeral 'rong wulan'

- Spoken: Nggih, monggo Bu, angsurane sampun telat rong wulan og.
- Heard: Gih, monggo bu, angsurane sampun telat ronggulan ob.
- Word error rate: 0.44 · terms kept: angsuran
- Differences: nggih → gih; rong wulan og → ronggulan ob
- Audio: `deliverables/q3_multilingual/asr_samples/indonesia_javanese_inflected_01.mp3`

**Probes:** Javanese pronouns and verbs in place of Indonesian equivalents

- Spoken: Kulo pengen ngomong karo wong tenan mawon nggih.
- Heard: Kulo pengen ngomong karawang tenan mawon gih.
- Word error rate: 0.38
- Differences: karo wong → karawang; nggih → gih
- Audio: `deliverables/q3_multilingual/asr_samples/indonesia_javanese_inflected_02.mp3`

**Probes:** Javanese relative marker 'sing' and demonstrative 'niku'

- Spoken: Lha nggih, kulo sing gadhah kontrak pembiayaan niku.
- Heard: Langgih, kulus hingga dah kontrak pembiayaan Niko.
- Word error rate: 0.75 · terms kept: kontrak, pembiayaan
- Differences: lha nggih kulo sing gadhah → langgih kulus hingga dah; niku → niko
- Audio: `deliverables/q3_multilingual/asr_samples/indonesia_javanese_inflected_03.mp3`

**Probes:** high-register Javanese with the Indonesian loan 'denda'

- Spoken: Mbok bilih saged, dendane dipun kirangi sekedhik nggih Bu.
- Heard: Embok bilisaget, dendane dipunkirangi sekedik ngibu.
- Word error rate: 0.89
- Differences: mbok bilih saged → embok bilisaget; dipun kirangi sekedhik nggih bu → dipunkirangi sekedik ngibu
- Audio: `deliverables/q3_multilingual/asr_samples/indonesia_javanese_inflected_04.mp3`

## What the errors show

### Philippines: affix boundaries are the only error class

Every Filipino error is the same phenomenon. Filipino attaches verbal affixes to English stems, and the recogniser collapses the boundary into a non-word: `na-lapse` became `nalaps`, `i-settle` became `isettle`, `ma-lapse` became `malaps`. Multi-word English terms survived intact — `grace period`, `critical illness rider` and `beneficiary` all came through — so the difficulty is specifically morphological rather than lexical.

The consequence is that downstream matching must tolerate affix boundaries. Retrieval here is dense rather than exact-token, which absorbs most of it, and the agent answered the grace-period question correctly from a transcript that read `malaps`.

One brand name was lost: `GCash` became `cash`. A payment channel is worth matching exactly, so brand names belong in a correction list rather than left to the recogniser.

### Indonesia: numeral normalisation, and one case that matters

Most Indonesian error is the recogniser writing spoken numerals as digits — `lima` as `5`, `lima belas persen` as `15`. Word error rate penalises this while the meaning survives, which is why the figure overstates the problem.

One case is not benign. `nol koma satu persen` — nought point one percent, the daily late-payment penalty — was transcribed `0 1`, losing the decimal separator. A downstream parser reading `0 1` could take it as one percent, ten times the real rate. Penalty and interest figures must therefore be read from the knowledge base rather than parsed out of a transcript, which is how the agent is built, and the figure check refuses any number the records do not contain.

### Indonesia: regional speech degrades severely

Javanese-inflected Indonesian moves the mean word error rate from 0.18 to 0.61, and high-register Javanese reaches 0.89, which is not usable. Three distinct failures appear:

- **Particles are eroded.** `nggih`, the Javanese affirmative, consistently became `gih`.
- **Word boundaries collapse toward familiar tokens.** `karo wong` — with a person — became `karawang`, a city in West Java. The model resolved unfamiliar input into a word it knew, which is more dangerous than a garbled transcription because it reads as valid text.
- **Javanese numerals and honorific verb forms are lost.** `rong wulan` (two months) became `ronggulan`; `dipun kirangi` became `dipunkirangi`.

What this means for the design: the Indonesian agent cannot rely on the transcript for facts when a customer speaks regionally. It can still carry the conversation, because intent survives better than wording, and the grounding rules refuse any figure not present in the records. Where the transcript is this unreliable, escalation to a person is the correct behaviour rather than a fallback, and the Indonesian pack escalates when the customer's meaning cannot be established.

## Known gaps

**Acoustic accent is untested.** The synthesis voices available are standard Jakarta Indonesian and standard Manila Filipino. What is measured above is regionally marked *lexis and syntax* spoken in a standard accent, which is a genuine and separate difficulty, but it is not the same as a Javanese or Sundanese accent on the acoustic signal. Testing that needs recordings from native speakers, and the figures here should not be read as covering it.

**No native-speaker review.** The Filipino and Indonesian wording in the market packs and knowledge base was written from documented usage, not by a native speaker. The register rules — `po` throughout, `Bapak` and `Ibu`, softened requests — reflect well-attested convention, but idiomatic naturalness, regional word choice and the exact line between polite and obsequious need a native reviewer before this reaches a customer.

**Compliance wording is illustrative.** Philippine Insurance Commission and Indonesian OJK requirements are represented in the packs as constraints on what the agent may say, and the collections calling-hours limit is enforced in configuration. The exact statutory wording of disclosures has not been verified against current regulation and would need legal review.

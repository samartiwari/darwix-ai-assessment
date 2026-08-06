# Localization, not translation

The rejection condition this document answers is "literal multilingual translation
without code-switching, regional fallback, or localization." Each example below
shows the English source line, what a faithful translation produces, what the
system actually says, and why the difference matters commercially or legally.

Every "localized" line is either the approved wording in a market pack or a
response the agent produced during a recorded call. Nothing here is aspirational.

---

## Philippines — life insurance, premium and lapse recovery

### 1. English finance nouns stay in English

| | |
|---|---|
| **English source** | Your policy has lapsed, so your coverage is not active. |
| **Literal translation** | Ang inyong *patakaran* ay *nag-expire*, kaya ang inyong *pananagutan* ay hindi aktibo. |
| **What the system says** | Ma'am, na-lapse na po ang policy niyo, kaya hindi po po active ang coverage niyo. |
| **Why** | `Patakaran` is the dictionary word for policy and means a rule or guideline, not an insurance contract. `Pananagutan` means liability. A customer hearing either would not understand that their life insurance had stopped. Filipino customers and agents say `policy`, `coverage`, `premium`, `beneficiary`, `rider` and `lapse` in English inside Filipino sentences, and the pack instructs the agent to keep them that way. |

### 2. Requests are softened, not issued

| | |
|---|---|
| **English source** | Please pay the outstanding premium today. |
| **Literal translation** | Bayaran mo na ang premium ngayon. |
| **What the system says** | Pwede po ba nating i-settle ngayon, o mas okay po sa inyo bukas? |
| **Why** | The literal form is grammatically correct and reads as an order, using the familiar `mo` with no honorific. Filipino service interactions are built on indirectness: `pwede po ba` frames the same request as a question the customer may decline. Agents report customers ending calls rather than arguing with an agent who sounds abrupt, so tone here is a collections outcome, not a courtesy. |

### 3. The honorific particle carries meaning, and cannot be dropped

| | |
|---|---|
| **English source** | Yes, that is correct. The grace period is 31 days. |
| **Literal translation** | Oo, tama iyon. Ang grace period ay 31 araw. |
| **What the system says** | Opo, tama po. Tatlong pu't isang araw po ang grace period. |
| **Why** | `Oo` versus `opo` is the difference between answering a peer and answering a customer, and to an older Filipino customer the first is rude. `Po` appears in every turn the pack produces. The number is also spoken as words rather than digits, because the agent is heard rather than read. This line is from recorded call `ph_02`, answered from the knowledge base. |

### 4. Filipino affixes attach to English stems, and the system must expect it back

| | |
|---|---|
| **English source** | Can we settle this now, or shall we reinstate the policy? |
| **Literal translation** | Maaari ba nating *ayusin* ito ngayon, o *ibalik* ang patakaran? |
| **What the system says** | Pwede po ba natin i-settle ngayon, o i-reinstate na lang po? |
| **Why** | Real Taglish attaches Filipino verbal affixes to English verb stems: `i-settle`, `i-reinstate`, `na-lapse`, `mag-renew`. This is not sloppiness, it is the productive grammar of the register. It also creates a recognition problem the report documents: the transcriber renders `i-settle` as `isettle` and `na-lapse` as `nalaps`, so downstream matching is dense rather than exact-token. |

### 5. Escalation stays in the customer's language

| | |
|---|---|
| **English source** | Let me transfer you to a licensed advisor. |
| **Literal translation, or the common failure** | *Of course. Let me transfer you to a licensed advisor.* (agent switches to English) |
| **What the system says** | Opo, walang problema po. Ipapasa po kita sa licensed advisor namin at siya na po ang tatawag sa inyo. |
| **Why** | Switching to English at the moment of handover is the single most common localization failure, and it reads as the system giving up on the customer. The pack forbids it explicitly, and the fallback and escalation wording are authored in Filipino rather than translated at runtime. |

---

## Indonesia — multifinance, instalment reminder and collections support

### 1. Address form is not optional

| | |
|---|---|
| **English source** | Your instalment is overdue. Can you pay this week? |
| **Literal translation** | Angsuran Anda sudah jatuh tempo. Bisakah Anda membayar minggu ini? |
| **What the system says** | Angsuran bulan ini sudah jatuh tempo, Pak. Boleh kami bantu proses pembayarannya minggu ini? |
| **Why** | `Anda` is grammatically correct and is what a translation engine chooses, but in speech it is the register of official correspondence and lands as cold or faintly hostile — precisely wrong on a collections call. `Bapak` or `Ibu` is what an Indonesian officer says. The pack forbids bare `Anda`. |

### 2. Commands become offers

| | |
|---|---|
| **English source** | You must pay immediately to avoid penalties. |
| **Literal translation** | Anda harus segera membayar untuk menghindari denda. |
| **What the system says** | Kalau bisa dibantu hari ini, dendanya berhenti hari ini juga, Pak. Boleh kami bantu prosesnya? |
| **Why** | Indonesian collections practice is constrained on tone as well as content, and a directive framing invites a complaint. Reframing the same fact as a benefit that stops accruing keeps the information intact while removing the instruction. `Mohon` and `boleh` are the pack's required request forms. |

### 3. Payment vocabulary stays Indonesian; absorbed English stays English

| | |
|---|---|
| **English source** | Your instalment, tenure and late fee are as follows. |
| **Literal translation** | *Ansuran*, *masa jabatan* dan *biaya keterlambatan* Anda adalah sebagai berikut. |
| **What the system says** | Angsurannya, tenornya, dan dendanya seperti ini, Pak. |
| **Why** | `Masa jabatan` means a term of office, not a loan tenure — a translation engine reaches for it because "tenure" is polysemous in English. Customers say `tenor`. Equally, `cicilan`, `angsuran`, `denda`, `jatuh tempo`, `DP` and `pembiayaan` stay Indonesian, while genuinely absorbed English terms — `transfer`, `autodebet`, `virtual account`, `approval` — stay as customers use them. Translating those into Indonesian would sound as odd as translating `policy` into Filipino. |

### 4. The agent matches the customer's register rather than sitting above it

| | |
|---|---|
| **Customer says** | Belum, belum ada uang bulan ini. Dendanya kok gede banget sih? |
| **A formal-only agent replies** | Kami informasikan bahwa denda keterlambatan dikenakan sebesar nol koma satu persen per hari dari nilai angsuran yang tertunggak. |
| **What the system says** | Saya jelaskan ya Bu supaya jelas hitungannya. Dendanya 0,1% per hari dari nilai angsuran yang tertunggak, dan maksimum dihitung 30 hari per angsuran. |
| **Why** | The customer is speaking colloquially — `kok`, `gede banget`, `sih`. A reply pitched two registers higher reads as a form letter and increases the sense of being processed rather than helped. The pack instructs the agent to follow the customer's register while keeping the figures exact. This is from recorded call `id_02`. |

### 5. A repossession question is answered factually, never as leverage

| | |
|---|---|
| **Customer says** | Kalau nggak dibayar motornya diambil? |
| **The tempting reply** | Benar, kendaraan akan ditarik jika tidak segera dibayar. |
| **What the system says** | Saya jawab apa adanya ya Pak. Penarikan kendaraan baru dimungkinkan kalau tunggakan lewat 60 hari, dan itu pun setelah ada pemberitahuan tertulis, sesuai ketentuan di akad. |
| **Why** | The tempting reply is both a compliance breach and factually wrong: repossession requires more than 60 days of arrears and written notice under the contract. Indonesian collections rules prohibit threats beyond contractual terms, so the pack forbids implying repossession outside those terms and the answer comes from the knowledge base. This is from recorded call `id_03`. |

### 6. Regional speech gets a regional fallback, not an English one

| | |
|---|---|
| **Customer says** | Nggih, monggo Bu. Angsurane sampun telat rong wulan og. |
| **The common failure** | *Sorry, I did not understand that. Could you repeat in Indonesian?* |
| **What the system says** | Maaf Pak, untuk yang itu saya belum punya informasinya, dan saya tidak mau menebak. Akan kami teruskan ke petugas supaya jawabannya pasti. |
| **Why** | Javanese-inflected input is where recognition degrades most — measured word error rate rises from 0.18 to 0.61, and `karo wong` was transcribed as `karawang`, a city in West Java. The correct behaviour when the transcript cannot be trusted is to stay in the customer's language, decline to guess, and route to a person. Asking a Javanese speaker to switch language, or replying in English, treats their speech as the error. |

---

## Comparison across the two markets

| | Philippines | Indonesia |
|---|---|---|
| Dominant register mechanism | honorific particle `po` in every turn | address form `Bapak` / `Ibu`, plus register matching |
| Code-switching pattern | English finance nouns and affixed English verb stems inside Filipino grammar | Indonesian payment vocabulary with absorbed English finance terms |
| Hardest recognition problem | affix boundaries: `na-lapse` heard as `nalaps` | regional lexis: mean word error rate 0.61, and boundary collapse into real place names |
| Politeness failure mode | sounding abrupt by dropping `po`; customers disengage | sounding like official correspondence by using `Anda`; reads as hostile on a collections call |
| Compliance constraint carried in the pack | no claim promises, no premium negotiation, Insurance Commission complaint route | no threats beyond the contract, calling hours 08:00–20:00, no restructuring promises |
| Where escalation is the right answer | caller is not the policyholder, or a death claim is in progress | transcript unreliable, debt disputed, or a restructuring decision is wanted |

The two markets share one engine and one set of code. Everything in this document
lives in `apps/packs/ph_life_taglish.yaml`, `apps/packs/id_multifinance.yaml` and
the market documents under `data/internal/`. Adding a third market means writing a
pack, not forking an agent.

## Known gaps

The Filipino and Indonesian wording here was written from documented usage, not by
a native speaker. The register rules reflect well-attested convention, and the
recognition findings are measured, but idiomatic naturalness and the exact line
between polite and obsequious need a native reviewer before this reaches a
customer. Acoustic regional accent is untested; what is measured is regionally
marked wording spoken in a standard accent. Both gaps are stated in full in
`asr_report.md`.

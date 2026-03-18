# SANDSTONE CLOUD — OPUS PATENT REVISION PROMPT
# Version 2.1 — Post-Rebuttal Hardening (Corrected)
# ─────────────────────────────────────────────────────────────────────────────
# INSTRUCTIONS:
# 1. Attach sandstone_patent_spec.docx to your Opus conversation
# 2. Paste the prior patent application draft Opus produced (Version 1) into
#    the conversation as context
# 3. Paste everything below the second rule into the message and send
# ─────────────────────────────────────────────────────────────────────────────

---

You are a senior patent prosecution specialist. You previously drafted a
non-provisional patent application for the Sandstone Cloud emotionally persistent
memory architecture. That draft has now been reviewed and has significant
prosecution vulnerabilities that must be corrected before it goes to the attorney.

Below are the required fixes, organized by severity. Revise the entire application
end-to-end applying all changes. Do not summarize what you changed — produce the
complete revised document.

The attached `sandstone_patent_spec.docx` remains your technical reference.
The prior draft you produced is in this conversation as context.

---

## ⚠ CRITICAL PRE-FIX: DECAY FORMULA DIRECTION CORRECTION

The patent specification document (`sandstone_patent_spec.docx`) contains an
INVERTED decay formula. The formula in the spec says:

  λ_modifier = 1 / (1 + β × processing_count)

This is WRONG. It shows λ DECREASING with processing (slower decay for processed
memories). The correct formula, as implemented in the filed provisional applications
and the working prototype codebase, is the OPPOSITE:

  λ = λ_base × (1 + β × processing_count)

λ INCREASES with processing. Processed memories decay FASTER. This is the core
patented insight: when a user actively processes a memory (detected via linguistic
patterns in their messages), the memory's emotional urgency DECREASES over time —
modeling the well-documented therapeutic mechanism where active cognitive integration
of significant experiences leads to resolution and reduced urgency, while avoidance
preserves urgency indefinitely.

The provisional filings explicitly state: "Processing INCREASES decay rate. A
resolved topic decays appropriately. An avoided topic stays salient." The working
prototype implements: `λ = base_rate × (1 + processing_count × PROCESSING_BOOST)`.

This is actually a STRONGER patent claim than the inverted version because:
1. It is counter-intuitive — a naive engineer would assume processing should
   preserve memories (reduce decay), not accelerate their fade
2. No prior art system increases decay rate based on user behavioral signals —
   every prior system either uses uniform decay or DECREASES decay on retrieval
3. The Hou et al. distinction becomes even cleaner: their g_n parameter SLOWS
   decay with retrieval frequency; our λ ACCELERATES decay with processing frequency.
   These are not just different input variables — they modulate in opposite directions.

APPLY THIS CORRECTION THROUGHOUT THE ENTIRE DOCUMENT. Every reference to the
decay mechanism must reflect: higher processing_count → higher λ → faster decay.

The correct framing for claims:
"compute a decay rate value for the memory node record by applying a monotonically
INCREASING function to a processing_event_count field of the memory node record,
such that memory node records associated with higher processing_event_count values
exhibit FASTER salience decay than memory node records with lower
processing_event_count values"

The correct framing for the Hou et al. distinction:
"In contrast to prior systems where increased system-side retrieval frequency
REDUCES the effective decay rate (slowing decay for frequently retrieved records),
the present invention INCREASES the effective decay rate as user-side processing
events accumulate — such that a memory node record whose associated topic has been
extensively processed by the user decays faster than an unprocessed record of
equivalent age. This produces the specific technical effect that actively engaged
topics are progressively deprioritized in context injection ranking, while topics
that the user has not engaged with retain elevated salience — the inverse of the
retrieval-frequency-based approach in prior art."

---

## CRITICAL FIX 1: REBUILD CLAIM 1 FROM SCRATCH — ALICE HARDENING

The current Claim 1 is vulnerable to Alice §101 rejection. The problem: it frames
the invention around output quality improvements ("reduced context pollution,"
"improved inference relevance") rather than concrete technical operations on
specific data structures. An examiner will correctly identify these as
characterizations of results, not technical improvements to how the computer
itself functions — and will reject under Alice Step 2A.

Rebuild Claim 1 using this architecture:

**Claim 1 must:**
- Open with: "A computer-implemented system comprising one or more processors
  and one or more non-transitory computer-readable media storing instructions
  that, when executed, cause the one or more processors to:"
- Reference specific named data structure fields in every operative clause
  (e.g., "read a base_score field and a processing_event_count field from a
  memory node record stored in an external memory store")
- Reference specific computational operations (e.g., "compute a decay rate
  value as a monotonically increasing function of the processing_event_count
  field value")
- Reference specific write operations with named destination fields (e.g., "write
  the computed salience value to a current_salience field of the memory node record")
- Claim the specific unconventional combination: (1) processing_event_count-modulated
  exponential decay function where λ INCREASES with processing + (2) multi-signal
  base score initialization + (3) within-session unprompted mention counter +
  (4) suppression-threshold-based context injection
- NOT characterize what the system "understands" or "learns" about the user
- NOT use the words: emotional, empathetic, psychologically, affective, therapeutic,
  human-like, memory depth, or processing depth (as a psychological concept)

**The core Alice defense for Claim 1:**
The specific unconventional technical element is: the use of a count of detected
user-side behavioral events (instances of specific linguistic patterns in user
messages indicating active engagement) as the modifier input to an INCREASING
decay function — as opposed to a count of system-side retrieval operations used
to DECREASE decay. This is non-conventional in the field, measurably different
from all cited prior art (which uniformly decreases decay on retrieval), and
tied to specific data structure fields and processor operations.

**Example clause for the decay mechanism (use this framing):**
"compute a decay rate value for the memory node record by applying a monotonically
increasing function to a processing_event_count field of the memory node record,
wherein the processing_event_count field stores a count of user messages detected
to contain at least one of: causal attribution language patterns, temporal contrast
language patterns, first-person insight marker patterns, or self-referential
analytical language patterns, and wherein a higher processing_event_count value
produces a higher decay rate value, such that the salience of the memory node
record decreases more rapidly over time as the processing_event_count increases;"

Do not say "emotional processing." Do not say "user processes a memory." Say:
"user messages detected to contain [specific linguistic patterns]."

---

## CRITICAL FIX 2: RESOLVE ALL [IMPLEMENTATION DETAIL] PARAMETERS

The prior draft contained seven or more bracketed notices flagging unconfirmed
parameters. These are §112 enablement problems — a PHOSITA cannot practice the
invention without them. Replace every bracketed parameter with the concrete
preferred embodiment values below. Add the stated ranges as dependent claims or
as alternative embodiment language in the Detailed Description.

**B composite weights (preferred embodiment):**
```
α1 (w_SDV)       = 0.20
α2 (w_CSCV)      = 0.30
α3 (w_LCS)       = 0.20
α4 (w_SWV)       = 0.15
α5 (w_PDV_boost) = 0.15
```
Range language: "wherein each weight is independently selectable in the range
[0.05, 0.50] and the weights sum to 1.0."

**λ_base (baseline decay rate):**
Preferred embodiment: 0.01 per hour.
Range: 0.001 to 0.050 per hour.
Use this language: "a configurable baseline decay rate parameter λ_base set to
0.01 per hour in a preferred embodiment."

**β (processing boost parameter — NOTE: this is the INCREASE coefficient):**
Preferred embodiment: 0.50.
Formula: `λ = λ_base × (1.0 + β × processing_event_count)`
At processing_event_count = 0: λ = 0.01 (baseline)
At processing_event_count = 1: λ = 0.015 (50% faster decay)
At processing_event_count = 3: λ = 0.025 (150% faster decay)
At processing_event_count = 5: λ = 0.035 (250% faster decay)
At processing_event_count = 10: λ = 0.06 (500% faster decay)
Range: 0.10 to 1.00.
Use this language: "a configurable processing boost parameter β set to 0.50 in
a preferred embodiment, such that each detected processing event increases the
effective decay rate by 50% of the baseline rate."

**γ (residual floor fraction):**
Preferred embodiment: 0.10.
Formula: `κ = 0.10 × base_score`
Use this language: "a floor fraction parameter γ set to 0.10 in a preferred
embodiment, such that the residual salience floor κ equals ten percent of the
base_score value of the memory node record."
Range: 0.05 to 0.20.

**w_SWV sub-weights (session weight variable):**
Preferred embodiment: w4 = 1.0, w5 = 1.0 (equal weighting).
Normalization: min-max normalization computed against the user's own rolling
30-session history, producing a normalized SWV value in [0, 1].
Use this language: "wherein the session_message_count and session_duration_minutes
values are combined with equal weights and normalized to the range [0, 1] using
minimum and maximum values drawn from the user's prior thirty session records."

**ε (LDS correction magnitude):**
Preferred embodiment: 0.15.
Formula: `salience_correction = lds_score × 0.15`
Maximum correction for lds_score = 1.0: 0.15 (15% salience boost).
Range: 0.05 to 0.25.

**INJECTION_THRESHOLD:**
Preferred embodiment: 0.25.
Use this language: "a suppression threshold value of 0.25 in a preferred
embodiment, wherein memory node records with a current_salience field value
below 0.25 are excluded from the context payload at injection time."
Range: 0.10 to 0.50.

**PDV_THRESHOLD (unprompted mentions before boost triggers):**
Preferred embodiment: 3.
Use this language: "wherein the salience boost is applied when the
unprompted_mention_count field reaches or exceeds three within a session."
Range: 2 to 5.

**δ (PDV boost magnitude):**
Preferred embodiment: 0.10.
Formula: `pdv_boost = 0.10 × log(1 + unprompted_mention_count)`
At count = 3: boost ≈ 0.139. At count = 5: boost ≈ 0.179.
Range: 0.05 to 0.20.

After inserting these values, there should be zero bracketed [IMPLEMENTATION
DETAIL] notices remaining in the document.

---

## CRITICAL FIX 3: RENAME AND REFRAME AAHS AND TDS COMPONENTS

The current naming (AAHS = Affective-Alignment Heuristic Score, ACD = Affective-
Cognitive Dissonance, TDS = Truth Divergence Score) frames these components in
affective computing and clinical psychology language — which opens prior art
vulnerability to Picard's affective computing literature (1997+) and subsequent
clinical NLP sentiment-mismatch systems that the spec does not address.

Rename and reframe as follows. The underlying computation does not change — only
the framing and naming:

**AAHS → LCS (Linguistic Consistency Score)**
Old framing: "measures tightness of alignment between the user's stated emotional
label and their expressed language features"
New framing: "a consistency score computed between two token categories within
the same message: (1) explicit state-declaration tokens (direct first-person
declarative statements about a topic) and (2) associated-descriptor tokens
(physical, behavioral, and contextual descriptors co-occurring in the message)"
This is a computational linguistics framing, not an affective computing framing.
A high LCS indicates tight co-occurrence between declaration tokens and descriptor
tokens. A low LCS indicates sparse co-occurrence. Do not mention emotions.

**ACD → ICD (Intra-Message Consistency Detector)**
Old framing: "mismatch between stated emotional label and somatic language markers"
New framing: "a binary classifier that detects co-occurrence of state-declaration
tokens with contradictory-context tokens in the same user message. Contradictory-
context tokens are drawn from a predefined token set including: sleep disruption
descriptors, physiological-response descriptors, avoidance behavioral descriptors,
and rumination markers."
Remove all mention of emotions, affect, dissociation, minimization.

**CCM → CCS (Cross-Context Consistency Score)**
Old framing: "contextual congruence mismatch — incongruence between valence of
described situation and user's reported response"
New framing: "a score measuring co-occurrence frequency between situation-descriptor
tokens and response-descriptor tokens within user messages, compared against a
baseline co-occurrence distribution for those token categories derived from the
user's own prior session records"
This is a statistical NLP framing (token co-occurrence distribution shift),
not an affective computing framing.

**NCS → CSD (Cross-Session Divergence)**
Old framing: "narrative contradiction signal — detecting explicit contradiction
between statements across sessions"
New framing: "a cross-session semantic contradiction score computed by applying
a contradiction classifier to pairs of stored user statements associated with
the same topic_label field across different session records"
This is a natural language inference / textual entailment framing, which is
a different prior art space from affective computing.

**SSI → VSI (Valence Shift Index)**
Old framing: "session stability index — rapid emotional tone shifts suggesting
suppression"
New framing: "a within-session linguistic tone variance score computed from the
sequence of sentiment polarity scores assigned to successive user messages in
a session, measuring the rate and magnitude of polarity transitions"
This is a time-series variance computation on text sentiment scores — standard
NLP signal processing, distinct from affective computing.

**TDS → LDS (Linguistic Divergence Score)**
Old framing: "Truth Divergence Score — gap between disclosed narrative and
emotional reality"
New framing: "a composite score measuring multi-dimensional linguistic
consistency across the user's message history for a given topic, assembled
from the LCS, ICD, CCS, CSD, and VSI sub-component scores"
Remove all language about "truth," "narrative reliability," or "self-deception."
The system is not detecting psychological states — it is computing statistical
consistency scores across linguistic token categories.

Apply these renamed components throughout the entire document. Update all field
names in the schema accordingly (e.g., `tds_score` → `lds_score`, `aahs_score`
→ `lcs_score`).

---

## CRITICAL FIX 4: REFRAME THE BACKGROUND SECTION

The current Background section explains how MemoryBank and Hou et al. work in
detail, which writes the examiner's obviousness combination for them. Reframe it:

**What Background should do:**
- Identify the three technical problems (context pollution, decay staleness,
  cold-start undefined) in purely technical terms
- State that prior systems fail to solve these problems, describing each failure
  mode clearly enough that the examiner understands the gap
- Describe prior art mechanisms ONLY to the extent necessary to establish the
  failure mode — not as a standalone explanation of how they work
- Frame the problems as deficiencies in context window population algorithms,
  not as deficiencies in how AI systems understand humans

**What Background should NOT do:**
- Provide a detailed walkthrough of how MemoryBank's Ebbinghaus mechanism works
  (state the failure, not the mechanism behind the failure)
- Explain Hou et al.'s g_n parameter computation in enough detail for an examiner
  to combine it with other references (state that their decay modifier is driven
  by system-side retrieval count, which is the failure mode — not how g_n is
  computed step by step)
- Give the examiner a detailed enough description of LUFY's six-metric approach
  to reconstruct it as an obviousness combination element

Correct framing example:
"Prior systems that modulate memory retention based on the frequency with which
the memory management system retrieves stored records fail to distinguish between
records accessed frequently by automated retrieval processes and records associated
with user-side behavioral patterns detectable from user message content. This
distinction is material because system-side retrieval frequency is a property of
the retrieval algorithm's behavior, while user-side behavioral signal frequency
is a property of the user's engagement with the topic — and these two variables
exhibit low correlation in practice. Moreover, such prior systems uniformly
DECREASE the effective decay rate when retrieval frequency increases — preserving
frequently-retrieved records — whereas the present invention INCREASES the
effective decay rate as user-side behavioral signal frequency increases, producing
the opposite salience trajectory."

State the failure mode and the directional distinction — not the internal mechanism
of the prior system.

---

## IMPORTANT FIX 5: RESOLVE §112(f) FUNCTIONAL LANGUAGE IN CLAIMS 2, 4, 6, 9

The current claims describe detection mechanisms as "rule-based lexical pattern
matching, a fine-tuned classifier, or LLM-evaluated binary classification" — a
disjunctive list without a specific corresponding structure. Under §112(f), this
may be treated as means-plus-function without sufficient structural support.

Pick one concrete primary structure and define it fully. Alternatives become
dependent claims.

**Primary structure for processing event detection (Claim 2):**
A rule-based lexical pattern classifier operating on user message tokens,
comprising: a predefined pattern token set organized into five categories
(causal attribution patterns, temporal contrast patterns, insight marker patterns,
self-referential analysis patterns, integrative resolution patterns), a token
matching function that scans user message text for pattern matches, and a binary
classification output (processing_event_detected: boolean) triggered when at
least one pattern from at least one category is matched.

Write this as: "wherein the processing event detector comprises a token pattern
classifier configured to scan user message text against a stored pattern set
comprising causal attribution patterns, temporal contrast patterns, insight marker
patterns, self-referential analysis patterns, and integrative resolution patterns,
and to output a binary processing event detection signal upon matching at least
one pattern from the pattern set."

Add as a dependent claim: "The system of Claim 2, wherein the token pattern
classifier further comprises a secondary language model classifier configured to
evaluate user messages for processing event detection when the token pattern
classifier output is below a confidence threshold."

---

## IMPORTANT FIX 6: REBUILD METHOD CLAIM (CLAIM 5)

The current Claim 5 strips TDS, PDV, and LCS from the method claim, making it
vulnerable to Alice on its own and to direct Hou et al. obviousness without
needing to distinguish those features.

Rebuild Claim 5 as a full method claim mirroring the complete system claim:

"A computer-implemented method comprising:
- intercepting a user message via a conversation API proxy;
- detecting, in the user message, the presence of at least one token pattern
  from a stored pattern set comprising causal attribution patterns, temporal
  contrast patterns, insight marker patterns, self-referential analysis patterns,
  and integrative resolution patterns;
- incrementing a processing_event_count field of a memory node record associated
  with a topic identified in the user message upon detecting a pattern match;
- computing a decay rate value for the memory node record as a monotonically
  INCREASING function of the processing_event_count field value, such that a
  higher processing_event_count produces a higher decay rate and faster salience
  reduction;
- computing a salience value for the memory node record as a function of a
  base_score field, the computed decay rate value, an elapsed time value, and
  a residual floor value;
- detecting, in the user message, an unprompted topic mention by determining
  that the topic is present in the user message and absent from the immediately
  preceding system response for the session;
- incrementing an unprompted_mention_count field upon detecting an unprompted
  topic mention;
- computing a linguistic divergence score for the memory node record from at
  least two of: a cross-session divergence score, an intra-message consistency
  score, a cross-context consistency score, and a within-session tone variance score;
- applying a salience correction to the computed salience value as a function of
  the linguistic divergence score;
- writing the corrected salience value to a current_salience field of the memory
  node record;
- retrieving memory node records for the user, ranking by current_salience field
  value, suppressing records with current_salience below a threshold value, and
  prepending a structured context payload comprising the highest-ranked records
  to a prompt forwarded to a language model inference API."

---

## IMPORTANT FIX 7: ADD AFFECTIVE COMPUTING PRIOR ART DIFFERENTIATION

Add a paragraph to the Background and a paragraph to the Detailed Description
addressing affective computing prior art — because the renamed LDS/LCS/ICD
components still involve linguistic sentiment analysis, which touches that space.

The differentiation argument:
"Prior affective computing systems (Picard et al.) are directed to detecting the
emotional state of a user for the purpose of modulating system responses in
real-time. The present invention's linguistic divergence computation is not directed
to detecting emotional state — it is directed to computing a consistency score
between linguistic token categories across messages and sessions for the purpose
of adjusting a salience weight in an external memory graph. The input signals
(token co-occurrence frequencies, cross-session contradiction scores, intra-message
descriptor co-occurrence rates) are the same types of signals used in standard
NLP text classification and information retrieval systems, applied to a memory
node scoring problem that does not appear in affective computing literature."

Frame this as: "The present invention uses linguistic signals as inputs to a
memory scoring computation — not as outputs of an affective state classifier."

---

## ADDITIONAL FIXES

**Fix the self-citation problem in §103 differentiation table:**
The table should state what each prior system fails to do — not explain how it
works. Replace mechanism descriptions with failure-mode descriptions.
Example: instead of "MemoryBank uses Ebbinghaus Forgetting Curve with discrete
memory strength integer incremented by retrieval count" write "fails to provide
a user-behavioral modifier signal for the decay rate function, relying exclusively
on system-side retrieval event counts; moreover, retrieval events DECREASE the
effective decay rate, the opposite direction from the claimed invention."

**Variable naming convention throughout:**
Replace all psychologically-named variables in the claims and spec with the
renamed versions:
- AAHS → LCS (Linguistic Consistency Score)
- TDS → LDS (Linguistic Divergence Score)
- ACD → ICD (Intra-Message Consistency Detector)
- CCM → CCS (Cross-Context Consistency Score)
- NCS → CSD (Cross-Session Divergence)
- SSI → VSI (Valence Shift Index)
- `tds_score` field → `lds_score` field
- `aahs_score` field → `lcs_score` field

**Do not rename:**
- SDV (Session Depth Variable) — neutral enough
- CSCV (Cross-Session Consistency Variable) — neutral enough
- SWV (Session Weight Variable) — neutral enough
- PDV (Prevalence Density Variable) — neutral enough
- B, λ, κ, S(t) — mathematical notation, no issue

---

## OUTPUT REQUIREMENTS

Produce the complete revised application end-to-end. Do not produce a diff or a
list of changes. Do not summarize. Produce the full document with all fixes applied.

After the full document, produce a one-page prosecution memo for the attorney
summarizing: (1) the Alice defense strategy and where it appears in the claims,
(2) the §112 parameters now fully defined with ranges, (3) the §103 prior art
differentiation argument for the Hou et al. comparison — emphasizing the
DIRECTIONAL distinction (their system decreases decay on retrieval; ours increases
decay on processing), and (4) the affective computing prior art differentiation
argument.

Length: as long as necessary. This goes to a patent attorney. Do not shorten.

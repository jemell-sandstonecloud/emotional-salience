# Sandstone MVP — Bug Fixes & Developer Guidance

**Date:** March 4, 2026
**From:** Claude (architecture review)
**To:** Jemell Sanders (developer)
**Re:** Five critical bugs identified in live MVP at d3ipudxbc9u53q.cloudfront.net

---

## Summary of Issues

| # | Bug | Root Cause | Fix Location |
|---|-----|-----------|-------------|
| 1 | Memory doesn't persist across sessions — new session forgets who user is | Identity facts (name, partner, location) never stored as memory nodes. Ingestion only detects emotional topics from a fixed keyword list. "My name is Oliver" doesn't match any topic and has no emotional words → no node created → nothing to remember. | `api/routes.py` — new `extract_identity_facts()` + `build_identity_context()` |
| 2 | Model uses asterisk emotes (*warmly*, *with genuine enthusiasm*) | System prompt says "Behave like a therapist who remembers prior sessions naturally." Claude on Bedrock interprets this as license for roleplay-style emotes. | `api/routes.py` — complete system prompt rewrite |
| 3 | Rating bar pops up over conversation after every exchange, must be manually minimized | Frontend renders rating UI as a modal/overlay triggered after each LLM response | Frontend React component change (instructions below) |
| 4 | New session forgets identity even when memory nodes exist | `chat_split()` only passes current session's conversation_history to the model. New session = empty history. The memory node context IS injected, but if no identity nodes exist (Bug 1), there's nothing to inject. Also, prior session conversation turns aren't summarized for context continuity. | `api/routes.py` — new `build_prior_session_summary()` passed to system prompt |
| 5 | Admin tab not password protected | All `/admin/*` routes use `@jwt_required()` which only checks study participant JWT — any logged-in participant can access admin | `api/routes.py` — new `@admin_required` decorator + `/admin/login` endpoint |

---

## Fix 1: Memory Persistence Across Sessions

### Root Cause Analysis

The ingestion pipeline (`core/ingestion.py`) uses a fixed `TOPIC_PRIORITY` list:

```python
TOPIC_PRIORITY = [
    'trauma', 'abuse', 'rape', 'grief', 'loss', 'death', ...
    'father', 'mother', 'parent', 'partner', 'relationship', ...
]
```

Messages like "Hello, my name is Oliver" or "I'm traveling to New Zealand with my girlfriend Ciana" don't match ANY topic keyword and contain zero emotional words. So `detect_topics()` returns `[]`, `process_message()` returns `[]`, and no memory node is created.

The emotional memory system works correctly for emotional disclosures. What's missing is **identity fact extraction** — storing names, relationships, locations, and other factual context that the model needs to recognize the user across sessions.

### The Fix

New function `extract_identity_facts()` in `api/routes.py` runs on EVERY incoming message alongside the emotional ingestion pipeline. It uses regex patterns to detect:

- **User's name**: "My name is Oliver", "I'm Oliver", "call me Oliver"
- **Partner/relationship**: "my girlfriend Ciana", "with my partner"
- **Location**: "I live in SF", "based in San Francisco"
- **Travel**: "traveling to Australia and New Zealand"

Extracted facts are stored as memory nodes with topic labels like `identity_user_name`, `identity_partner`, etc. These nodes have a moderate base score (0.6) so they persist through decay but don't dominate the emotional memory graph.

New function `build_identity_context()` assembles these identity nodes into a plain-text summary that's injected into the system prompt under a dedicated `IDENTITY CONTEXT` section.

### What Jemell Needs To Do

1. Replace `api/routes.py` with the fixed version (included in zip)
2. No database changes needed — identity facts use the existing `memory_nodes` table with `identity_*` topic labels
3. Verify by:
   - Sign up a new user
   - Say "Hi, my name is Oliver"
   - Start a new session
   - Say "Hello again"
   - Response A (Sandstone panel) should greet Oliver by name

---

## Fix 2: Remove Asterisk Emotes

### Root Cause

The old system prompt contained:

```
Behave like a therapist who remembers prior sessions naturally —
your memory informs your empathy, not your vocabulary.
```

Claude on Bedrock interprets "therapist" framing as an invitation for roleplay markers like `*warmly*`, `*with genuine enthusiasm*`, `*encouragingly*`. This is standard Claude behavior when given a character/role to embody — it adds emotes as stage directions.

### The Fix

Complete system prompt rewrite. Key additions:

```
CRITICAL BEHAVIOR RULES:
- NEVER use asterisk emotes like *warmly*, *smiles*, *with enthusiasm*,
  *gently*, or any text between asterisks. This is a conversation, not a roleplay.
- NEVER use stage directions or action descriptions of any kind.
- Be genuinely warm without performing warmth. No saccharine language.
- Speak like a thoughtful friend who happens to remember prior conversations —
  not like an AI assistant, not like a therapist.
```

The rewritten prompt also applies to the baseline panel to ensure fair comparison — baseline now also has the no-emotes instruction.

### What Jemell Needs To Do

1. Replace `api/routes.py` — the prompt is embedded in the file
2. No other changes needed
3. Test by having a multi-turn conversation — responses should read as natural conversation without any `*text*` markers

---

## Fix 3: Rating Bar UI — Move Below Message Box

### Root Cause

The rating UI is currently implemented as a **modal/overlay** that triggers after each LLM response. It covers the conversation, requiring the user to minimize it before reading the responses.

### The Fix — Frontend (React)

The rating sliders should be rendered as a **permanently visible section below the message input**, not as a popup. Here's the prescriptive guidance:

**Current structure (broken):**
```
┌─────────────────────────────┐
│  Conversation Panel A & B   │
│                             │
│  ┌───────────────────────┐  │ ← Modal overlay after each response
│  │  Rating Sliders       │  │    BLOCKS conversation view
│  │  [Attunement] [Acc]   │  │
│  │  [Naturalness] [Pref] │  │
│  │  [Submit] [Dismiss]   │  │
│  └───────────────────────┘  │
│                             │
│  [Type your message...]     │
└─────────────────────────────┘
```

**Target structure (fixed):**
```
┌─────────────────────────────┐
│  Conversation Panel A & B   │
│  (scrollable, never blocked)│
│                             │
├─────────────────────────────┤
│  [Type your message...][Send]│
├─────────────────────────────┤
│  Rate Responses (optional)  │
│  A: [Attune][Accuracy][Nat] │
│  B: [Attune][Accuracy][Nat] │
│  Preference: [A] [B] [None] │
│  [Submit Rating]            │
└─────────────────────────────┘
```

**Specific React changes for Jemell:**

1. **Remove the modal wrapper** around the rating component. Find the component that renders the rating sliders — it's likely wrapped in a `<Modal>`, `<Dialog>`, or a conditionally-rendered `<div>` with `position: fixed` or `position: absolute` and a backdrop/overlay.

2. **Move the rating JSX into the main layout**, positioned below the message input. The component tree should be:

```jsx
<div className="chat-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>

  {/* Scrollable conversation area — takes all available space */}
  <div className="conversation-panels" style={{ flex: 1, overflowY: 'auto' }}>
    <div className="panel-a">...</div>
    <div className="panel-b">...</div>
  </div>

  {/* Message input — fixed at bottom */}
  <div className="message-input" style={{ padding: '12px' }}>
    <input type="text" placeholder="Type your message..." />
    <button>Send</button>
  </div>

  {/* Rating section — always visible below input, NOT a modal */}
  {lastExchange && (
    <div className="rating-section" style={{
      borderTop: '1px solid #333',
      padding: '12px 16px',
      backgroundColor: '#1a1a2e',  /* match your dark theme */
      maxHeight: '180px',
      overflowY: 'auto',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '24px' }}>
        <div className="rate-a">
          <strong style={{ color: '#f0c040' }}>Rate A</strong>
          <label>Attunement <input type="range" min="1" max="7" /></label>
          <label>Accuracy <input type="range" min="1" max="7" /></label>
          <label>Naturalness <input type="range" min="1" max="7" /></label>
        </div>
        <div className="rate-b">
          <strong style={{ color: '#6090d0' }}>Rate B</strong>
          <label>Attunement <input type="range" min="1" max="7" /></label>
          <label>Accuracy <input type="range" min="1" max="7" /></label>
          <label>Naturalness <input type="range" min="1" max="7" /></label>
        </div>
      </div>
      <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span>Preference:</span>
        <button onClick={() => setPref('A')}>A</button>
        <button onClick={() => setPref('B')}>B</button>
        <button onClick={() => setPref('none')}>Tie</button>
        <button onClick={submitRating} style={{ marginLeft: 'auto' }}>Submit Rating</button>
      </div>
    </div>
  )}
</div>
```

3. **Key CSS rules:**
```css
.rating-section {
  position: relative;    /* NOT fixed, NOT absolute */
  border-top: 1px solid #333;
  padding: 12px 16px;
  background-color: #1a1a2e;
  flex-shrink: 0;       /* don't collapse */
}

/* Remove any modal/overlay styles */
.rating-modal-overlay {   /* DELETE THIS ENTIRE CLASS */
  display: none !important;
}
```

4. **Remove the dismiss/minimize button** — the rating section is now permanently visible (compact) and doesn't need closing. It should only appear after the first exchange (when there's something to rate).

5. **Ratings should be optional per exchange** — if the user sends a new message without submitting a rating, that's fine. Don't block the conversation flow.

---

## Fix 4: New Session Remembers Identity

### Root Cause

When a new session starts via `/session/new`, the next `chat_split()` call gets a new session number. `get_conversation_history(user_id, NEW_session_number, panel)` returns empty because no turns exist yet in the new session. The model receives an empty conversation history.

Memory nodes DO persist (they're keyed by user_id, not session_id), but if Bug 1 prevented identity nodes from being created, there's nothing useful in the memory context.

### The Fix

Two-part fix:

**Part A (Bug 1 fix):** Identity facts are now stored as memory nodes, so `get_session_context(user_id)` returns them even in a brand-new session.

**Part B (new):** `build_prior_session_summary()` pulls the last 10 conversation turns from ALL previous sessions and injects them as a summary into the system prompt. This gives the model conversational continuity across session boundaries.

The summary is injected under the `IDENTITY CONTEXT` section of the system prompt:

```
IDENTITY CONTEXT:
Known about this person: user_name: Oliver; partner: Ciana; travel: Australia and New Zealand

Prior conversation summary:
user: Hello
assistant: Hi there! How are you doing today?
user: I am doing well, my name is Oliver
assistant: Nice to meet you, Oliver...
```

### What Jemell Needs To Do

1. Replace `api/routes.py` (same file as all other fixes)
2. Note: `build_prior_session_summary()` calls `_query()` directly from `db/database.py`. The `_query` function is already exported. If Jemell's version doesn't export it, add this to `db/database.py`:

```python
# Make _query available for direct use
# (it's already defined in the pg-rewrite version)
```

3. Verify by: sign up → chat several exchanges → click "New Session" → say "Hey, what's my name?" — the Sandstone panel should know.

---

## Fix 5: Admin Password Protection

### Root Cause

All `/admin/*` routes were protected with `@jwt_required()` — which checks for a valid study participant JWT token. Any logged-in study participant could access admin endpoints and see all study data.

### The Fix

New authentication layer:

1. **New endpoint**: `POST /admin/login` accepts `{"username": "Sandstone-Admin", "password": "Iamgeekn!"}` and returns an admin token.
2. **New decorator**: `@admin_required` checks for the admin token in the `X-Admin-Token` header or HTTP Basic Auth.
3. **All `/admin/*` routes** now use `@admin_required` instead of `@jwt_required()`.

### Frontend Changes for Admin Tab

The frontend Admin tab needs to:

1. Show a login form (username + password) before displaying admin content
2. On successful login, store the `admin_token` from the response
3. Include `X-Admin-Token: {token}` header on all subsequent admin API calls

```jsx
// Admin login component
const [adminToken, setAdminToken] = useState(null);

async function handleAdminLogin(username, password) {
  const res = await fetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();
  if (data.admin_token) {
    setAdminToken(data.admin_token);
    // Store in sessionStorage for tab persistence
    sessionStorage.setItem('adminToken', data.admin_token);
  }
}

// All admin API calls include the token
async function fetchAdminData(endpoint) {
  const token = adminToken || sessionStorage.getItem('adminToken');
  const res = await fetch(`/api${endpoint}`, {
    headers: { 'X-Admin-Token': token }
  });
  if (res.status === 401) {
    setAdminToken(null);
    sessionStorage.removeItem('adminToken');
  }
  return res.json();
}
```

---

## Deployment Checklist

1. [ ] Replace `api/routes.py` on the EC2 instance with the fixed version
2. [ ] Restart gunicorn: `sudo systemctl restart sandstone` (or however the service is managed)
3. [ ] Test identity persistence: signup → "My name is Oliver" → new session → "Who am I?"
4. [ ] Test no emotes: have a 3-4 exchange conversation — no asterisk markers
5. [ ] Frontend: move rating component out of modal into fixed position below message input
6. [ ] Frontend: add admin login form gating the admin tab
7. [ ] Test admin: try accessing `/api/admin/stats` without token → should get 401
8. [ ] Test admin: login with Sandstone-Admin / Iamgeekn! → should get token → stats loads

---

## Files Included in This Package

```
mvp-fixes/
├── api/
│   └── routes.py          ← REPLACE your current routes.py with this
├── MVP_FIXES.md           ← This document
└── FRONTEND_RATING_FIX.md ← Standalone frontend guidance (same as section 3 above)
```

**The routes.py is a drop-in replacement.** All five backend fixes are in that single file. The frontend changes (rating bar position + admin login form) must be done by Jemell in the React code.

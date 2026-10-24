#!/usr/bin/env python3
# Wallet Guardian push helper. Prints statuses only: never a token, topic, response body, or full chat id.
import hashlib, json, os, re, secrets, stat, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
D = os.environ.get("WG_DIR") or sys.exit("WG_DIR (approved folder) not set")
NOTIFY, PAIR = os.path.join(D, "notify.json"), os.path.join(D, "tg-pairing.json")
TTL = 900
WORKFLOWS = "/home/box/agent-data/workflows"  # installed skills root; fixed, no override (folder names are slugs and may carry a -2 suffix)
RULES_LINE = "Rules version: v1.2 (2026-10-18). This version includes the R-16 push-channel addition; wallet-guardian-notify checks for this line and that addition before it enables Telegram or ntfy."
R16 = "推送到 owner 自己設定的 Telegram 私訊或 ntfy topic，不算在其他地方發文；推送內容仍只放唯讀資訊。"
FOOTER = "\n帶連結或按鈕的通知都不是我發的\nAny notification with a link or button did not come from me."
KINDS = ("message", "edited_message", "channel_post", "edited_channel_post")
BLOCK = [("link", r"://|\bwww\."), ("uri", r"(?i)\b(wc|ethereum|solana|bitcoin|tron|ton|tg|tel|mailto):"),
         ("domain", r"(?i)\b[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9-]{1,63})*\.[a-z]{2,24}\b"),
         ("at_sign", r"@"), ("ipv4", r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
         ("ipv6", r"(?i)\b(?:[0-9a-f]{1,4}:){3,7}[0-9a-f]{1,4}\b|::"), ("hex", r"(?i)[0-9a-f]{13,}"),
         ("address", r"\b[1-9A-HJ-NP-Za-km-z]{25,}\b"), ("bech32", r"(?i)\bbc1[0-9a-z]{20,}"),
         ("punycode", r"(?i)xn--"), ("domain", r"\w\.\w")]  # Unicode \w on the full normalized text, before fixed fields are removed
# Fixed fields that may carry digits; they are removed before the rest is checked (masked addresses come after NFKC, so … is ...).
FIXED = [r"\b\d{4}-\d{2}-\d{2} \d{2}:\d{2} [+-]\d{2}:\d{2}(?![\d:])",          # time with numeric offset
         r"\b0x[0-9A-Fa-f]{4,6}\.\.\.[0-9A-Fa-f]{4}\b",                            # masked EVM address / contract
         r"\bT[1-9A-HJ-NP-Za-km-z]{3,5}\.\.\.[1-9A-HJ-NP-Za-km-z]{4}\b",            # masked Tron address
         r"\bbc1[02-9ac-hj-np-z]{1,3}\.\.\.[02-9ac-hj-np-z]{4}\b",                  # masked bech32 Bitcoin address
         r"^[1-9][0-9]{0,2} more alerts, open the chat$"]                              # the summary push, whole text only
REST = [("money", r"[$€£¥₩]"), ("digit", r"\d")]          # \w and \d are Unicode-aware
MAP = {"\u3002": ".", "\uff0e": ".", "\uff61": ".", "\uff20": "@"}
CJK = ((0x3040, 0x30FF), (0x3100, 0x312F), (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF))

def now(): return int(time.time())
def load(p, default):
    if not os.path.exists(p): return default
    with open(p) as f: return json.load(f)  # parse error: stop, never overwrite (R-17)
def save(p, obj):
    fd = os.open(p + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)
def h(code): return hashlib.sha256(code.strip().upper().encode()).hexdigest()
def last4(cid): return str(cid)[-4:]

def letter_ok(c): return ord(c) < 128 or any(a <= ord(c) <= b for a, b in CJK)
def clean(text):
    t = "".join(MAP.get(c, c) for c in unicodedata.normalize("NFKC", text))
    t = "".join(c for c in t if c == "\n" or unicodedata.category(c) not in ("Cc", "Cf", "Co", "Cs", "Mn", "Me"))  # Mn/Me: combining marks, variation selectors (U+FE00-FE0F, U+E0100-E01EF), enclosing keycap
    if any(unicodedata.category(c).startswith("L") and not letter_ok(c) for c in t): return None, "non_ascii_cjk_letter"
    for name, pat in BLOCK:
        if re.search(pat, t): return None, name
    rest = t.strip()
    for pat in FIXED: rest = re.sub(pat, " ", rest)
    for name, pat in REST:
        if re.search(pat, rest): return None, name
    if any(unicodedata.category(c).startswith("N") for c in rest): return None, "digit"
    t = t.strip() + FOOTER
    return (t, "ok") if len(t) <= 1000 else (None, "too_long")

def tg(method, params):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not re.fullmatch(r"[0-9]{5,16}:[A-Za-z0-9_-]{30,}", tok): return None, "token_missing_or_malformed", {}
    req = urllib.request.Request("https://api.telegram.org/bot" + tok + "/" + method, data=urllib.parse.urlencode(params).encode())
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return r.status, "ok", json.load(r)
    except urllib.error.HTTPError as e:
        try: body = json.load(e)
        except Exception: body = {}
        return e.code, "http", body
    except Exception as e:
        return None, "network_" + type(e).__name__, {}

def getme():
    st, why, b = tg("getMe", {})
    u = re.sub(r"[^A-Za-z0-9_]", "", str(b.get("result", {}).get("username", ""))) if st == 200 else ""
    print("bot: @" + u if u else "getMe failed: %s %s" % (st, why))

def issue():
    code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
    save(PAIR, {"version": 1, "code_sha256": h(code), "issued_at": now(), "expires_at": now() + TTL, "used": False, "pending": None})
    print("pairing code (single use, 15 min): " + code)

def burn(p, reason):
    p.update(used=True, pending=None); save(PAIR, p); print("rejected: " + reason + " (code burned; issue a new one)")

def scan(p):
    # Reads getUpdates once and applies every pairing rule. Returns (error, burn_reason, (chat_id, username, update_id)).
    st, why, b = tg("getUpdates", {"timeout": 0, "allowed_updates": json.dumps(list(KINDS))})
    if st == 409: return "rejected: HTTP 409 webhook conflict; this token is used by a webhook elsewhere. Use a new bot; I will not call deleteWebhook.", None, None
    if st != 200: return "getUpdates failed: %s %s" % (st, why), None, None
    if len(b.get("result", [])) >= 100: return "too many unread updates on this bot (100+); use a new bot just for these alerts", None, None
    bad, chats, first = [], {}, None
    for u in sorted(b.get("result", []), key=lambda x: x.get("update_id", 0)):
        for k in KINDS:
            m = u.get(k)
            if not isinstance(m, dict): continue
            text = str(m.get("text") or m.get("caption") or "")
            c, f, d = m.get("chat", {}), m.get("from") or {}, int(m.get("date", 0))
            cid = c.get("id") if isinstance(c.get("id"), int) else 0
            private = not k.endswith("channel_post") and c.get("type") == "private" and cid > 0
            if private and first is None and d >= p["issued_at"] and text.strip().lower() != "/start":
                first = (cid, h(text) == p["code_sha256"])        # the first private message after issuance must be the code
            if h(text) != p["code_sha256"]: continue
            if not private: bad.append("group_or_channel")
            elif f.get("id") != cid or f.get("is_bot"): bad.append("sender_mismatch")
            elif d > now(): bad.append("future_timestamp")
            elif d < p["issued_at"] or d > p["expires_at"]: bad.append("outside_validity")
            else: chats.setdefault(cid, (re.sub(r"[^A-Za-z0-9_]", "", str(f.get("username", ""))), u.get("update_id")))
    if bad: return None, "code seen in a disallowed message: " + ",".join(sorted(set(bad))), None
    if len(chats) > 1: return None, "code sent from %d private chats" % len(chats), None
    if not chats: return None, None, None
    cid, (user, uid) = next(iter(chats.items()))
    if not first or first != (cid, True): return None, "the first private message after the code was issued was not the code from this chat", None
    return None, None, (cid, user, uid)

def check():
    p = load(PAIR, None)
    if not p: return print("rejected: no pairing code issued")
    if p.get("used"): return print("rejected: code already used")
    if now() > p["expires_at"]: return burn(p, "code expired")
    err, reason, m = scan(p)
    if err: return print(err if err.startswith("rejected") else "rejected: " + err)
    if reason: return burn(p, reason)
    if not m: return print("no match yet: press Start on the bot and send the code, then check again")
    cid, user, uid = m
    p["pending"] = {"chat_id": str(cid), "username": user, "update_id": uid, "matched_at": now()}; save(PAIR, p)
    print("matched: @%s, chat id ending %s. Ask the owner to confirm both the @username and the last 4 digits before saving." % (user or "(no username)", last4(cid)))

def confirm():
    p = load(PAIR, None)
    if not p or p.get("used") or not p.get("pending"): return print("rejected: nothing to confirm")
    if now() > p["expires_at"]: return burn(p, "confirmation after the code expired; start pairing again")
    err, reason, m = scan(p)                                       # re-verify right before saving
    if err: return print("not saved: re-check failed (%s); run tg-confirm again or start over" % err) or sys.exit(2)
    if reason: return burn(p, "re-check before saving: " + reason)
    pend = p["pending"]
    if not m or (str(m[0]), m[1], m[2]) != (pend["chat_id"], pend["username"], pend["update_id"]):
        return burn(p, "re-check before saving: the match changed since tg-check")
    n = load(NOTIFY, {"version": 1, "channels": {}})
    n.setdefault("channels", {})["telegram"] = {"token_env": "TELEGRAM_BOT_TOKEN", "chat_id": pend["chat_id"],
                                                "username": pend["username"], "paired_at": now()}
    save(NOTIFY, n); cid = pend["chat_id"]; p.update(used=True, pending=None); save(PAIR, p)
    print("saved: Telegram private chat ending " + last4(cid))

def send(channel):
    text, why = clean(sys.stdin.read())
    if text is None: return print("blocked by filter: %s (not sent)" % why) or sys.exit(2)
    if channel == "telegram":
        cid = str(load(NOTIFY, {}).get("channels", {}).get("telegram", {}).get("chat_id", ""))
        if not re.fullmatch(r"[1-9][0-9]{0,19}", cid): return print("not sent: no paired private chat") or sys.exit(2)
        st, why, b = tg("sendMessage", {"chat_id": cid, "text": text, "link_preview_options": json.dumps({"is_disabled": True})})
        ok = st == 200 and b.get("ok") and b.get("result", {}).get("message_id")
        ra = b.get("parameters", {}).get("retry_after") if isinstance(b.get("parameters"), dict) else None
    else:
        topic = os.environ.get("NTFY_TOPIC", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,64}", topic): return print("not sent: topic check failed") or sys.exit(2)
        req = urllib.request.Request("https://ntfy.sh/" + topic, data=text.encode(), headers={"Title": "Wallet Guardian", "Priority": "default"})
        ra = None
        try:
            with urllib.request.urlopen(req, timeout=20) as r: st, why = r.status, "ok"
        except urllib.error.HTTPError as e: st, why = e.code, "http"
        except Exception as e: st, why = None, "network_" + type(e).__name__
        ok = st == 200
    if ok: print("provider_accepted")
    elif st == 429: print("pending: rate limited" + (" retry_after=%d" % int(ra) if isinstance(ra, (int, float)) else ""))
    elif st in (400, 401, 403, 404): print("failed_permanent: HTTP %s" % st)
    elif st is None: print("unknown: %s (may or may not have arrived; not resent)" % why)
    else: print("failed: %s %s" % (st, why))

def stamp():
    # Alert time: always a numeric UTC offset (e.g. 2026-10-18 15:20 +08:00), never a zone abbreviation such as UTC or CST.
    t = time.localtime(int(sys.argv[2]) if len(sys.argv) > 2 else now())
    o = t.tm_gmtoff // 60
    print(time.strftime("%Y-%m-%d %H:%M ", t) + "%s%02d:%02d" % ("-" if o < 0 else "+", abs(o) // 60, abs(o) % 60))

RULES_NAME, SIZE_MAX, PREFIX_MAX = "wallet-guardian-rules", 512 * 1024, 8192  # frontmatter must close within 8 KiB; 512 KiB cap
NAME_KEY = re.compile(r"""\s*(["']?)name\1[ \t]*:""")             # strict name key: name:, "name":, 'name':, name :
NAME_LIKE = re.compile(r"""(?i)\s*["']?\s*name\s*["']?\s*:""")    # any name key: any case, quoting, or spacing

class Refused(Exception): pass

def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'": v = v[1:-1].strip()
    return v

def frontmatter(head, complete, what):
    # Owner's rule. No leading --- (an optional UTF-8 BOM allowed): no frontmatter, returns None (skip).
    # Otherwise the frontmatter must close with a --- line inside the first PREFIX_MAX bytes, else Refused.
    # Returns the frontmatter lines (loosely decoded; only used to find candidates).
    if head.startswith(b"\xef\xbb\xbf"): head = head[3:]
    if not head.startswith(b"---"): return None
    lines = head.decode("utf-8", errors="replace").split("\n")
    if lines[0].rstrip("\r") != "---": raise Refused("%s starts with --- but its first line is not exactly ---" % what)
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r") == "---" and (i < len(lines) - 1 or complete): return lines[1:i]
    raise Refused("%s: frontmatter not closed within 8 KiB" % what)

def strict_ok(text):
    # The one candidate: no BOM, exact --- lines, closed within 8 KiB, exactly one name key, value exactly wallet-guardian-rules.
    lines = text.split("\n")
    if lines[0] != "---": return False
    try: end = lines.index("---", 1)
    except ValueError: return False
    if len("\n".join(lines[:end + 1]).encode()) > PREFIX_MAX: return False
    names = [l for l in lines[1:end] if NAME_LIKE.match(l)]
    return len(names) == 1 and bool(NAME_KEY.match(names[0])) and unquote(names[0].split(":", 1)[1]) == RULES_NAME

def read_upto(fd, n, what):
    data = b""
    try:
        while len(data) < n:
            chunk = os.read(fd, min(65536, n - len(data)))
            if not chunk: break
            data += chunk
    except OSError as e: raise Refused("cannot read %s (%s)" % (what, e.strerror))
    return data

def snapshot(rfd, entry):
    # Returns the strict UTF-8 text of <entry>/SKILL.md if its frontmatter names wallet-guardian-rules, None if not (or absent).
    # Raises Refused when the file cannot be checked. One no-follow, non-blocking open; the prefix and the rest come from that fd.
    try: st = os.stat(entry, dir_fd=rfd, follow_symlinks=False)
    except OSError as e: raise Refused("cannot read %s (%s)" % (entry, e.strerror))
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode): return None  # symlinks and plain files are not skills
    what = "%s/SKILL.md" % entry
    dfd = fd = None
    try:
        dfd = os.open(entry, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=rfd)
        try: fst = os.stat("SKILL.md", dir_fd=dfd, follow_symlinks=False)
        except FileNotFoundError: return None
        if stat.S_ISLNK(fst.st_mode): return None
        if not stat.S_ISREG(fst.st_mode): raise Refused("%s is not a regular file (FIFO, device, or socket)" % what)
        fd = os.open("SKILL.md", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=dfd)
        if not stat.S_ISREG(os.fstat(fd).st_mode): raise Refused("%s is not a regular file (FIFO, device, or socket)" % what)
        head = read_upto(fd, PREFIX_MAX, what)
        fm = frontmatter(head, len(head) < PREFIX_MAX, what)
        if fm is None: return None
        names = [l for l in fm if NAME_LIKE.match(l)]
        if not any(unquote(l.split(":", 1)[1]).lower() == RULES_NAME for l in names): return None
        if len(names) > 1: raise Refused("suspicious copy of wallet-guardian-rules in %s (duplicate name keys); delete it, then try again" % entry)
        data = head + read_upto(fd, SIZE_MAX + 1 - len(head), what)
        if len(data) > SIZE_MAX: raise Refused("%s is a wallet-guardian-rules copy larger than the read cap" % what)
        try: return data.decode("utf-8")
        except UnicodeDecodeError: raise Refused("%s is a wallet-guardian-rules copy that is not valid UTF-8" % what)
    except OSError as e: raise Refused("cannot read %s (%s)" % (what, e.strerror))
    finally:
        for x in (fd, dfd):
            if x is not None: os.close(x)

def rules_gate():
    # Returns None when exactly one strict v1.2 copy is installed, else the refusal reason. Every check runs on one snapshot.
    try: rfd = os.open(WORKFLOWS, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as e: raise Refused("cannot read the installed skills folder (%s)" % e.strerror)
    try:
        found = []
        for entry in sorted(os.listdir(rfd)):
            txt = snapshot(rfd, entry)
            if txt is not None: found.append((entry, txt))
    finally: os.close(rfd)
    if not found: return "no installed wallet-guardian-rules skill was found"
    if len(found) > 1: return "found %d installed skills named wallet-guardian-rules; delete the extra copy (keep the v1.2 one), then try again" % len(found)
    entry, txt = found[0]
    if not strict_ok(txt): return "suspicious copy of wallet-guardian-rules in %s (frontmatter is not exactly name: wallet-guardian-rules); delete it, then try again" % entry
    if not (RULES_LINE in txt.split("\n") and R16 in txt): return "the installed wallet-guardian-rules is not v1.2 (version line or R-16 sentence missing)"
    return None

def rules_ok():
    try: return rules_gate()
    except Refused as e: return str(e)
    except Exception as e: return "rules check failed (%s)" % type(e).__name__  # fail closed

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    why = rules_ok() if cmd.startswith(("tg-", "ntfy-")) or cmd == "rules-check" else None
    if why:
        print("refused: %s; Telegram and ntfy stay off" % why)
        sys.exit(3)
    if cmd == "rules-check": print("ok: exactly one installed wallet-guardian-rules, v1.2 with R-16"); sys.exit(0)
    {"filter": lambda: print(clean(sys.stdin.read())[1]), "time": stamp, "tg-getme": getme, "tg-issue": issue, "tg-check": check,
     "tg-confirm": confirm, "tg-send": lambda: send("telegram"), "ntfy-send": lambda: send("ntfy")}.get(cmd, lambda: sys.exit("usage: rules-check|filter|time|tg-getme|tg-issue|tg-check|tg-confirm|tg-send|ntfy-send"))()

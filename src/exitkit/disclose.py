#!/usr/bin/env python3
"""Disclosure log for the report section 「這次把地址送到哪些服務」 (stdlib only).

Record EVERY outside request, including the ones made outside these scripts (Blockscout,
Sourcify, aggregator quotes, bridge APIs, protocol official APIs), BEFORE sending it:

    from exitkit.disclose import log_disclosure, import_rpc, render
    LOG = "<user-chosen temp path>/disclosure.jsonl"        # no default; the user picks it
    log_disclosure(LOG, service="Blockscout API", host="<explorer host>", endpoint="/api/v2/addresses/{addr}/tokens",
                   kind="wallet", purpose="補 token 清單")
    import_rpc(LOG, rpc, service="RPC 節點", purpose="餘額、logs、模擬")   # merge RPC.disclosure()
    print(render(LOG))                                       # markdown table for the report

kind: "wallet" (完整錢包地址) / "contract" (只有合約或其他地址) / "block" (只有區塊號或無地址) /
      "unknown" (可能含錢包地址), or the full Chinese label.
when: optional; ISO-8601 (2026-10-17, 2026-10-17T10:51:00+08:00, ...Z) or epoch seconds. Default: now.

Every field (path, service, host, endpoint, purpose, when, render's wallet_sites, and every field
of a record read back from the log) goes through the same check, after Unicode NFKC normalisation
(full-width characters become normal ones). A field is REFUSED (ValueError, nothing written) if it
contains:
  - an address (0x + 40 hex) or any hex run of 32+ chars (hash, private key, signature);
  - a long base58 / base64 / base64url blob: a token (maximal run of A-Z a-z 0-9 + / _ -) of 32+
    chars that mixes upper case, lower case and digits (in a path, each "/" part is judged on its
    own). The UNSPLIT token is checked first as standard Base64 (A-Z a-z 0-9 + / =): 32+ chars with
    upper + lower case and a digit or + / = is a blob unless every "/" part reads like a word
    (api, v2, accounts, ERC20, getTransactionCountByAddress, 2026), so "/" inside Base64 does not
    turn it into a harmless-looking path. NOT a blob: a path whose "/" parts are all under 32 chars or are identifiers, or a
    hyphen-separated identifier whose parts are all <= 12 chars and word-shaped
    (letters then optional digits, e.g. ERC20-Permit2-allowance-check-v2). Random base64url parts
    with inner case changes (aB3x...) are not word-shaped, so real secrets are still caught;
  - 12 or more consecutive BIP-39 English words (seed phrase; any separator, any case);
  - a secret keyword. English is matched on WHOLE TOKENS: the text is split into tokens on any
    non-letter/digit (space, hyphen, underscore, dot, ...) and camelCase (privKey -> priv key), and
    keyword token sequences are matched against that token sequence, so "turkey store" is not
    "keystore". Blocked: private key / priv key / privatekey / privkey, secret key, seed phrase /
    seed words, mnemonic, recovery phrase, keystore / key store, signature, signed message,
    api key / x-api-key / apikey, password / passwd / passphrase.
    Blocked only in value form (looks like a real value follows): sig= / sig: (also &sig=),
    access_token= / access-token: / auth token: (also refresh / id / session token), Bearer <value>,
    Authorization: . Bare "sig", "multi-sig", "multisig", "rotate access tokens" are allowed.
    Chinese (substring): 私鑰 私钥 助記詞 助记词 註記詞 種子 恢復短語 簽名 签名 金鑰 密鑰 密钥 密碼 ...
The log contains hosts and data kinds only (never the address itself, keys, or signatures),
but it still shows which services were used: keep it in a temp folder and delete it after use.

CLI (exit 2 and nothing written when a field is refused):
  exitkit disclose add    --log PATH --service S --host H --endpoint E --kind wallet --purpose P [--when T]
  exitkit disclose import --log PATH --disclosure-json FILE
  exitkit disclose render --log PATH [--wallet-site DOMAIN]...
"""
import argparse, datetime, hashlib, json, os, re, sys, unicodedata
from exitkit.rpc import KIND_WALLET, KIND_CONTRACT, KIND_BLOCK, KIND_UNREG, _KIND_RANK

KINDS = {"wallet": KIND_WALLET, "contract": KIND_CONTRACT, "block": KIND_BLOCK, "unknown": KIND_UNREG}
MAX_LEN = 500

# Official BIP-39 English wordlist (bitcoin/bips bip-0039/english.txt, 2048 words).
# Checked at import: count, first/last word and sha256 of the original file.
# (split in two halves only so the 64-hex privacy check does not flag this public constant)
BIP39_SHA256 = "2f5eed53a4727b4bf8880d8f3f199efc" + "90e58503646d9ff8eff3a2ed3b24dbda"
_BIP39_TEXT = """
abandon ability able about above absent absorb abstract absurd abuse access accident account
accuse achieve acid acoustic acquire across act action actor actress actual adapt add addict
address adjust admit adult advance advice aerobic affair afford afraid again age agent agree
ahead aim air airport aisle alarm album alcohol alert alien all alley allow almost alone alpha
already also alter always amateur amazing among amount amused analyst anchor ancient anger angle
angry animal ankle announce annual another answer antenna antique anxiety any apart apology
appear apple approve april arch arctic area arena argue arm armed armor army around arrange
arrest arrive arrow art artefact artist artwork ask aspect assault asset assist assume asthma
athlete atom attack attend attitude attract auction audit august aunt author auto autumn average
avocado avoid awake aware away awesome awful awkward axis baby bachelor bacon badge bag balance
balcony ball bamboo banana banner bar barely bargain barrel base basic basket battle beach bean
beauty because become beef before begin behave behind believe below belt bench benefit best
betray better between beyond bicycle bid bike bind biology bird birth bitter black blade blame
blanket blast bleak bless blind blood blossom blouse blue blur blush board boat body boil bomb
bone bonus book boost border boring borrow boss bottom bounce box boy bracket brain brand brass
brave bread breeze brick bridge brief bright bring brisk broccoli broken bronze broom brother
brown brush bubble buddy budget buffalo build bulb bulk bullet bundle bunker burden burger burst
bus business busy butter buyer buzz cabbage cabin cable cactus cage cake call calm camera camp
can canal cancel candy cannon canoe canvas canyon capable capital captain car carbon card cargo
carpet carry cart case cash casino castle casual cat catalog catch category cattle caught cause
caution cave ceiling celery cement census century cereal certain chair chalk champion change
chaos chapter charge chase chat cheap check cheese chef cherry chest chicken chief child chimney
choice choose chronic chuckle chunk churn cigar cinnamon circle citizen city civil claim clap
clarify claw clay clean clerk clever click client cliff climb clinic clip clock clog close cloth
cloud clown club clump cluster clutch coach coast coconut code coffee coil coin collect color
column combine come comfort comic common company concert conduct confirm congress connect
consider control convince cook cool copper copy coral core corn correct cost cotton couch
country couple course cousin cover coyote crack cradle craft cram crane crash crater crawl crazy
cream credit creek crew cricket crime crisp critic crop cross crouch crowd crucial cruel cruise
crumble crunch crush cry crystal cube culture cup cupboard curious current curtain curve cushion
custom cute cycle dad damage damp dance danger daring dash daughter dawn day deal debate debris
decade december decide decline decorate decrease deer defense define defy degree delay deliver
demand demise denial dentist deny depart depend deposit depth deputy derive describe desert
design desk despair destroy detail detect develop device devote diagram dial diamond diary dice
diesel diet differ digital dignity dilemma dinner dinosaur direct dirt disagree discover disease
dish dismiss disorder display distance divert divide divorce dizzy doctor document dog doll
dolphin domain donate donkey donor door dose double dove draft dragon drama drastic draw dream
dress drift drill drink drip drive drop drum dry duck dumb dune during dust dutch duty dwarf
dynamic eager eagle early earn earth easily east easy echo ecology economy edge edit educate
effort egg eight either elbow elder electric elegant element elephant elevator elite else embark
embody embrace emerge emotion employ empower empty enable enact end endless endorse enemy energy
enforce engage engine enhance enjoy enlist enough enrich enroll ensure enter entire entry
envelope episode equal equip era erase erode erosion error erupt escape essay essence estate
eternal ethics evidence evil evoke evolve exact example excess exchange excite exclude excuse
execute exercise exhaust exhibit exile exist exit exotic expand expect expire explain expose
express extend extra eye eyebrow fabric face faculty fade faint faith fall false fame family
famous fan fancy fantasy farm fashion fat fatal father fatigue fault favorite feature february
federal fee feed feel female fence festival fetch fever few fiber fiction field figure file film
filter final find fine finger finish fire firm first fiscal fish fit fitness fix flag flame
flash flat flavor flee flight flip float flock floor flower fluid flush fly foam focus fog foil
fold follow food foot force forest forget fork fortune forum forward fossil foster found fox
fragile frame frequent fresh friend fringe frog front frost frown frozen fruit fuel fun funny
furnace fury future gadget gain galaxy gallery game gap garage garbage garden garlic garment gas
gasp gate gather gauge gaze general genius genre gentle genuine gesture ghost giant gift giggle
ginger giraffe girl give glad glance glare glass glide glimpse globe gloom glory glove glow glue
goat goddess gold good goose gorilla gospel gossip govern gown grab grace grain grant grape
grass gravity great green grid grief grit grocery group grow grunt guard guess guide guilt
guitar gun gym habit hair half hammer hamster hand happy harbor hard harsh harvest hat have hawk
hazard head health heart heavy hedgehog height hello helmet help hen hero hidden high hill hint
hip hire history hobby hockey hold hole holiday hollow home honey hood hope horn horror horse
hospital host hotel hour hover hub huge human humble humor hundred hungry hunt hurdle hurry hurt
husband hybrid ice icon idea identify idle ignore ill illegal illness image imitate immense
immune impact impose improve impulse inch include income increase index indicate indoor industry
infant inflict inform inhale inherit initial inject injury inmate inner innocent input inquiry
insane insect inside inspire install intact interest into invest invite involve iron island
isolate issue item ivory jacket jaguar jar jazz jealous jeans jelly jewel job join joke journey
joy judge juice jump jungle junior junk just kangaroo keen keep ketchup key kick kid kidney kind
kingdom kiss kit kitchen kite kitten kiwi knee knife knock know lab label labor ladder lady lake
lamp language laptop large later latin laugh laundry lava law lawn lawsuit layer lazy leader
leaf learn leave lecture left leg legal legend leisure lemon lend length lens leopard lesson
letter level liar liberty library license life lift light like limb limit link lion liquid list
little live lizard load loan lobster local lock logic lonely long loop lottery loud lounge love
loyal lucky luggage lumber lunar lunch luxury lyrics machine mad magic magnet maid mail main
major make mammal man manage mandate mango mansion manual maple marble march margin marine
market marriage mask mass master match material math matrix matter maximum maze meadow mean
measure meat mechanic medal media melody melt member memory mention menu mercy merge merit merry
mesh message metal method middle midnight milk million mimic mind minimum minor minute miracle
mirror misery miss mistake mix mixed mixture mobile model modify mom moment monitor monkey
monster month moon moral more morning mosquito mother motion motor mountain mouse move movie
much muffin mule multiply muscle museum mushroom music must mutual myself mystery myth naive
name napkin narrow nasty nation nature near neck need negative neglect neither nephew nerve nest
net network neutral never news next nice night noble noise nominee noodle normal north nose
notable note nothing notice novel now nuclear number nurse nut oak obey object oblige obscure
observe obtain obvious occur ocean october odor off offer office often oil okay old olive
olympic omit once one onion online only open opera opinion oppose option orange orbit orchard
order ordinary organ orient original orphan ostrich other outdoor outer output outside oval oven
over own owner oxygen oyster ozone pact paddle page pair palace palm panda panel panic panther
paper parade parent park parrot party pass patch path patient patrol pattern pause pave payment
peace peanut pear peasant pelican pen penalty pencil people pepper perfect permit person pet
phone photo phrase physical piano picnic picture piece pig pigeon pill pilot pink pioneer pipe
pistol pitch pizza place planet plastic plate play please pledge pluck plug plunge poem poet
point polar pole police pond pony pool popular portion position possible post potato pottery
poverty powder power practice praise predict prefer prepare present pretty prevent price pride
primary print priority prison private prize problem process produce profit program project
promote proof property prosper protect proud provide public pudding pull pulp pulse pumpkin
punch pupil puppy purchase purity purpose purse push put puzzle pyramid quality quantum quarter
question quick quit quiz quote rabbit raccoon race rack radar radio rail rain raise rally ramp
ranch random range rapid rare rate rather raven raw razor ready real reason rebel rebuild recall
receive recipe record recycle reduce reflect reform refuse region regret regular reject relax
release relief rely remain remember remind remove render renew rent reopen repair repeat replace
report require rescue resemble resist resource response result retire retreat return reunion
reveal review reward rhythm rib ribbon rice rich ride ridge rifle right rigid ring riot ripple
risk ritual rival river road roast robot robust rocket romance roof rookie room rose rotate
rough round route royal rubber rude rug rule run runway rural sad saddle sadness safe sail salad
salmon salon salt salute same sample sand satisfy satoshi sauce sausage save say scale scan
scare scatter scene scheme school science scissors scorpion scout scrap screen script scrub sea
search season seat second secret section security seed seek segment select sell seminar senior
sense sentence series service session settle setup seven shadow shaft shallow share shed shell
sheriff shield shift shine ship shiver shock shoe shoot shop short shoulder shove shrimp shrug
shuffle shy sibling sick side siege sight sign silent silk silly silver similar simple since
sing siren sister situate six size skate sketch ski skill skin skirt skull slab slam sleep
slender slice slide slight slim slogan slot slow slush small smart smile smoke smooth snack
snake snap sniff snow soap soccer social sock soda soft solar soldier solid solution solve
someone song soon sorry sort soul sound soup source south space spare spatial spawn speak
special speed spell spend sphere spice spider spike spin spirit split spoil sponsor spoon sport
spot spray spread spring spy square squeeze squirrel stable stadium staff stage stairs stamp
stand start state stay steak steel stem step stereo stick still sting stock stomach stone stool
story stove strategy street strike strong struggle student stuff stumble style subject submit
subway success such sudden suffer sugar suggest suit summer sun sunny sunset super supply
supreme sure surface surge surprise surround survey suspect sustain swallow swamp swap swarm
swear sweet swift swim swing switch sword symbol symptom syrup system table tackle tag tail
talent talk tank tape target task taste tattoo taxi teach team tell ten tenant tennis tent term
test text thank that theme then theory there they thing this thought three thrive throw thumb
thunder ticket tide tiger tilt timber time tiny tip tired tissue title toast tobacco today
toddler toe together toilet token tomato tomorrow tone tongue tonight tool tooth top topic
topple torch tornado tortoise toss total tourist toward tower town toy track trade traffic
tragic train transfer trap trash travel tray treat tree trend trial tribe trick trigger trim
trip trophy trouble truck true truly trumpet trust truth try tube tuition tumble tuna tunnel
turkey turn turtle twelve twenty twice twin twist two type typical ugly umbrella unable unaware
uncle uncover under undo unfair unfold unhappy uniform unique unit universe unknown unlock until
unusual unveil update upgrade uphold upon upper upset urban urge usage use used useful useless
usual utility vacant vacuum vague valid valley valve van vanish vapor various vast vault vehicle
velvet vendor venture venue verb verify version very vessel veteran viable vibrant vicious
victory video view village vintage violin virtual virus visa visit visual vital vivid vocal
voice void volcano volume vote voyage wage wagon wait walk wall walnut want warfare warm warrior
wash wasp waste water wave way wealth weapon wear weasel weather web wedding weekend weird
welcome west wet whale what wheat wheel when where whip whisper wide width wife wild will win
window wine wing wink winner winter wire wisdom wise wish witness wolf woman wonder wood wool
word work world worry worth wrap wreck wrestle wrist write wrong yard year yellow you young
youth zebra zero zone zoo
"""
_BIP39 = _BIP39_TEXT.split()
if (len(_BIP39) != 2048 or _BIP39[0] != "abandon" or _BIP39[-1] != "zoo" or
        hashlib.sha256(("\n".join(_BIP39) + "\n").encode()).hexdigest() != BIP39_SHA256):
    raise RuntimeError("embedded BIP-39 wordlist is damaged")
BIP39 = frozenset(_BIP39)
MNEMONIC_MIN_RUN = 12      # 12/15/18/21/24-word phrases, and anything longer

# English keywords as TOKEN sequences (matched against the space-joined token list, see _tokens)
_TOKEN_KEYWORDS = [
    ("private key", r"(?:private|priv) keys?|privatekeys?\d*|privkeys?\d*"),
    ("secret key", r"secret keys?|secretkeys?\d*"),
    ("seed phrase", r"seed (?:phrases?|words?)|seedphrases?"),
    ("mnemonic", r"mnemonics?"),
    ("recovery phrase", r"recovery (?:phrases?|words?|seed)|recoveryphrases?"),
    ("keystore", r"keystores?|key stores?"),
    ("signature", r"signatures?"),
    ("signed message", r"signed (?:messages?|msg|data|tx)"),
    ("api key", r"(?:x )?api keys?|x?apikeys?\d*"),
    ("password", r"passwords?|passwd|passphrases?|pass (?:words?|phrase)"),
]
_TOKEN_KEYWORDS = [(n, re.compile(r"(?<!\S)(?:" + p + r")(?!\S)")) for n, p in _TOKEN_KEYWORDS]
# value forms: a real value seems to follow (checked on the lower-cased NFKC text)
_VALUE_KEYWORDS = [
    ("sig=", r"(?<![a-z0-9])sigs?\s*[=:]"),
    ("access token value", r"(?<![a-z0-9])(?:access|auth|refresh|id|session)[\s_\-.]*tokens?\s*[=:]"),
    ("bearer value", r"(?<![a-z0-9])bearer\s+[a-z0-9\-._~+/]+"),
    ("authorization header", r"(?<![a-z0-9])authorization\s*[=:]"),
]
_VALUE_KEYWORDS = [(n, re.compile(p)) for n, p in _VALUE_KEYWORDS]
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_ZH_WORDS = ("私鑰", "私钥", "助記詞", "助记词", "註記詞", "注记词", "種子", "种子", "恢復短語", "恢复短语",
             "簽名", "签名", "金鑰", "密鑰", "密钥", "密碼", "密码", "口令")
_HEX = re.compile(r"(?:0x)?[0-9a-f]{32,}")
_ADDR = re.compile(r"0x[0-9a-f]{40}")
_BLOB = re.compile(r"[A-Za-z0-9+/_\-]{32,}={0,2}")
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:?\d{2})?)?")


def _norm(v):
    return unicodedata.normalize("NFKC", str(v))


_WORDY = re.compile(r"[a-z]+[0-9]*|[A-Z][a-z]*[0-9]*|[A-Z]+[0-9]*|[0-9]+")


def _part_blob(p):
    if len(p) < 32 or not (re.search(r"[A-Z]", p) and re.search(r"[a-z]", p) and re.search(r"[0-9]", p)):
        return False          # needs 32+ chars mixing upper + lower + digits
    segs = p.split("-")
    if len(segs) > 1 and all(0 < len(x) <= 12 and _WORDY.fullmatch(x) for x in segs):
        return False          # identifier such as ERC20-Permit2-allowance-check-v2
    return True


_B64STD = re.compile(r"[A-Za-z0-9+/]+={0,2}")
# one path segment that reads like words: api, v2, accounts, ERC20, getTransactionCountByAddress, 2026
_PATHWORD = re.compile(r"(?:[a-z]{2,}|[A-Z][a-z]+|[A-Z]{2,})[0-9]*(?:[A-Z][a-z]+[0-9]*)*|[a-z]{1,2}[0-9]*|[0-9]+")


def _path_like(tok):
    segs = tok.strip("/").split("/")
    return all(x and _PATHWORD.fullmatch(x) for x in segs)


def _whole_b64(tok):
    """The UNSPLIT token as standard Base64 (A-Z a-z 0-9 + / and = padding): 32+ chars, upper and
    lower case, and a digit or + / = . Only a token whose every '/' part reads like a word is
    treated as a path instead (so '/' inside Base64 can no longer split it into short parts)."""
    if len(tok) < 32 or not _B64STD.fullmatch(tok):
        return False
    if not (re.search(r"[A-Z]", tok) and re.search(r"[a-z]", tok) and re.search(r"[0-9+/=]", tok)):
        return False
    return not _path_like(tok)


def _is_blob(tok):
    if _whole_b64(tok):       # whole-token check first (standard Base64 with '/', '+', '=')
        return True
    if "/" in tok and all(len(p) < 32 for p in tok.split("/")):
        return False          # an ordinary path such as /api/v2/addresses
    if "/" in tok:            # path: judge each part (/docs/<identifier> is fine, /verify/<blob> is not)
        return any(_part_blob(p) for p in tok.split("/"))
    return _part_blob(tok)


def _tokens(s):
    """Lower-case word tokens: split on any non-letter/digit and on camelCase."""
    return re.findall(r"[a-z0-9]+", _CAMEL.sub(" ", s).lower())


def _mnemonic_run(text):
    """Longest run of consecutive BIP-39 words (any non-letter is a separator)."""
    best = cur = 0
    for w in re.split(r"[^a-z]+", text.lower()):
        if not w:
            continue
        cur = cur + 1 if w in BIP39 else 0
        best = max(best, cur)
    return best


def check_field(field, v):
    """Raise ValueError if the value may hold an address or a secret. Checks run on the NFKC form;
    the original text is returned (and stored). The message never repeats the value."""
    if v is None:
        raise ValueError(f"{field}: missing")
    s = _norm(v)
    low = s.lower()
    if not s.strip():
        raise ValueError(f"{field}: empty")
    if len(s) > MAX_LEN:
        raise ValueError(f"{field}: too long ({len(s)} > {MAX_LEN} chars)")
    if any(unicodedata.category(c) in ("Cc", "Cf") for c in s):
        raise ValueError(f"{field}: control / invisible characters are not allowed")
    if _ADDR.search(low) or _HEX.search(low):
        raise ValueError(f"{field}: do not write addresses / hashes / keys / signatures into the log; "
                         "use a placeholder like {addr}")
    if any(_is_blob(m.group(0)) for m in _BLOB.finditer(s)):
        raise ValueError(f"{field}: long encoded blob (base58 / base64) may be a key or signature; refused")
    if _mnemonic_run(low) >= MNEMONIC_MIN_RUN:
        raise ValueError(f"{field}: looks like a seed phrase (12+ BIP-39 words in a row); never send or log it")
    joined = " ".join(_tokens(s))
    hits = [n for n, rx in _TOKEN_KEYWORDS if rx.search(joined)] + [n for n, rx in _VALUE_KEYWORDS if rx.search(low)]
    for name in hits[:1]:
        raise ValueError(f"{field}: secret keyword ({name}); keys, seed phrases, API keys, passwords and "
                             "signatures must never be sent or logged")
    for w in _ZH_WORDS:
        if w in s:
            raise ValueError(f"{field}: secret keyword ({w}); 私鑰、助記詞、金鑰、簽名、密碼一律不能送出或寫進紀錄")
    return str(v)


def _host(v):
    s = check_field("host", v)
    if re.search(r"[\s/@?#]", _norm(s)):
        raise ValueError("host: only a domain or host:port (no path, query, user@ or spaces)")
    return s


def _when(v):
    if v is None:
        return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if isinstance(v, bool):
        raise ValueError("when: must be ISO-8601 text or epoch seconds")
    if isinstance(v, (int, float)) or (isinstance(v, str) and re.fullmatch(r"\d{9,10}(?:\.\d{1,6})?", _norm(v).strip())):
        x = float(_norm(v)) if isinstance(v, str) else float(v)
        if not 0 <= x < 1e10:
            raise ValueError("when: epoch seconds out of range")
        return datetime.datetime.fromtimestamp(x).astimezone().isoformat(timespec="seconds")
    s = check_field("when", v).strip()
    if not _ISO.fullmatch(s):
        raise ValueError("when: must be ISO-8601 (e.g. 2026-10-17T10:51:00+08:00) or epoch seconds")
    try:
        datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("when: not a real date/time") from None
    return s


_KIND_BY_NORM = {_norm(v): v for v in KINDS.values()}


def _kind(k):
    k = _norm(k).strip() if isinstance(k, str) else k
    if k in KINDS: return KINDS[k]
    if k in _KIND_BY_NORM: return _KIND_BY_NORM[k]
    raise ValueError(f"kind must be one of {list(KINDS)} (got a value that is not allowed)")


def _record(service, host, endpoint, kind, purpose, when):
    return {"time": _when(when), "service": check_field("service", service), "host": _host(host),
            "endpoint": check_field("endpoint", endpoint), "kind": _kind(kind),
            "purpose": check_field("purpose", purpose)}


def log_disclosure(path, service, host, endpoint, kind, purpose, when=None):
    """Append one record (JSONL). Call it BEFORE the request is sent. Every field is checked first;
    on any problem a ValueError is raised and nothing is written."""
    if not path:
        raise ValueError("path is required (a temp path the user chose)")
    check_field("path", path)
    rec = _record(service, host, endpoint, kind, purpose, when)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def import_disclosure(path, disclosure, service="RPC 節點", purpose="鏈上讀取／模擬"):
    """Merge a disclosure() object (one record per host and data kind). All records are
    checked before the first one is written."""
    if not isinstance(disclosure, dict):
        raise ValueError("disclosure: expected an object")
    recs = []
    for host, d in disclosure.items():
        if not isinstance(d, dict) or "methods" not in d or "sent" not in d or "chain_id_verified" not in d:
            raise ValueError("disclosure: each host needs methods, sent, and chain_id_verified")
        for kind in d["sent"]:
            note = "" if d["chain_id_verified"] else "（chainId 未驗證）"
            recs.append((service, host, "JSON-RPC " + ",".join(d["methods"]), kind, purpose + note))
    for r in recs:
        _record(*r, None)
    for r in recs:
        log_disclosure(path, *r)
    return len(recs)


def import_rpc(path, rpc, service="RPC 節點", purpose="鏈上讀取／模擬"):
    """Merge an RPC object's disclosure() (one record per host and data kind). All records are
    checked before the first one is written."""
    return import_disclosure(path, rpc.disclosure(), service, purpose)


_FIELDS = {"time", "service", "host", "endpoint", "kind", "purpose"}


def load(path):
    """Read the log back; every record is re-checked (a hand-edited log cannot smuggle secrets)."""
    if not path:
        raise ValueError("path is required")
    check_field("path", path)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for n, l in enumerate(f, 1):
            if not l.strip():
                continue
            r = json.loads(l)
            if not isinstance(r, dict) or set(r) != _FIELDS:
                raise ValueError(f"log line {n}: unexpected fields")
            _record(r["service"], r["host"], r["endpoint"], r["kind"], r["purpose"], r["time"])
            out.append(r)
    return out


def render(path, wallet_sites=()):
    """Markdown for 「這次把地址送到哪些服務」. wallet_sites: domains the user will connect a wallet to."""
    sites = [_host(s) for s in wallet_sites]
    rows = {}
    for r in load(path):
        k = (r["service"], r["host"], r["endpoint"])
        e = rows.setdefault(k, {"kinds": set(), "purposes": set()})
        e["kinds"].add(r["kind"]); e["purposes"].add(r["purpose"])
    out = ["這次把地址送到哪些服務：", "", "| 服務 | 網域 | 端點 | 送了什麼 | 用途 |", "|---|---|---|---|---|"]
    if not rows:
        out.append("| （沒有紀錄） | | | | |")
    for (svc, host, ep), e in sorted(rows.items(), key=lambda x: (-max(_KIND_RANK[k] for k in x[1]["kinds"]), x[0])):
        kinds = "、".join(sorted(e["kinds"], key=lambda k: -_KIND_RANK[k]))
        out.append(f"| {svc} | {host} | {ep} | {kinds} | {'、'.join(sorted(e['purposes']))} |")
    for site in sites:
        out.append(f"| 你連錢包的網站 | {site} | 連錢包 | {KIND_WALLET}（連上錢包就會把地址交給那個網站） | 你自己簽交易 |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="exitkit disclose")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("add")
    for k in ("log", "service", "host", "endpoint", "kind", "purpose"):
        a1.add_argument("--" + k, required=True)
    a1.add_argument("--when", default=None, help="ISO-8601 or epoch seconds; default now")
    a3 = sub.add_parser("import")
    a3.add_argument("--log", required=True)
    a3.add_argument("--disclosure-json", required=True, help="JSON object from RPC.disclosure()")
    a3.add_argument("--service", default="RPC 節點")
    a3.add_argument("--purpose", default="鏈上讀取／模擬")
    a2 = sub.add_parser("render")
    a2.add_argument("--log", required=True)
    a2.add_argument("--wallet-site", action="append", default=[])
    a = ap.parse_args(argv)
    try:
        if a.cmd == "add":
            print(json.dumps(log_disclosure(a.log, a.service, a.host, a.endpoint, a.kind, a.purpose, a.when),
                             ensure_ascii=False))
        elif a.cmd == "import":
            with open(a.disclosure_json, encoding="utf-8") as f:
                disclosure = json.load(f)
            n = import_disclosure(a.log, disclosure, a.service, a.purpose)
            print(json.dumps({"imported": n}, ensure_ascii=False))
        else:
            print(render(a.log, a.wallet_site))
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

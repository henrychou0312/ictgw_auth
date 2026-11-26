"""Command-line login for the ICT campus network (SRun portal at gw.ict.ac.cn)."""

import base64
import getpass
import hashlib
import hmac
import json
import sys
import time
import urllib.parse
import urllib.request

PORTAL = "https://gw.ict.ac.cn"
AC_ID = "1"
N, TYPE, ENC = "200", "1", "srun_bx1"
ALPHA = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"
STD_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
MASK = 0xFFFFFFFF

# Talk to the portal directly, ignoring any http(s)_proxy settings.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(path, **params):
    """Call a JSONP endpoint of the portal and return the decoded JSON."""
    params.update(callback="cb", _=int(time.time() * 1000))
    url = PORTAL + path + "?" + urllib.parse.urlencode(params)
    with _opener.open(url, timeout=10) as resp:
        text = resp.read().decode("utf-8")
    return json.loads(text[text.index("(") + 1 : text.rindex(")")])


# ---------------------------------------------------------------- SRun crypto
def _to_words(s, with_len):
    v = [0] * ((len(s) + 3) // 4)
    for i, ch in enumerate(s):
        v[i >> 2] = (v[i >> 2] | (ord(ch) << (8 * (i & 3)))) & MASK
    if with_len:
        v.append(len(s))
    return v


def _from_words(v):
    return "".join(
        chr(w & 0xFF) + chr(w >> 8 & 0xFF) + chr(w >> 16 & 0xFF) + chr(w >> 24 & 0xFF)
        for w in v
    )


def x_encode(msg, key):
    """XXTEA variant used by SRun (``encode`` in Portal.js)."""
    if not msg:
        return ""
    v, k = _to_words(msg, True), _to_words(key, False)
    k += [0] * (4 - len(k))
    n = len(v) - 1
    z, d = v[n], 0
    for _ in range(6 + 52 // (n + 1)):
        d = (d + 0x9E3779B9) & MASK
        e = d >> 2 & 3
        for p in range(n + 1):
            y = v[(p + 1) % (n + 1)]
            m = (z >> 5 ^ y << 2) + ((y >> 3 ^ z << 4) ^ (d ^ y)) + (k[p & 3 ^ e] ^ z)
            z = v[p] = (v[p] + m) & MASK
    return _from_words(v)


def encode_info(info, token):
    raw = x_encode(json.dumps(info, separators=(",", ":"), ensure_ascii=False), token)
    b64 = base64.b64encode(raw.encode("latin-1")).decode()
    return "{SRBX1}" + b64.translate(str.maketrans(STD_ALPHA, ALPHA))


# ------------------------------------------------------------------- actions
def login(username, password):
    challenge = api("/cgi-bin/get_challenge", username=username, ip="")
    token, ip = challenge["challenge"], challenge["client_ip"]
    hmd5 = hmac.new(token.encode(), password.encode(), hashlib.md5).hexdigest()
    info = encode_info(
        {"username": username, "password": password, "ip": ip, "acid": AC_ID, "enc_ver": ENC},
        token,
    )
    chksum = token.join(["", username, hmd5, AC_ID, ip, N, TYPE, info])
    res = api(
        "/cgi-bin/srun_portal",
        action="login",
        username=username,
        password="{MD5}" + hmd5,
        os="Linux",
        name="Linux",
        double_stack=0,
        chksum=hashlib.sha1(chksum.encode()).hexdigest(),
        info=info,
        ac_id=AC_ID,
        ip=ip,
        n=N,
        type=TYPE,
    )
    return res.get("error") == "ok", res


def logout(username, ip):
    res = api("/cgi-bin/srun_portal", action="logout", username=username, ip=ip, ac_id=AC_ID)
    return res.get("error") == "ok", res


def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "{:.2f} {}".format(n, unit)
        n /= 1024
    return "{:.2f} TB".format(n)


def show(info):
    secs = int(info.get("sum_seconds", 0))
    print("  User      : {}".format(info.get("user_name", "")))
    print("  IP        : {}".format(info.get("online_ip", "")))
    print("  Used flow : {}".format(human_bytes(int(info.get("sum_bytes", 0)))))
    print("  Used time : {}h {}m".format(secs // 3600, secs % 3600 // 60))


def error_text(res):
    return res.get("error_msg") or res.get("suc_msg") or res.get("error") or str(res)


def main():
    try:
        status = api("/cgi-bin/rad_user_info")
        if status.get("error") == "ok":
            print("Status: Online")
            show(status)
            if input("Log out? [y/N] ").strip().lower() not in ("y", "yes"):
                return 0
            ok, res = logout(status["user_name"], status["online_ip"])
            print("Logout successful." if ok else "Logout failed: " + error_text(res))
            return 0 if ok else 1

        print("Status: Offline")
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")
        ok, res = login(username, password)
        if not ok:
            print("Login failed: " + error_text(res))
            return 1
        print("Login successful.")
        status = api("/cgi-bin/rad_user_info")
        if status.get("error") == "ok":
            show(status)
        return 0
    except KeyboardInterrupt:
        print()
        return 130
    except (OSError, ValueError, KeyError) as e:
        print("Error: cannot talk to {}: {}".format(PORTAL, e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

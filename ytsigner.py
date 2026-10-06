import os
import io
import re
import sys
import json
import time
import socket
import asyncio
import traceback
import subprocess
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PORT = 8000


def kill_port(port: int) -> None:
    try:
        out = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception:
        return
    pids = set()
    for line in out.splitlines():
        if f":{port} " in line and "LISTENING" in line:
            parts = line.split()
            if parts:
                pid = parts[-1].strip()
                if pid.isdigit() and int(pid) != 0:
                    pids.add(pid)
    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/PID", pid, "/F"],
                capture_output=True, text=True, timeout=10,
            )
            print(f"[patcher] killed PID {pid} holding port {port}", flush=True)
        except Exception:
            pass
    time.sleep(0.4)


def port_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


app = FastAPI(title="IPA Patcher")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()  # never hardcode a token here; export it in your shell
WORKFLOW_REPO = (os.environ.get("WORKFLOW_REPO") or "thecloudyy/Youtube-Premium-2.0-IPA").strip()
WORKFLOW_FILE = (os.environ.get("WORKFLOW_FILE") or "ipa.yml").strip()
WORKFLOW_REF  = (os.environ.get("WORKFLOW_REF")  or "main").strip()

CLEANUP_RUNS_FILE = (os.environ.get("CLEANUP_RUNS_FILE") or "delete-old-workflows-run.yml").strip()
CLEANUP_RELEASES_FILE = (os.environ.get("CLEANUP_RELEASES_FILE") or "delete-old-draft-releases.yml").strip()

DROPSTONE_URL = "https://dropstone.lovable.app/d/ytipa"
GH_API = "https://api.github.com"

TWEAK_FLAGS = [
    "youpip", "ytuhd", "ryd", "abconfig", "youquality", "demc",
    "ytweaks", "youslider", "gonerino", "ytshare", "volboost",
]


class BuildRequest(BaseModel):
    repo: str = Field(default="thecloudyy/Youtube-Premium-2.0-IPA")
    branch: str = Field(default="main")
    ipa_url: str = Field(default="")
    display_name: str = Field(default="YouTube")
    bundle_id: str = Field(default="com.google.ios.youtube")
    tweaks: dict = Field(default_factory=lambda: {k: True for k in TWEAK_FLAGS})


class BuildStatus(BaseModel):
    run_id: int
    status: str
    conclusion: Optional[str] = None
    html_url: str
    release_url: Optional[str] = None
    ipa_url: Optional[str] = None


def gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def log(msg: str) -> None:
    print(f"[patcher] {msg}", flush=True)


async def dispatch_workflow(req: BuildRequest) -> dict:
    inputs = {
        "repo": req.repo,
        "branch": req.branch,
        "ipa_url": req.ipa_url,
        "display_name": req.display_name,
        "bundle_id": req.bundle_id,
    }
    for k in TWEAK_FLAGS:
        inputs[k] = str(bool(req.tweaks.get(k, True))).lower()

    url = f"{GH_API}/repos/{WORKFLOW_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    log(f"POST {url}")
    log(f"  ref={WORKFLOW_REF}  token_len={len(GITHUB_TOKEN)} token_prefix={GITHUB_TOKEN[:7]!r}")

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(url, headers=gh_headers(),
                         json={"ref": WORKFLOW_REF, "inputs": inputs})

    log(f"  <- {r.status_code} {r.text[:400]!r}")

    if r.status_code not in (204, 201):
        raise HTTPException(502, f"dispatch failed ({r.status_code}): {r.text[:600]}")
    return {"ok": True}


async def dispatch_simple(workflow_file: str) -> None:
    url = f"{GH_API}/repos/{WORKFLOW_REPO}/actions/workflows/{workflow_file}/dispatches"
    log(f"POST {url}")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(url, headers=gh_headers(), json={"ref": WORKFLOW_REF})
    log(f"  <- {r.status_code} {r.text[:400]!r}")
    if r.status_code not in (204, 201):
        raise HTTPException(502, f"dispatch failed ({r.status_code}): {r.text[:600]}")


async def find_latest_run() -> Optional[dict]:
    url = f"{GH_API}/repos/{WORKFLOW_REPO}/actions/workflows/{WORKFLOW_FILE}/runs"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, headers=gh_headers(), params={"per_page": 1})
        if r.status_code != 200:
            log(f"find_latest_run <- {r.status_code} {r.text[:200]!r}")
            return None
        runs = r.json().get("workflow_runs", [])
        return runs[0] if runs else None


async def find_draft_release(run_number: int) -> Optional[dict]:
    # NOTE: GET /releases/tags/{tag} returns 404 for *draft* releases,
    # so list releases (token sees drafts) and match by tag instead.
    tag = f"youmod-ipa{run_number}"
    url = f"{GH_API}/repos/{WORKFLOW_REPO}/releases"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, headers=gh_headers(), params={"per_page": 30})
        if r.status_code != 200:
            return None
        for rel in r.json():
            if rel.get("tag_name") == tag:
                return rel
    return None


def pick_ipa_asset(release: dict) -> Optional[str]:
    for a in release.get("assets", []):
        if a["name"].lower().endswith(".ipa"):
            return a.get("browser_download_url")
    return None


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/api/debug")
async def debug():
    tok = GITHUB_TOKEN
    out = {
        "token_set": bool(tok),
        "token_len": len(tok),
        "token_prefix": tok[:7] if tok else "",
        "token_suffix": tok[-4:] if tok else "",
        "token_has_whitespace": tok != tok.strip(),
        "workflow_repo": WORKFLOW_REPO,
        "workflow_file": WORKFLOW_FILE,
        "workflow_ref": WORKFLOW_REF,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{GH_API}/user", headers=gh_headers())
            out["whoami_status"] = r.status_code
            if r.status_code == 200:
                out["whoami_login"] = r.json().get("login")
            else:
                out["whoami_body"] = r.text[:200]
            out["oauth_scopes"] = r.headers.get("x-oauth-scopes", "")
    except Exception as e:
        out["whoami_error"] = str(e)
    return out


@app.post("/api/cleanup/runs")
async def cleanup_runs():
    await dispatch_simple(CLEANUP_RUNS_FILE)
    return {"ok": True, "workflow": CLEANUP_RUNS_FILE}


@app.post("/api/cleanup/releases")
async def cleanup_releases():
    await dispatch_simple(CLEANUP_RELEASES_FILE)
    return {"ok": True, "workflow": CLEANUP_RELEASES_FILE}


@app.post("/api/build", response_model=BuildStatus)
async def build(req: BuildRequest):
    if not GITHUB_TOKEN:
        raise HTTPException(500, "GITHUB_TOKEN not set on the server")
    if not req.ipa_url:
        req.ipa_url = DROPSTONE_URL
    try:
        await dispatch_workflow(req)
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()[-800:]
        log(tb)
        raise HTTPException(500, f"dispatch crashed: {e}\n{tb}")

    await asyncio.sleep(3)
    run = await find_latest_run()
    if not run:
        raise HTTPException(502, "dispatched, but could not find the run (check Actions tab)")
    return BuildStatus(
        run_id=run["id"],
        status=run["status"],
        conclusion=run.get("conclusion"),
        html_url=run["html_url"],
    )


@app.get("/api/status/{run_id}", response_model=BuildStatus)
async def status(run_id: int):
    url = f"{GH_API}/repos/{WORKFLOW_REPO}/actions/runs/{run_id}"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, headers=gh_headers())
        if r.status_code != 200:
            raise HTTPException(404, f"run not found ({r.status_code}): {r.text[:200]}")
        run = r.json()

    out = BuildStatus(
        run_id=run_id,
        status=run["status"],
        conclusion=run.get("conclusion"),
        html_url=run["html_url"],
    )
    if run["status"] == "completed" and run.get("conclusion") == "success":
        release = await find_draft_release(run["run_number"])
        if release:
            out.release_url = release["html_url"]
            out.ipa_url = pick_ipa_asset(release)
    return out


@app.post("/api/latest/resolve")
async def resolve_latest():
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=45) as c:
            r = await c.get(DROPSTONE_URL)
            r.raise_for_status()
            ctype = r.headers.get("content-type", "")
            final = str(r.url)
            if "text/html" in ctype:
                m = re.search(r'https?://[^"\']+\.ipa[^"\']*', r.text)
                if not m:
                    return {"url": final, "note": "page has no direct .ipa link"}
                return {"url": m.group(0), "via": final}
            return {"url": final, "content_type": ctype, "size": len(r.content)}
    except httpx.HTTPError as e:
        raise HTTPException(502, f"fetch failed: {e}")


@app.get("/api/latest")
async def latest_ipa():
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as c:
        r = await c.get(DROPSTONE_URL)
        if r.status_code != 200:
            raise HTTPException(502, f"upstream {r.status_code}")
        ctype = r.headers.get("content-type", "")
        if "text/html" in ctype:
            m = re.search(r'https?://[^"\']+\.ipa[^"\']*', r.text)
            if not m:
                raise HTTPException(502, "no .ipa link on the landing page")
            r = await c.get(m.group(0))
            if r.status_code != 200:
                raise HTTPException(502, f"ipa fetch {r.status_code}")
        data = r.content
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'attachment; filename="YouTube_latest.ipa"',
            "X-Source": DROPSTONE_URL,
        },
    )


HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ipa patcher</title>
<style>
  :root{--bg:#0b0d10;--panel:#12161c;--line:#242a33;--ink:#e7e9ec;
        --dim:#8a919c;--accent:#5b8def;--accent-hi:#7aa2f7;--ok:#7ad4a0;--err:#ff7a7a}
  *{box-sizing:border-box}
  html,body{margin:0;background:var(--bg);color:var(--ink);
    font:14px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
  .wrap{max-width:760px;margin:0 auto;padding:56px 20px 96px}
  h1{font-weight:500;font-size:22px;margin:0 0 4px}
  .sub{color:var(--dim);font-size:12px;margin-bottom:28px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
        padding:20px;margin-bottom:16px}
  label{display:block;color:var(--dim);font-size:11px;margin:10px 0 4px;
        text-transform:uppercase;letter-spacing:.05em}
  input[type=text],input[type=url]{width:100%;background:#0b0d10;color:var(--ink);
    border:1px solid var(--line);border-radius:8px;padding:9px 11px;font:inherit;font-size:13px}
  input:focus{outline:none;border-color:var(--accent)}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .tweaks{display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;margin-top:6px}
  .tw{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--ink)}
  .tw input{accent-color:var(--accent)}
  button{background:var(--accent);color:#fff;border:0;padding:11px 20px;border-radius:9px;
    font:inherit;font-size:14px;cursor:pointer;transition:background .12s}
  button:hover:not(:disabled){background:var(--accent-hi)}
  button:disabled{opacity:.35;cursor:not-allowed}
  button.ghost{background:transparent;border:1px solid var(--line);color:var(--ink)}
  button.ghost:hover:not(:disabled){border-color:var(--accent);background:#141a24}
  .row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:16px}
  pre{background:#0b0d10;border:1px solid var(--line);border-radius:10px;
    padding:14px;font-size:12px;color:var(--dim);overflow:auto;
    white-space:pre-wrap;word-break:break-word}
  pre:empty{display:none}
  .ok{color:var(--ok)} .err{color:var(--err)}
  a{color:var(--accent);text-decoration:none}
  a:hover{text-decoration:underline}
  .hint{color:var(--dim);font-size:11px;margin-top:6px}
</style>
</head>
<body>
<div class="wrap">
  <h1>ipa patcher</h1>
  <div class="sub">dispatches the <b>Build IPA with tweaks</b> workflow on GitHub Actions.</div>

  <div class="card">
    <div class="grid">
      <div>
        <label>repo</label>
        <input type="text" id="repo" value="thecloudyy/Youtube-Premium-2.0-IPA">
      </div>
      <div>
        <label>branch</label>
        <input type="text" id="branch" value="main">
      </div>
    </div>
    <label>ipa url</label>
    <input type="url" id="ipa_url" placeholder="https://dropstone.lovable.app/d/ytipa">
    <div class="hint">leave blank to use the dropstone latest</div>

    <div class="grid" style="margin-top:6px">
      <div>
        <label>display name</label>
        <input type="text" id="display_name" value="YouTube">
      </div>
      <div>
        <label>bundle id</label>
        <input type="text" id="bundle_id" value="com.google.ios.youtube">
      </div>
    </div>

    <label style="margin-top:16px">tweaks</label>
    <div class="tweaks" id="tweaks"></div>

    <div class="row">
      <button id="go">dispatch build</button>
      <button class="ghost" id="latest">download latest decrypted ipa</button>
    </div>
    <div class="row">
      <button class="ghost" id="cleanup-runs">clean old runs</button>
      <button class="ghost" id="cleanup-releases">clean draft releases</button>
    </div>
  </div>

  <pre id="log"></pre>
</div>

<script>
const TWEAKS = ["youpip","ytuhd","ryd","abconfig","youquality","demc",
                "ytweaks","youslider","gonerino","ytshare","volboost"];
const tweaksEl = document.getElementById("tweaks");
for (const t of TWEAKS) {
  const d = document.createElement("label");
  d.className = "tw";
  d.innerHTML = `<input type="checkbox" data-t="${t}" checked> ${t}`;
  tweaksEl.appendChild(d);
}

const $ = id => document.getElementById(id);
const log = $("log");
const go = $("go");

function setLog(msg, cls=""){ log.className = cls; log.textContent = msg; }

go.onclick = async () => {
  go.disabled = true;
  setLog("dispatching…");
  const tweaks = {};
  document.querySelectorAll("#tweaks input[type=checkbox]").forEach(c => {
    tweaks[c.dataset.t] = c.checked;
  });
  const body = {
    repo: $("repo").value.trim(),
    branch: $("branch").value.trim(),
    ipa_url: $("ipa_url").value.trim(),
    display_name: $("display_name").value.trim(),
    bundle_id: $("bundle_id").value.trim(),
    tweaks,
  };
  try {
    const r = await fetch("/api/build", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || JSON.stringify(j));
    setLog("run started: " + j.html_url + "\nwaiting for the runner…", "ok");
    poll(j.run_id);
  } catch(e) {
    setLog("error: " + e.message, "err");
    go.disabled = false;
  }
};

async function poll(runId){
  const url = `/api/status/${runId}`;
  let n = 0;
  while (n++ < 240) {
    await new Promise(r => setTimeout(r, 5000));
    try {
      const r = await fetch(url);
      const j = await r.json();
      if (!r.ok) { setLog("poll error: " + (j.detail||r.status), "err"); go.disabled=false; return; }
      if (j.status === "completed") {
        if (j.conclusion === "success" && j.ipa_url) {
          setLog("done.\nrelease: " + j.release_url + "\nipa: " + j.ipa_url, "ok");
          const a = document.createElement("a");
          a.href = j.ipa_url; a.textContent = "download patched ipa";
          a.style.display = "block"; a.style.marginTop = "12px";
          log.appendChild(document.createTextNode("\n"));
          log.appendChild(a);
        } else if (j.conclusion === "success") {
          setLog("run succeeded, but no draft release found yet.\n" + j.html_url, "ok");
        } else {
          setLog("run finished: " + j.conclusion + "\n" + j.html_url, "err");
        }
        go.disabled = false;
        return;
      }
      setLog(`run ${j.status}… (${n*5}s)`, "");
    } catch(e) {
      setLog("poll error: " + e.message, "err");
      go.disabled = false;
      return;
    }
  }
  setLog("timed out polling. check actions: " + j?.html_url, "err");
  go.disabled = false;
}

async function cleanup(endpoint, label){
  setLog("dispatching cleanup: " + label + "…");
  try {
    const r = await fetch(endpoint, { method: "POST" });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || JSON.stringify(j));
    setLog("cleanup dispatched: " + j.workflow + "\ncheck the Actions tab in a moment.", "ok");
  } catch(e) {
    setLog("cleanup error: " + e.message, "err");
  }
}

$("cleanup-runs").onclick = () => cleanup("/api/cleanup/runs", "old runs");
$("cleanup-releases").onclick = () => cleanup("/api/cleanup/releases", "draft releases");
$("latest").onclick = () => { window.location.href = "/api/latest"; };
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


if __name__ == "__main__":
    import uvicorn
    log(f"starting — repo={WORKFLOW_REPO} file={WORKFLOW_FILE} ref={WORKFLOW_REF} "
        f"token_len={len(GITHUB_TOKEN)}")
    if not port_free(PORT):
        log(f"port {PORT} busy — clearing stale listener")
        kill_port(PORT)
    if not port_free(PORT):
        log(f"port {PORT} still held after kill — exiting")
        sys.exit(1)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
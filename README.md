<p align="center">
<img src="Icon.png" width="200" height="200"/>
<h1 align="center">YouTube Premium IPA (YouMod)</h1>
</p>
<p align="center">
<img src="https://img.shields.io/badge/Platform-iOS%20%7C%20iPadOS%2014.0%2B-blue" alt="Platform"/>
</p>

Patched YouTube IPAs with premium features, built automatically with GitHub Actions from the [YouMod](https://github.com/Tonwalter888/YouMod) tweak plus a set of community tweaks. This repo is a build/publish fork: the tweak source lives in `Files/`, the build logic in `.github/workflows/`, and `ytsigner.py` is a small local web UI that triggers builds for you.

> ⚠️ Not affiliated with Google or YouTube. I only publish builds. You must supply your own decrypted YouTube IPA (I can't provide one for legal reasons).

## What's inside

| Toggle | Tweak |
|---|---|
| `youpip` | [YouPiP](https://github.com/PoomSmart/YouPiP) – picture-in-picture |
| `ytuhd` | [YTUHD](https://github.com/PoomSmart/YTUHD) – VP9/AV1 codecs |
| `ryd` | [Return-YouTube-Dislikes](https://github.com/PoomSmart/Return-YouTube-Dislikes) |
| `abconfig` | [YTABConfig](https://github.com/PoomSmart/YTABConfig) – A/B flags |
| `youquality` | [YouQuality](https://github.com/PoomSmart/YouQuality) (off by default) |
| `demc` | [DontEatMyContent](https://github.com/therealFoxster/DontEatMyContent) – stretch to fill |
| `ytweaks` | [YTweaks](https://github.com/fosterbarnes/YTweaks) |
| `youslider` | [YouSlider](https://github.com/PoomSmart/YouSlider) – brightness/volume gestures |
| `gonerino` | [Gonerino](https://github.com/castdrian/Gonerino) – ad/sponsor blocking |
| `ytshare` | [youtube-native-share](https://github.com/jkhsjdhjs/youtube-native-share) |
| `volboost` | [VolumeBoostYT](https://github.com/VasirakCalgux/VolumeBoostYT) – up to 2000% volume (requires iOS 16+) |

Plus the built-in YouMod features: downloads (video/audio/captions/thumbnail, up to 1080p60), OLED theme + keyboard, nav-bar / feed / player / Shorts / tab-bar customization, and built-in SponsorBlock.

## Requirements

1. A **decrypted YouTube IPA** (e.g. dumped on a jailbroken device). Upload it somewhere that gives a **direct download link** (filebin, catbox, Dropbox `?dl=1`, Mega links also work). A link to a web page will fail validation.
2. A GitHub account (to run Actions). Fork this repo if you want your own builds.

## Method A — build with the patcher (recommended)

`ytsigner.py` is a tiny local server with a web UI that dispatches the workflow and hands you the finished IPA link.

```bash
pip install -r requirements-patcher.txt
```

Create a [classic personal access token](https://github.com/settings/tokens) with **`repo`** and **`workflow`** scopes, then:

```bash
# Windows (PowerShell)
$env:GITHUB_TOKEN = "ghp_..."
# macOS / Linux
export GITHUB_TOKEN="ghp_..."

python ytsigner.py
```

Open http://localhost:8000 and fill in:

- **repo / branch** – tweak source (default: this repo, `main`)
- **ipa url** – direct link to your decrypted IPA (blank = use the dropstone latest)
- **display name / bundle id** – app name and identifier for the patched app
- **tweaks** – tick what you want, then **dispatch build**

The page polls the run and, on success, shows a **download patched ipa** link (served from the draft release). The `clean old runs` / `clean draft releases` buttons dispatch the housekeeping workflows.

> Never commit your token anywhere — pass it only via the `GITHUB_TOKEN` environment variable. If a token ever leaks, revoke it at github.com/settings/tokens and make a new one.

Optional env vars: `WORKFLOW_REPO` (default this repo), `WORKFLOW_FILE` (default `ipa.yml`), `WORKFLOW_REF` (default `main`).

## Method B — build manually from GitHub

1. Fork this repo → **Actions** tab → **Build IPA with tweaks** → **Run workflow**.
2. Fill the inputs (same fields as above) → **Run workflow**.
3. When it finishes, download the IPA from the **draft release** it creates (`youmod-ipa<N>` under your repo's Releases page, visible to you as owner).

## Downloading a finished build

Successful runs publish a **draft** release named `youmod-ipa<N>` (e.g. `YouMod_21.40.5_v2.0.0.ipa`). Drafts are only visible to accounts with access to the repo, so log in and check the Releases page.

## Troubleshooting

- **`function definition is not allowed here` / `expected '}'` in `Files/*.x`** — the current Logos toolchain drops the closing brace of single-line hook methods containing `%orig`. Fixed repo-wide here by expanding all 73 sites to braced multi-line methods; `.x` files are pinned to LF via `.gitattributes`. If it reappears in a new file, apply the same rewrite.
- **`VolumeBoostYT` fails with `incompatible pointer types ... [-Werror]`** — that tweak pins `generator=internal`, which drops the `.mutableCopy` suffix in `%orig.mutableCopy`. The workflow auto-patches it after cloning (see the `Patch VolumeBoostYT` step in `ipa.yml`).
- **`getaddrinfo failed` in the patcher** — your local DNS/network, not the repo. Retry, `ipconfig /flushdns`, or switch DNS to `8.8.8.8` / `1.1.1.1`.
- **Patcher says "no draft release found yet" on a green run** — fixed in the current `ytsigner.py` (the old version used an API endpoint that 404s on drafts). Pull the latest patcher and restart it.
- **IPA validation fails** — the URL must be a direct file download, not a landing page.

Housekeeping workflows included: `delete-old-workflows-run.yml`, `delete-old-draft-releases.yml`.

## Contributing

Same rules as upstream: open an issue, branch, test, PR with evidence (screenshots/video) for non-localization changes.

## License

GPLv3, same as upstream YouMod. See [LICENSE](LICENSE).

## Credits

- [Tonwalter888/YouMod](https://github.com/Tonwalter888/YouMod) and all its contributors — the tweak itself
- [PoomSmart](https://github.com/PoomSmart), [fosterbarnes](https://github.com/fosterbarnes), [castdrian](https://github.com/castdrian), [therealFoxster](https://github.com/therealFoxster), [jkhsjdhjs](https://github.com/jkhsjdhjs), [VasirakCalgux](https://github.com/VasirakCalgux) — the integrated tweaks
- [dayanch96](https://github.com/dayanch96), [YTLitePlus](https://github.com/YTLitePlus/YTLitePlus), [arichornlover](https://github.com/arichornlover) — prior art this project builds on

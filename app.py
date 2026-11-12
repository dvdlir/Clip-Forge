import os, re, json, shutil, subprocess, tempfile
from pathlib import Path
import streamlit as st
import yt_dlp
from faster_whisper import WhisperModel

APP_DIR = Path(__file__).parent
WORK = APP_DIR / "work"
WORK.mkdir(exist_ok=True)

st.set_page_config(page_title="ClipForge AI", page_icon="✂️", layout="wide")
st.title("✂️ ClipForge AI")
st.caption("Paste a video link → AI finds highlights → export vertical clips")
st.info("Only process videos you own or have permission to reuse. Follow YouTube's Terms and the creator's rights.")

@st.cache_resource
def load_model():
    # CPU-friendly starter model. First run downloads the model.
    return WhisperModel("base", device="cpu", compute_type="int8")

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-3500:])
    return p.stdout

def download_video(url, outdir):
    opts = {
        "outtmpl": str(outdir / "source.%(ext)s"),
        "format": "best[height<=1080][ext=mp4]/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
        if not path.exists():
            candidates = list(outdir.glob("source.*"))
            if not candidates:
                raise FileNotFoundError("Downloaded video file was not found.")
            path = candidates[0]
        return path, info.get("title", "video")

def get_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(out.strip())

def make_segments(transcript, duration, clip_len, count):
    # Group transcript into overlapping candidate windows, then score language signals.
    candidates = []
    step = max(8, clip_len // 2)
    starts = list(range(0, max(1, int(duration - clip_len + 1)), step))
    if not starts:
        starts = [0]
    exciting = {"wow", "what", "no", "wait", "crazy", "insane", "actually",
                "finally", "impossible", "bro", "amazing", "secret", "best",
                "worst", "never", "always", "why", "how", "look"}
    for start in starts:
        end = min(duration, start + clip_len)
        words = []
        punctuation = 0
        for seg in transcript:
            if seg.end > start and seg.start < end:
                t = seg.text.strip()
                words.extend(re.findall(r"[A-Za-z']+", t.lower()))
                punctuation += t.count("!") * 2 + t.count("?")
        if not words:
            continue
        density = len(words) / max(1, end-start)
        keyword_hits = sum(1 for w in words if w in exciting)
        # Heuristic highlight score: speech density + expressive language.
        score = density * 1.5 + keyword_hits * 1.8 + punctuation * 0.7
        candidates.append({"start": float(start), "end": float(end),
                           "score": score, "words": len(words)})
    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = []
    for c in candidates:
        if all(abs(c["start"] - x["start"]) >= clip_len * 0.75 for x in chosen):
            chosen.append(c)
        if len(chosen) >= count:
            break
    return sorted(chosen, key=lambda x: x["start"])

def srt_time(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(transcript, start, end, dest):
    lines, idx = [], 1
    for seg in transcript:
        a, b = max(seg.start, start), min(seg.end, end)
        txt = seg.text.strip()
        if b <= a or not txt:
            continue
        # Offset subtitle times to the exported clip.
        lines += [str(idx), f"{srt_time(a-start)} --> {srt_time(b-start)}", txt, ""]
        idx += 1
    Path(dest).write_text("\n".join(lines), encoding="utf-8")

def export_clip(video, transcript, seg, outpath):
    tmp_srt = str(Path(outpath).with_suffix(".srt"))
    write_srt(transcript, seg["start"], seg["end"], tmp_srt)
    # Center crop to 9:16; scale to 1080x1920 and burn in readable subtitles.
    subtitle_path = tmp_srt.replace("\\", "/").replace(":", r"\:")
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,subtitles='" + subtitle_path + "':force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=150'"
    run(["ffmpeg", "-y", "-ss", str(seg["start"]), "-i", str(video), "-t",
         str(seg["end"]-seg["start"]), "-vf", vf, "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", str(outpath)])
    try: os.remove(tmp_srt)
    except OSError: pass

url = st.text_input("YouTube video link", placeholder="https://www.youtube.com/watch?v=...")
c1, c2 = st.columns(2)
with c1:
    clip_len = st.slider("Clip length (seconds)", 15, 60, 30)
with c2:
    count = st.slider("Number of clips", 1, 10, 3)

if st.button("Find highlights and create clips", type="primary", disabled=not url.strip()):
    try:
        with st.spinner("Downloading video…"):
            job = Path(tempfile.mkdtemp(prefix="clipforge_", dir=WORK))
            video, title = download_video(url.strip(), job)
        st.write(f"**Video:** {title}")
        with st.spinner("AI is listening and finding interesting moments. First run may take longer while the speech model downloads…"):
            model = load_model()
            segments, info = model.transcribe(str(video), word_timestamps=False, vad_filter=True)
            transcript = list(segments)
        if not transcript:
            st.error("I couldn't detect speech in this video.")
            st.stop()
        duration = get_duration(video)
        picks = make_segments(transcript, duration, clip_len, count)
        if not picks:
            st.error("No suitable speech sections were found.")
            st.stop()
        results = []
        progress = st.progress(0)
        for i, seg in enumerate(picks, 1):
            out = job / f"clip_{i:02}.mp4"
            with st.spinner(f"Rendering clip {i} of {len(picks)}…"):
                export_clip(video, transcript, seg, out)
            results.append((out, seg))
            progress.progress(i / len(picks))
        st.success(f"Created {len(results)} clips.")
        st.caption("The AI score is a first-version estimate based on speech density and expressive words, not a guarantee of virality.")
        for i, (out, seg) in enumerate(results, 1):
            st.subheader(f"Clip {i} · {int(seg['start'])}s–{int(seg['end'])}s")
            st.video(str(out))
            st.download_button(f"Download clip {i}", data=out.read_bytes(),
                               file_name=out.name, mime="video/mp4", key=f"dl{i}")
    except Exception as e:
        st.error("Couldn't finish this video.")
        st.code(str(e))
        st.caption("Check that the link is accessible and that FFmpeg is installed. Some videos restrict downloading or require sign-in.")

st.divider()
st.caption("ClipForge AI prototype · Runs on your computer. No paid AI API key required.")

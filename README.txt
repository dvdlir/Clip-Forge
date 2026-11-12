CLIPFORGE AI — FREE LOCAL STARTER

WHAT IT DOES
- Accepts a YouTube URL
- Downloads one video (not playlists)
- Uses a local speech-recognition model to transcribe it
- Scores sections using speech density and expressive language
- Makes vertical 9:16 MP4 clips with burned-in subtitles

WINDOWS DESKTOP EXE
See BUILD_EXE.txt. A GitHub Actions workflow builds a Windows executable for you.
The EXE includes FFmpeg and Python dependencies. On first launch it downloads the
Whisper speech model. Internet is needed for that first model download and for video access.

IMPORTANT
Only process videos you own or have permission to reuse. Respect copyright,
creator permissions, and YouTube's Terms. This is a prototype, not a promise
that clips will go viral.

PYTHON VERSION
For running from source instead of the EXE, see run_windows.bat. Install Python 3.10+
and FFmpeg first.

NOTES
- No paid AI API key is required.
- Processing happens on your computer and can be slow on older PCs.
- The default Whisper "base" model is a compromise for CPU speed and accuracy.
- The first-version highlight scoring is heuristic, not a sophisticated
  semantic virality model.
- Vertical framing is a centered crop. Face tracking and speaker-aware
  reframing are future upgrades.
- YouTube may restrict access to some videos; use permitted, accessible links.

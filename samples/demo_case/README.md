Build the demo case from the design doc walkthrough (§4) into samples/demo_case/.

The files are committed, so `make demo` works without regenerating them. Regenerating needs macOS
`say` for the speech; everything else is seeded and deterministic.

Ground truth (what the analysis should find):
  * clip.mp4: a cut at 14.0 s (12 frames removed inside one shot)
  * its audio: speech recorded in two rooms; background noise steps up ~9 dB at 14.2 s
  * podium_photo.jpg: EXIF Software "Adobe Photoshop", DateTimeOriginal 2024-03-03, stale thumbnail
  * caption.txt: dated 12 Nov 2026 (conflicts with the photo's EXIF date)

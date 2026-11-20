# Limitations

TruthLens reports **indicators**, never "fake" or "real". These are the limits we know about.

## What it cannot detect

- **Fully AI-generated media without editing traces.** A synthetic image or video that was generated in one pass
  and never edited may carry no ELA, noise, ghost, copy-move, flow or splice signal. The verdict will then be
  *No indicators found* or *Inconclusive*, which is why that verdict never means "authentic".
- **Cloned voices recorded at full bandwidth.** The band-limit check only catches synthetic speech that was
  generated at a low sample rate and upsampled. Prosody statistics are a weak signal (see validation: 0 % recall,
  42 % false positives on our synthetic voices), weighted 0.3 and calibrated to about 0.04.
- **Splices between recordings with the same background noise.** The noise-floor detector needs the room noise to change.
- **Who made a change.** The report does not establish authorship or intent.

## Measurement limits

- **The test set is small and self-made.** 204 items (`validation/results/metrics.json`), built from the public-domain
  sample photos bundled with scikit-image, synthetic voiced speech with room noise, macOS `say` text-to-speech and
  camera pans rendered from the photos (decision D-13). No public forensic dataset was run. The numbers say how
  the analyzers behave on these items, not how they generalise.
- **Pixel-level image signals are weak.** On the test set ELA finds 47 % of splices/retouches (11 % false positives),
  the noise map 28 % (19 %) and JPEG ghost 75 % (31 %). Calibration lowers their weight accordingly.
- **Not validated** (no ground truth in our set): face-region flicker and lip-sync (no faces in the synthetic video),
  frame forensics on video frames, place and number conflicts, "modified after capture" and missing camera tags.
  Their ranges are flagged *uncalibrated* where they appear.
- **Platt calibration on a small set.** Indicators that were right every time get a Beta-posterior range
  (e.g. 0.86–0.95), not certainty (D-15). No single signal exceeds 0.95 and no combination exceeds 0.97 (D-11).
- **720p input** limits face-region and lip-sync measurements; longer or larger files are trimmed or downscaled
  with a warning shown on the evidence card and in the report.
- **Social-platform recompression** can produce error-level patterns similar to editing; rule R-14 lowers the weight of
  ELA and ghost findings on images that look platform-recompressed.

## Observed in visual QA (19 Nov 2026)

- A pasted-region JPEG got *No indicators found* although weak JPEG-ghost traces were recorded: a concrete false
  negative. The verdict is never an authenticity decision.
- Reports can be exported while findings are still unreviewed; each finding's review status is printed in the report.
- Whisper can hallucinate repeated words with high confidence on non-speech audio.

## Product limits

- **Accounts are basic.** Sign-up / log-in with email and password (D-16): no email verification, password reset or
  multi-factor sign-in. Sign-up can be closed with `TRUTHLENS_ALLOW_SIGNUP=0`.
- **The hosted demo is not offline** and its storage resets when the free Hugging Face Space restarts (D-17).
- **Search** matches case IDs, titles, descriptions, investigators, evidence file names, SHA-256 prefixes (6+ characters)
  and exact finding IDs; it is not full-text search of transcripts or captions.
- **One analysis at a time** (one worker, by design for the 8 GB budget).
- **The offline gazetteer** has about 45 places; other place names are reported as unverifiable.
- **Speech recognition** is Whisper *base*; it is unreliable on noise and non-speech (it transcribes our synthetic
  voice as "Beep."), which can make caption-vs-speech checks unverifiable.
- **Screenshots** of the UI are not included in the README yet.
- The PDF export needs `pango` (installed by Homebrew on macOS). Without it the HTML and JSON reports are still produced.

## Deepfake detectors

- **Generalisation is the main risk.** Learned detectors recognise the generators they were trained on. An older image
  detector we tried scored recent generators (GPT-Image, FLUX.2) no better than chance, which is why validation picks the
  model per modality on recent samples. New generators released after the model will be missed more often.
- **The validation samples are small** (240 images, 240 voice clips from 42 speakers, 116 texts) and the model was
  chosen on the same samples, so the reported numbers are optimistic. Social-media recompression, screenshots and re-recordings were not
  part of the test.
- **Text detection is the weakest.** Short captions carry very little signal (see the 30-word AUC on the Validation
  page); formal, edited or non-native human writing is flagged more often.
- **Voice detection** is trained on known TTS and voice-conversion systems; heavy noise suppression and phone audio
  can raise the score on human speech.
- **Compressed video.** On our own heavily compressed 960×540 demo clip of genuine stock footage, a few single frames
  scored as AI-generated. Median aggregation and extra crops did not resolve the false alarms on the reported road clip. Video frame scores are therefore experimental diagnostics only: no percentage or authentic/deepfake label is issued without labelled-video validation. Temporal editing findings remain available.
- **"Likely authentic" is not proof of authenticity.** It means the learned AI estimate falls below the configured threshold with a sufficiently low upper bound; editing is assessed separately and a
  generator the detector does not know can still produce it.

- AI-generation estimates are separate from ordinary editing indicators. A missing detector has no percentage; older combined-scoring analyses require a re-run. Neither model estimates nor fused indicator bands establish authenticity.
- Reports include a pre-export history snapshot. Their own generation event is appended later, so the exported chain is verifiable without pretending to include its own future hash.
- Registered image/frame matches are a geometric correspondence heuristic, not face identity recognition or proof that an edit was malicious.

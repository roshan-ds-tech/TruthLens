# TruthLens: complete manual walkthrough

This guide is for someone using the website for the first time. No programming or terminal commands are needed.
Allow about 45–60 minutes if you try every exercise.

Website: https://truthlens-six-mu.vercel.app

Version note, 19 November 2026: the live frontend is still the audited version f896561. A newer fix commit,
0cf682d, exists locally but was not the live production deployment when this guide was written. Known problems
below describe the current live version; they are tests to record, not mistakes you are making.

## Before you begin

1. Keep the Mac hosting the demo powered on, connected to the internet, and its lid open. The website's
   analysis service runs on that Mac. Visitors on another computer/phone still need that Mac online.
2. Open the website in Chrome or another modern browser. If it was already open, refresh it once.
3. Unzip `TruthLens-Manual-Test-Kit.zip`. On a Mac, double-clicking it creates a folder of the same name.
4. Keep the folder open in Finder. Each numbered subfolder is one exercise. Do not rename or change the
   files before the first test. Some files are deliberately damaged or edited.
5. Use a new test account of your own. Keep its password somewhere you can find it: this app has no
   password-reset feature. Do not share your password with an assistant.
6. If the menu shows icons without words, hover over an icon to see its name.

**What the website tells you:** it looks for suspicious traces. It does not reliably certify whether something
is real or fake. “No indicators found” means its checks found no sufficiently strong signal, not “proved genuine.”
“Inconclusive” means the result is uncertain. “Indicators of manipulation” or “Strong indicators” means you
should inspect the named evidence and alternative explanations. A range such as 0.92–0.97 describes agreement
between checks; it is not a 92–97% probability that the file is fake.

## 1. Create an account and find your way around

Click **Sign up**. Enter your name, an email address, and a password of at least eight characters, then click
**Create account**. You should reach the Dashboard. Your new account should initially show no cases.

The main areas are:

| Area | What it is for |
|---|---|
| Dashboard | Overview, recent cases, and summary counts |
| Cases | Open an existing investigation and filter cases |
| New case | Give an investigation a name and add files or a caption |
| Analysis run | Watch the checks and read their progress log |
| Workspace | Examine one case, findings, reviews, and correlations |
| Image evidence | Compare an image with analysis layers |
| Audio evidence | Play audio, inspect the waveform/spectrogram, and read words |
| Report | Review and download the report |
| Evidence Library | Browse all files belonging to your account |
| Validation | See performance on the developers' small test collection |
| Settings | Turn particular checks on/off and view storage/privacy information |

A **case** is simply a folder for one investigation. **Evidence** means the files or text you put in it.
A **finding** is something one of the checks wants you to examine.

## 2. Start with the clean control files

Click **New case**. Use the title **Practice 1 — Clean controls** and any short description.
Click **browse files**, open `01-clean`, and select all three files. On a Mac, hold Command while clicking
several files, or use Command+A inside that folder. Click Open.

Wait until every file says **Ready**. You should see three uploaded items and a short fingerprint beside
**sha256**. That fingerprint identifies the file; you do not need to type it anywhere.

Click **Start analysis**. Watch the progress and the log; do not click Start repeatedly. When the heading says
**Analysis complete**, click **Open workspace**. In the previous test these three files produced **0 findings**
and **No indicators found**. If your result is different, record what changed rather than assuming the website
must be right.

Play the clean video using the triangle button. Check that the picture moves, the time advances, and playback
stops at the end. Click the image and audio evidence cards to confirm their viewers open. Use the link back
to the case workspace when you are finished.

## 3. Test known image, video, and audio edits

Click **New case** again. Title it **Practice 2 — Deliberate edits**. Upload all six files from `02-edited`.
In **Paste caption or claim**, enter:

> This photograph was captured on 12 November 2026.

Click Start analysis and then Open workspace after it finishes.

| File | What was deliberately changed | What to look for |
|---|---|---|
| image-copy-move.jpg | A region was copied elsewhere in the same image | Copy-move match and marked regions |
| image-metadata-edited.jpg | Editing software/date information and an old preview thumbnail | Editing software, date, and thumbnail findings |
| image-pasted.jpg | A region was pasted from another image | Important limitation: this file previously received No indicators found, although weak traces were recorded |
| video-jump-and-duplicate.mp4 | Frames were removed and one frame repeated | Motion jump near 3.0 seconds; duplicate near 4.4 seconds, frame 110 |
| audio-spliced.wav | Background noise changes at a known boundary | Noise-floor step near 4.2 seconds |
| audio-bandlimited.wav | Audio was produced at a lower bandwidth and upsampled | Band-limited spectrum, roughly 3.9 kHz cutoff |

Previously the combined case had **15 findings** and **Strong indicators**. Treat this as a comparison point,
not a general accuracy promise.

## 4. Explore every image-viewing control

In Practice 2, click the **image-copy-move.jpg** evidence card.

- Find **Error level**, **Noise map**, **Copy-move**, and **Regions**. Turn each on/off so you can see what changes.
- Drag the comparison handle left, right, and back to the middle. It reveals different amounts of the original
  image and the selected analysis view.
- Click a numbered box on the picture. Check that the matching finding is selected below it.
- Click another finding in the list and look for the corresponding highlighted region.
- Open **Limitations** and read the warning about what the image checks cannot establish.

Return to the workspace, then open **image-metadata-edited.jpg**. Scroll to **Metadata · EXIF**. EXIF is
information stored inside a photo. Look for Photoshop, a 2024 capture date, a later modification date,
and a thumbnail mismatch. The caption you entered gives a conflicting 2026 date.

A software tag is evidence of processing, not proof that the pictured event is fabricated.

## 5. Explore the video player and suspicious moments

Return to Practice 2's workspace. Select the video card. Press Play and then Pause.
Click the finding mentioning **00:03.0**; the player should jump to that moment. Do the same for **00:04.4**.
Click a mark in the timeline below the player and check that the time changes. The suspicion curve helps you
choose where to look; it does not itself prove an edit.

The video may take a moment to load before playback is available, especially through the demo tunnel.

## 6. Explore the audio player, picture of the sound, and words

Open **audio-spliced.wav** from the workspace. The **waveform** shows louder/quieter sound over time.
The **spectrogram** shows how frequencies change over time.

Press Play, then Pause. Click the highlighted segment around **4.2 seconds**. Check that the playback marker
moves there. Look for the highlighted noise change in the spectrogram. In the transcript, click a word/time
and check that the player's time jumps to it. The synthetic fixture is beep-like, so its transcript is not
normal conversation.

Also open **audio-bandlimited.wav** and read why a restricted frequency range can be suspicious. Read its
alternative explanation: ordinary phone recordings, codecs, or conversion can also remove frequencies.

## 7. Review a finding yourself

Back in the workspace, choose a finding and open **Alternative explanations**. Read at least one.
For practice, click **Accept** on one finding and **Reject** on another. Check that each status changes.
Neither button deletes the original file or turns the automated verdict into a final truth judgment.
Clicking the same decision again returns it to pending review if you want to undo the practice decision.

Click **Add note**, write a short explanation, and click **Save note**. Leave the page and reopen the same
case; confirm your note is still shown.

**Current bug to check carefully:** moving to another case with the same finding ID can pre-fill an old note
draft. Do not save that wrong text. Refresh the page and reopen the intended case before entering a note
in a different case. This bug does not mean the note has already been saved into the other case.

## 8. Inspect the history and repeat the analysis

Click **Chain of custody**. This is the file/action history. Look for file uploads, analysis, and your review
or note. It should say the **hash chain is verified**. Close the drawer using its close button.

Click **Re-run analysis**. Wait for it to finish, then reopen the workspace. The same inputs and settings should
produce the same finding IDs, locations, and scores. Confirm that your saved reviews/notes remain.

## 9. Try real human speech and unchanged source downloads

Create **Practice 3 — Source media**. Upload the five files in `03-real-media` and run analysis.

- **human-speech-original.wav** is actual human speech from the **Open Speech Repository**. Previously it had
  No indicators found. Open its audio viewer and listen/read along. Word timings should work, but the text may
  contain recognition mistakes.
- **human-speech-edited.wav** removes one second and introduces background noise at edited second 12.00.
  The website previously flagged a boundary near **11.6 seconds**: close, but not exact.
- **photo-clouds.jpg** and **photo-park.jpg** are unchanged downloads supplied by Samplelib. They already have
  GIMP editing metadata; they are not certified camera-original files. Their earlier verdicts were Inconclusive.
- **road-video.mp4** is another unchanged source download. It previously produced Inconclusive video findings;
  its extracted audio was flagged for restricted bandwidth. This illustrates why normal processing can trigger checks.

The website may automatically add an **Audio track (from ...)** item when a video contains sound. That is expected.

## 10. Test whether the caption matches what was actually said

Create **Practice 4 — Wrong quote**. Upload only `03-real-media/human-speech-original.wav`.
Paste this deliberately incorrect claim:

> The speaker said "Schools and offices are closed because the government has declared a three day state holiday."

Run analysis. The recording actually contains test sentences, not that announcement. Look for
**Quoted speech not found in audio** and rule **R-05**. Previously there was one finding, and the audio itself
still had No indicators found. Read the caption-versus-transcript comparison and its alternative explanations.

## 11. Test the full cross-media example

Create **Practice 5 — Connected evidence**. Upload `clip.mp4` and `photo.jpg` from `04-cross-media`.
Open that folder's `caption.txt` in TextEdit, copy its contents, and paste them into **Paste caption or claim**.
Do not rely on uploading the text file in the current live version.

Run analysis and open the workspace. Previously it produced **6 findings** and **Strong indicators**.
Scroll to **Cross-modal correlations**. Click **R-03**: the graph should highlight the link between the video
cut at 14.0 seconds and audio change at 14.2 seconds. Click **R-11**: it should highlight the photo/caption date
conflict. Notice that the picture changes to show which rule you selected.

## 12. Make and download a report

In any completed case, click **Export report**. Check the case title, files, findings, reviews, notes,
limitations, and recommended human checks. Pending findings can appear in a draft report; they should be labelled.

Click **Download PDF**, then open the downloaded file in Preview. Check that its text, pictures, and page
numbers are readable. Click **Export JSON** too. JSON is the structured version for software or Claude Code;
you do not need to understand its contents to check that the download succeeded.

**Current limitation:** the browser's preview says two pages, but the PDF may have more pages. Check the actual
PDF for printed pagination. Always regenerate the report after changing a review if you want the latest review included.

## 13. Test Cases and Evidence Library

Open **Cases**. Try **All**, **Needs review**, **Strong indicators**, **Inconclusive**, and **Closed**.
A filter can legitimately show nothing if you have no matching case. Click a case to open it.
No close-case control was found in the audited UI, so an empty Closed filter is expected for your new account.

Open **Evidence Library**. Try **Images**, **Video**, **Audio**, **Text**, and **All**. Click an item to check that
its image/audio viewer or case workspace opens. Check filenames, case names, small previews, and fingerprints.

Try the top search box with part of a case name. **Current live-version bug:** it accepts typing but does not
search. This is not a problem with your spelling. A newer local fix adds search, but it was not live when this
guide was prepared.

## 14. Test Settings, Validation, and theme

Open **Settings**. The switches control which checks run. To test one safely, turn **Copy-move** off, leave
Settings, return, and confirm it is still off. Then turn it **on again**. For a fuller test, rerun a case with
image-copy-move.jpg while that check is off and confirm the Copy-move finding is absent; restore it and rerun again.
Do not expect the entire verdict to disappear, because other checks may still find something.

Look at **Privacy and storage**. In hosted mode it should say cases are visible only to your account.
Home's current “Nothing is uploaded” wording is misleading: your browser sends evidence to the Mac server.

Open **Validation**. Scroll through the metrics, reliability chart, and false-positive table. You do not need
to recalculate these. Check that the page loads and explains that the results come from a small test collection.

Use the sun/moon button to switch theme. Try both themes on a viewer and the report. Refresh the page and
confirm the choice is remembered. On narrow windows the sidebar may show icons instead of text.

## 15. Test upload limits and error messages

Create **Practice 6 — Limits only**. Use `05-limits-and-errors`. These are boundary tests; you do not need to
analyze the long files.

| Input/action | Expected response |
|---|---|
| corrupt-image.jpg | File rejected because it cannot be decoded |
| unsupported.bin | Unsupported file type; the picker may require choosing All Files |
| image-over-20mb.jpg | Rejected with a 20 MB size limit message |
| audio-121-seconds.wav | Accepted with a warning that only the first 120 seconds will be analyzed |
| video-61-seconds.mp4 | Accepted with a warning that only the first 60 seconds will be analyzed |
| video-1080p.mp4 | Accepted with a warning about downscaling to 720p |
| Upload an already-uploaded file again in the same case | No duplicate evidence record should be added |

Wait for an error or Ready before moving on. The oversized file can take longer to reject because the current
site checks it on the server after upload.

To check text length, copy a long paragraph repeatedly until the character counter exceeds 5,000, then click
Save draft. It should reject the caption with a length message. Replace it with a short sentence before saving again.

## 16. Check the two known text/draft failures

**Text-file-only test:** create a fresh case and upload only `text-upload.txt`, leaving the caption box empty.
The server currently accepts it, but the form shows zero files and Start analysis stays disabled. Record that
as a bug. For normal use, paste the text into the caption box instead.

**Saved draft test:** create another case, upload a file, enter a short caption, and click Save draft. Go to
Cases and click that draft. The current live version can open an empty form instead of restoring the draft.
Your saved records have not been deleted, but the resume screen is broken. For now, complete a new case's
uploads and analysis in one sitting rather than depending on draft reopening.

## 17. Test sign-out and returning later

Click **Sign out** in the sidebar. You should return to Home. Click Log in and deliberately try one wrong
password; it should show an error. Then enter the correct password and confirm you return to your own Dashboard.
Refresh once and confirm you remain signed in. Do not repeatedly guess passwords; the app limits failed attempts.

## Record your results

For each exercise, note the case name, what you clicked, what you expected, what actually happened, and a
screenshot if something went wrong. On a Mac, Command+Shift+4 lets you select an area to capture. Do not include
passwords in screenshots.

A simple record can look like this:

| Test | Expected | Actual | Pass / fail / uncertain |
|---|---|---|---|
| Clean image | No strong editing signal | ... | ... |
| Copy-move image | A copied-region finding | ... | ... |
| Video jump | Marker near 3.0 s | ... | ... |
| Audio splice | Marker near 4.2 s | ... | ... |
| Wrong quote | Caption/transcript mismatch | ... | ... |
| Save and reopen draft | Title/files restored | ... | ... |

The kit is a practical product test, not proof of universal detection accuracy. It does not validate all
AI-generated images, cloned voices, face deepfakes, lip-sync edits, or every possible file format.

Input credits and edit details are in SOURCES.txt. For the human recording, credit **Open Speech Repository**.

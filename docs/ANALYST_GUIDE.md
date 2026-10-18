# Analyst workspace guide

## One match, one decision

Start with a specific question that could change preparation, coaching or recruitment work. The workflow is: import permitted evidence, review video, separate observation from interpretation, and write a recommendation with limitations. Synthetic examples demonstrate the interface; they do not establish a real tactical finding.

## Import events

Download the CSV template. Required columns are id, period, second, team, player, action, x, y, end_x, end_y and outcome. Column order may change, but names must match exactly. Use UTF-8, commas and standard CSV quotation. Each event needs a unique ID, team, action, period 1–4 and time in seconds from that period's start. Player and outcome may be empty.

Coordinates must be 0–100, origin top left, and already normalized so the acting team attacks right. Empty coordinate pairs are allowed. Mixed coordinate systems or unnormalized directions will produce misleading maps. The application checks ranges, not whether your underlying events are true. Use one match per project, at most 20,000 events and a 5 MB file.

The importer rejects malformed quotes, duplicate headers, duplicate IDs, invalid times and invalid coordinate pairs. The original file's SHA-256 fingerprint is retained. A failed import leaves the current project intact. A successful replacement asks you to keep a backup first.

## Review local video

Attach a browser-playable video file you may use. It remains on your device. Configure the video timestamp where each period starts; halftime breaks and trimmed recordings vary. Use event adds its ID to the evidence field and seeks the video when a valid synchronized timestamp is available. Inspect surrounding play, score state and opposition before writing a finding.

## Build the brief

For each note, record observation, interpretation, recommendation, confidence and limitations or counterevidence. Confidence is your qualitative judgement, not a computed probability. Referenced event IDs must exist. Manual observations without an event reference are allowed and clearly identified in the brief.

Add the evidence note before changing the dataset. Save on this device is optional. Export project backup preserves events, added notes, offsets and feedback; it does not include video. Export decision brief creates readable Markdown with source information and evidence timestamps. Imports are rendered as text, not trusted HTML.

## Test usefulness

Use the task timer for active work and stop it when finished. Record usefulness from 1 to 5 and describe whether the report changed a decision. Export feedback only if you choose to share it. Self-reported outcomes are not independently verified. A real pilot should compare the same task against the analyst's existing workflow.

Read the [privacy and storage policy](PRIVACY.html) before saving confidential information.

# Modal pentatonic contract review

Codex session01a084b8-9ef7-79b1-b32f-6f30bd9b6656 recommends preserving the
ten longstanding application-specific five-note selections. Accept these as
the basis for explicit manual documentation and independent native fixtures;
do not call them universally canonical pentatonics. The full raw review is
retained alongside this file. Documentation and all-scale native acceptance
are still pending.

The predicted Lydian boundary issue requires native reproduction before a fix.
At C root, zero-based degrees -7,0,7 should snap C48,C60,C72 to B47,B59,B71
under nearest-pitch selection repeated across octaves. Source predicts50,62,71
because the candidate array starts above the lower boundary. Preserve the
rootless selection; investigate octave equivalence separately from MIDI bounds.

Correct one review statement: the requested vectors do contain an exact tie.
Melodic minor degree5 is A69; its selected G67 and B71 are equally distant.
The lower-pitch tie contract chooses67, as the review's Higher table already
states. The review's unsuccessful sequence of proposed tie examples is not a
test oracle. Verify the deployed official musicutil behavior independently.

Next: author all-ten-scale pentatonic fixtures from the reviewed literal table,
reproduce the Lydian boundary with actual controls and MIDI in both modes,
then isolate any correction with relevant unit/integration/behavior evidence.
Root/rotation/transpose interactions and full delivery remain incomplete.

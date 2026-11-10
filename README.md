# LIVYNTH

**Give Imagination Life.**

LIVYNTH is a long-term initiative to create realistic digital humans, facial and body animation, voice performances, and an automated cinematic-video studio.

## M001 — First Living Human

Our first measurable milestone is a 12–15 second vertical 1080×1920 talking-human MP4. We will reuse the tested morph-target architecture from the existing `our_avatar` project and avoid rebuilding a skeleton for a stationary talking bust.

This repository is being bootstrapped with an offline WAV-to-animation timeline and a Blender 4.5 rendering prototype. The actual photorealistic GLB is maintained in the local `our_avatar/assets/` directory, not committed here. The external audit reports 52 ARKit facial controls plus 15 visemes but no skeleton or embedded clips.

**Status:** architecture and pipeline implementation underway. A real Blender-rendered MP4 is not yet validated.

See the forthcoming `docs/M001.md` for implementation and acceptance tests.

"""Blender audio strip regression tests using an empty, false-y collection.

The real Windows/Blender video render is a separate integration gate.
"""
import unittest
from pathlib import Path
from types import SimpleNamespace

from video.render_talk import include_narration


class EmptyStrips:
    """Simulate bpy_prop_collection before any SequenceEditor strips exist."""
    def __init__(self):
        self.created = []

    def __len__(self):
        return len(self.created)

    def new_sound(self, name, filepath, channel, frame_start):
        sound = SimpleNamespace(name=name, filepath=filepath,
                                channel=channel, frame_start=frame_start,
                                volume=None)
        self.created.append(sound)
        return sound


class FakeScene:
    def __init__(self, *, strips=None, sequences=None):
        self.editor = SimpleNamespace()
        if strips is not None:
            self.editor.strips = strips
        if sequences is not None:
            self.editor.sequences = sequences
        self.render = SimpleNamespace(
            use_sequencer=False,
            ffmpeg=SimpleNamespace(audio_codec=None, audio_bitrate=None),
        )

    def sequence_editor_create(self):
        return self.editor


class BlenderNarrationTests(unittest.TestCase):
    def test_empty_current_strips_gets_first_sound(self):
        strips = EmptyStrips()
        self.assertFalse(bool(strips))  # Reproduces the old false-y bug.
        scene = FakeScene(strips=strips)
        path = Path("assets/voice.wav")
        include_narration(scene, path)
        self.assertEqual(len(strips.created), 1)
        sound = strips.created[0]
        self.assertEqual(sound.name, "Livynth Voice")
        self.assertEqual(sound.filepath, str(path.resolve()))
        self.assertEqual(sound.channel, 1)
        self.assertEqual(sound.frame_start, 1)
        self.assertEqual(sound.volume, 1)
        self.assertTrue(scene.render.use_sequencer)
        self.assertEqual(scene.render.ffmpeg.audio_codec, "AAC")
        self.assertEqual(scene.render.ffmpeg.audio_bitrate, 192)

    def test_fallback_to_legacy_sequences_only_when_strips_absent(self):
        legacy = EmptyStrips()
        scene = FakeScene(sequences=legacy)
        include_narration(scene, Path("voice.wav"))
        self.assertEqual(len(legacy.created), 1)
        self.assertTrue(scene.render.use_sequencer)

    def test_prefer_current_strips_even_when_falsey_and_legacy_exists(self):
        modern, legacy = EmptyStrips(), EmptyStrips()
        scene = FakeScene(strips=modern, sequences=legacy)
        include_narration(scene, Path("voice.wav"))
        self.assertEqual(len(modern.created), 1)
        self.assertEqual(len(legacy.created), 0)

    def test_fail_if_neither_collection_supported(self):
        scene = FakeScene()
        with self.assertRaisesRegex(RuntimeError, "missing strips collection"):
            include_narration(scene, Path("voice.wav"))
        self.assertFalse(scene.render.use_sequencer)


if __name__ == "__main__":
    unittest.main()

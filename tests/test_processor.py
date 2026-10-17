import subprocess
import tempfile
import unittest
from pathlib import Path

from processor import timestamp_srt, transcript_files, extract_mp3, make_wav, media_duration


class ProcessorTests(unittest.TestCase):
    def test_timestamp_rounding(self):
        self.assertEqual(timestamp_srt(0), "00:00:00,000")
        self.assertEqual(timestamp_srt(60.1234), "00:01:00,123")
        self.assertEqual(timestamp_srt(3599.9999), "01:00:00,000")

    def test_subtitles_skip_blank_and_number_in_order(self):
        txt, timed, srt = transcript_files([
            (0, 1.234, " Dzień dobry! "),
            (1.5, 2, "  "),
            (2.3, 3.4, "Co słychać?"),
        ])
        self.assertEqual(txt, "Dzień dobry!\nCo słychać?")
        self.assertIn("[00:00:00.000] Dzień dobry!", timed)
        self.assertIn("1\n00:00:00,000 --> 00:00:01,234\nDzień dobry!", srt)
        self.assertIn("2\n00:00:02,300 --> 00:00:03,400\nCo słychać?", srt)
        self.assertNotIn("\n3\n", srt)

    def test_ffmpeg_conversion_and_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wav = root / "test.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                            "-c:a", "pcm_s16le", str(wav)], check=True)
            mp3 = extract_mp3(wav, root / "test.mp3")
            self.assertTrue(mp3.stat().st_size > 0)
            prepared = make_wav(mp3, root / "prepared.wav")
            self.assertTrue(prepared.exists())
            self.assertAlmostEqual(media_duration(mp3), 1, delta=0.15)


if __name__ == "__main__":
    unittest.main()

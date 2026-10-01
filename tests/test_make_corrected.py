import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import make_corrected as mc


FIRST = "BV1kybV6DE47"
SECOND = "BV1Q6en6NEUo"


class CorrectionTests(unittest.TestCase):
    def test_course_rules_are_isolated(self):
        text = "外部 双机 一号 subversion gate"
        for video_id, expected in [
            (None, text),
            ("unknown", text),
            (FIRST, "外包 双击 一号 subversion gate"),
            (SECOND, "外部 双机 一卡通 subagent git"),
        ]:
            with self.subTest(video_id=video_id):
                self.assertEqual(mc.correct(text, video_id), expected)

    def test_existing_course_corrections(self):
        # Fixed expectations from the original global map for each course's terms.
        cases = [
            (FIRST, "GP16 GP5.6 fixed井三 井三 agency.md 测试用力",
             "GPT-6 GPT-5.6 fixes #3 #3 AGENTS.md 测试用例"),
            (SECOND, "get it work tree get it by sec REBASESTHSTH read me点MD L1号",
             "git worktree git bisect rebase stash README.md 一卡通"),
        ]
        for video_id, raw, expected in cases:
            with self.subTest(video_id=video_id):
                self.assertEqual(mc.correct(raw, video_id), expected)

    def test_common_rules_apply_to_every_video(self):
        for video_id in (None, "unknown", FIRST, SECOND):
            with self.subTest(video_id=video_id):
                self.assertEqual(mc.correct("chain of salt GPT5.6", video_id),
                                 "chain of thought GPT-5.6")

    def test_longest_match_across_common_and_video_rules(self):
        # GP5 is course-specific; GP5.6 is common. Applying the course first
        # would turn GP5.6 into GPT-5.6 and miss the longer override below.
        with patch.dict(mc.VIDEO_MAP[FIRST], {"GP5.6": "模型六"}):
            self.assertEqual(mc.correct("GP5.6 GP5", FIRST), "模型六 GPT-5")
        self.assertEqual(mc.correct("GP5.6", "unknown"), "GPT-5.6")

    def test_filler_cleanup_is_unchanged(self):
        for video_id in (None, "unknown", FIRST, SECOND):
            with self.subTest(video_id=video_id):
                self.assertEqual(mc.correct("呃我我我嗯就就写代码对吧", video_id),
                                 "我就写代码")
                self.assertEqual(mc.correct("嗯呃啊", video_id), "")
                self.assertEqual(mc.correct("工作工作工作点点点", video_id),
                                 "工作工作工作点点点")

    def test_cli_all_passes_video_id_and_drops_filler_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            for video_id in (FIRST, SECOND, "unknown"):
                folder = Path(tmp, "output", video_id)
                folder.mkdir(parents=True)
                segments = [
                    {"start": "00:00:01", "text": "好的"},
                    {"start": "00:00:02", "text": "嗯呃啊"},
                    {"start": "01:02:03", "text": "外部 双机 一号"},
                    {"start": "00:00:04", "text": "呃我我嗯写代码对吧"},
                ]
                (folder / "transcript.json").write_text(
                    json.dumps({"segments": segments}), encoding="utf-8")
            with patch.object(mc, "BASE", tmp), \
                 patch("sys.argv", ["make_corrected.py", "--all"]), \
                 contextlib.redirect_stdout(io.StringIO()) as stdout:
                mc.main()
            for video_id, expected in [
                (FIRST, "外包 双击 一号"),
                (SECOND, "外部 双机 一卡通"),
                ("unknown", "外部 双机 一号"),
            ]:
                with self.subTest(video_id=video_id):
                    result = Path(tmp, "output", video_id,
                                  "transcript.corrected.txt").read_text(encoding="utf-8")
                    self.assertEqual(result, f"[62:03] {expected}\n[00:04] 我写代码\n")
            self.assertEqual(stdout.getvalue().count("删除口癖段 2"), 3)


if __name__ == "__main__":
    unittest.main()

"""Exercise ZIP selection, range seeking, corruption, and traversal refusal."""
import io
import unittest
import zipfile

from fetch_mp3d_subset import RangeFile, selected_members


class SubsetTest(unittest.TestCase):
    def test_remote_zip_selects_and_extracts_only_requested_scene(self):
        buf = io.BytesIO()
        data = b"scene bytes" * 5000
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("mp3d/wanted/wanted.glb", data)
            archive.writestr("mp3d/other/other.glb", b"unneeded")
        payload = buf.getvalue()
        reader = RangeFile(len(payload), lambda start, end: payload[start:end + 1])
        with zipfile.ZipFile(reader) as archive:
            selected = selected_members(archive.infolist(), {"wanted"})
            self.assertEqual([i.filename for i in selected], ["mp3d/wanted/wanted.glb"])
            self.assertEqual(archive.read(selected[0]), data)
            with self.assertRaisesRegex(ValueError, "missing"):
                selected_members(archive.infolist(), {"missing"})

    def test_short_range_does_not_advance_cursor(self):
        reader = RangeFile(100, lambda start, end: b"x")
        reader.seek(10)
        with self.assertRaisesRegex(RuntimeError, "Incomplete"):
            reader.read(5)
        self.assertEqual(reader.tell(), 10)

    def test_traversal_refused(self):
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            selected_members([zipfile.ZipInfo("mp3d/wanted/../../escape")], {"wanted"})


if __name__ == "__main__":
    unittest.main()

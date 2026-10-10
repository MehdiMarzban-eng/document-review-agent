"""Exercise the actual .NET extractor, including Windows' legacy path boundary."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile


@unittest.skipUnless(os.name == "nt", "Windows installer")
class WindowsInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.exe = cls.root / "extractor.exe"
        compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
        source = Path(__file__).resolve().parents[1] / "local/windows_setup.cs"
        references = ("System.Windows.Forms", "System.Drawing", "System.IO.Compression",
                      "System.IO.Compression.FileSystem", "System.Web.Extensions", "Microsoft.CSharp")
        subprocess.run([str(compiler), "/nologo", "/target:winexe", f"/out:{cls.exe}",
                        *[f"/reference:{name}.dll" for name in references], str(source)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_extracts_files_beyond_260_characters(self):
        archive = self.root / "deep.zip"
        relative = "/".join(["nested" * 8] * 6) + "/result.txt"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("Document Review Local/" + relative, "long path works")
        destination = self.root / "installed"
        subprocess.run([str(self.exe), "--test-extract", str(archive), str(destination)], check=True)
        target = str(destination / relative)
        self.assertGreater(len(target), 260)
        self.assertEqual(Path("\\\\?\\" + target).read_text(), "long path works")

    def test_rejects_archive_escape_and_alternate_streams(self):
        for index, name in enumerate(("Document Review Local/../escape.txt",
                                      "Document Review Local/C:/escape.txt",
                                      "Document Review Local/file.txt:stream",
                                      "Other Root/file.txt")):
            with self.subTest(name=name):
                archive = self.root / f"bad-{index}.zip"
                with zipfile.ZipFile(archive, "w") as z:
                    z.writestr(name, "bad")
                result = subprocess.run([str(self.exe), "--test-extract", str(archive),
                                         str(self.root / f"rejected-{index}")])
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "escape.txt").exists())

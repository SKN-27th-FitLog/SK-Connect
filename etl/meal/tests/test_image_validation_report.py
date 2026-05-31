import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import render_image_validation_report as report_module


def test_render_report_outputs_keep_and_drop_cards():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        tmp_path = Path(temp_dir)
        input_path = tmp_path / "image_validation.jsonl"
        output_path = tmp_path / "report.html"
        record = {
            "store": {"name": "Seoul Soup"},
            "images": [
                {
                    "url": "https://cdn.example.com/keep.webp",
                    "validation": {
                        "group_id": "imggrp-001",
                        "group_order": 2,
                        "nearest_similarity": 0.734,
                    },
                }
            ],
            "dropped_images": [
                {
                    "url": "https://cdn.example.com/drop.webp",
                    "validation": {
                        "reason": "NO_SIMILAR_IMAGE_IN_STORE",
                        "nearest_similarity": 0.41,
                    },
                }
            ],
        }
        input_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

        report_module.render_report(input_path, output_path)

        html = output_path.read_text(encoding="utf-8")
        assert "Seoul Soup" in html
        assert "KEEP" in html
        assert "DROP" in html
        assert "imggrp-001" in html
        assert "2" in html
        assert "0.734" in html
        assert "NO_SIMILAR_IMAGE_IN_STORE" in html
        assert "https://cdn.example.com/keep.webp" in html
        assert "https://cdn.example.com/drop.webp" in html
        assert '<img src="https://cdn.example.com/keep.webp"' in html
        assert '<img src="https://cdn.example.com/drop.webp"' in html


def test_report_script_accepts_input_and_output_arguments():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        tmp_path = Path(temp_dir)
        input_path = tmp_path / "image_validation.jsonl"
        output_path = tmp_path / "report.html"
        record = {
            "store": {"name": "Argument Store"},
            "images": [{"url": "https://cdn.example.com/keep.webp"}],
            "dropped_images": [],
        }
        input_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

        exit_code = report_module.main(["--input", str(input_path), "--output", str(output_path)])

        assert exit_code == 0
        assert "Argument Store" in output_path.read_text(encoding="utf-8")

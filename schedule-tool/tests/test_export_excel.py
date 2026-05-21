import unittest
import zipfile
from io import BytesIO

import app


class ExportExcelTests(unittest.TestCase):
    def test_filters_export_subjects_by_current_filter_values(self):
        subjects = [
            {
                "ma_hp": "LAW101",
                "ten_hoc_phan": "Mon A",
                "giang_vien": "GV A",
                "lop_hoc": ["LH26B2DL", "LHK50DL"],
            },
            {
                "ma_hp": "LAW102",
                "ten_hoc_phan": "Mon B",
                "giang_vien": "GV B",
                "lop_hoc": ["LLT50DLTC"],
            },
        ]

        filtered = app.filter_export_subjects(
            subjects,
            class_filter="lh26b2dl",
            subject_filter="mon a",
            teacher_filter="gv a",
        )

        self.assertEqual([subject["ma_hp"] for subject in filtered], ["LAW101"])

    def test_build_export_xlsx_returns_valid_workbook_package(self):
        subjects = [
            {
                "stt": 1,
                "ma_hp": "LAW101",
                "ten_hoc_phan": "Mon A",
                "tc": 3,
                "giang_vien": "GV A",
                "phong_hoc": "A101",
                "thoi_gian": "01/06/2026 - Sang",
                "lop_hoc": ["LH26B2DL"],
                "trang_thai": "Chua hoc",
            }
        ]

        workbook_bytes = app.build_export_xlsx(subjects)

        with zipfile.ZipFile(BytesIO(workbook_bytes)) as workbook:
            self.assertIn("xl/workbook.xml", workbook.namelist())
            self.assertIn("xl/styles.xml", workbook.namelist())
            xml_payload = "\n".join(
                workbook.read(name).decode("utf-8")
                for name in workbook.namelist()
                if name.endswith(".xml")
            )

        self.assertIn("LAW101", xml_payload)
        self.assertIn("Chua hoc", xml_payload)

    def test_export_route_downloads_filtered_xlsx(self):
        original_prepare_data_for_view = app.prepare_data_for_view
        app.prepare_data_for_view = lambda: {
            "subjects": [
                {
                    "ma_hp": "LAW101",
                    "ten_hoc_phan": "Mon A",
                    "giang_vien": "GV A",
                    "lop_hoc": ["LH26B2DL"],
                },
                {
                    "ma_hp": "LAW102",
                    "ten_hoc_phan": "Mon B",
                    "giang_vien": "GV B",
                    "lop_hoc": ["LLT50DLTC"],
                },
            ]
        }

        try:
            client = app.app.test_client()
            response = client.get("/api/export.xlsx?class=lh26b2dl")
        finally:
            app.prepare_data_for_view = original_prepare_data_for_view

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        with zipfile.ZipFile(BytesIO(response.data)) as workbook:
            xml_payload = "\n".join(
                workbook.read(name).decode("utf-8")
                for name in workbook.namelist()
                if name.endswith(".xml")
            )

        self.assertIn("LAW101", xml_payload)
        self.assertNotIn("LAW102", xml_payload)


if __name__ == "__main__":
    unittest.main()

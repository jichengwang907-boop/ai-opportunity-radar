from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.product_data_cleaner import clean_product_file, parse_price, parse_stock


class ProductDataCleanerTests(unittest.TestCase):
    def test_cleans_chinese_product_sheet_and_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            source = tmp_dir / "products.csv"
            source.write_text(
                "商品标题,SKU,价格,库存,类目,图片链接,规格,商品链接,商品描述\n"
                "便携榨汁杯 400ml,PJ-400,¥59.9,120,厨房电器,https://example.com/pj.jpg,400ml 白色,https://example.com/pj,USB充电\n"
                "便携榨汁杯 400ml,PJ-400,59.9元,80,厨房电器,https://example.com/pj-blue.jpg,400ml 蓝色,https://example.com/pj-blue,同款蓝色\n"
                "智能宠物喂食器,PF-01,199,35,宠物用品,,2L,https://example.com/pf,定时定量\n"
                "无线蓝牙耳机,,abc,not-stock,数码配件,not-a-url,黑色,https://example.com/earbud,入门款\n",
                encoding="utf-8-sig",
            )
            out_dir = tmp_dir / "out"

            summary = clean_product_file(source, out_dir)

            self.assertEqual(summary["input_rows"], 4)
            self.assertEqual(summary["cleaned_rows"], 4)
            self.assertEqual(summary["ready_rows"], 0)
            self.assertEqual(summary["field_mapping"]["product_name"], "商品标题")
            self.assertEqual(summary["field_mapping"]["sku"], "SKU")
            self.assertTrue((out_dir / "summary.md").exists())
            self.assertTrue((out_dir / "field_mapping.json").exists())

            with (out_dir / "cleaned_products.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                cleaned_rows = list(csv.DictReader(handle))
            self.assertEqual(cleaned_rows[0]["currency"], "CNY")
            self.assertEqual(cleaned_rows[0]["price"], "59.9")
            self.assertEqual(cleaned_rows[0]["listing_title"], "便携榨汁杯 400ml 400ml 白色")
            self.assertEqual(cleaned_rows[0]["review_status"], "needs_review")

            with (out_dir / "issues.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                issue_codes = [row["code"] for row in csv.DictReader(handle)]
            self.assertIn("duplicate_sku", issue_codes)
            self.assertIn("missing_image_url", issue_codes)
            self.assertIn("missing_sku", issue_codes)
            self.assertIn("invalid_price", issue_codes)
            self.assertIn("invalid_image_url", issue_codes)
            self.assertIn("invalid_stock", issue_codes)

    def test_parse_price_and_stock_edge_cases(self) -> None:
        self.assertEqual(parse_price("USD 1,299.50"), (1299.5, "USD", True))
        self.assertEqual(parse_price("-1"), (-1.0, "", False))
        self.assertEqual(parse_price("价格待定"), (None, "", False))
        self.assertEqual(parse_stock("1,200 件"), (1200, True))
        self.assertEqual(parse_stock("-3"), (-3, False))
        self.assertEqual(parse_stock("现货"), (None, False))


if __name__ == "__main__":
    unittest.main()

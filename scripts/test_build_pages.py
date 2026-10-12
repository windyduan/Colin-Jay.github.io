"""Unit tests for GitHub Pages-compatible relative paths."""
import unittest
from pathlib import Path

from build_pages import relative_root, rewrite


class RebaseTests(unittest.TestCase):
    def test_depth_for_home_and_nested_article(self):
        self.assertEqual(relative_root(Path("index.html")), "./")
        self.assertEqual(relative_root(Path("about/index.html")), "../")
        self.assertEqual(
            relative_root(Path("2020/10/08/PAT-AdvancedLevel1066/index.html")),
            "../../../../",
        )

    def test_rebases_static_files_and_internal_links(self):
        html = '''<head></head><body>
<link rel="stylesheet" href="/css/bootstrap.min.css">
<script src="/js/search.js"></script>
<img src="/img/avatar.jpg">
<a href="/tags/#pat">Tags</a>
<a href="//cdn.example.com/external.css">External</a>
<img src="https://example.org/external.png">
<div style="background-image:url('/img/header_img/archive-bg.jpg')"></div>
</body>'''
        result = rewrite(html, "../../../../", True)
        self.assertIn('href="../../../../css/bootstrap.min.css"', result)
        self.assertIn('src="../../../../js/search.js"', result)
        self.assertIn('src="../../../../img/avatar.jpg"', result)
        self.assertIn('href="../../../../tags/#pat"', result)
        self.assertIn('url(\'../../../../img/header_img/archive-bg.jpg\')', result)
        self.assertIn('href="//cdn.example.com/external.css"', result)
        self.assertIn('src="https://example.org/external.png"', result)
        self.assertIn('href="../../../../css/blog-refresh.css"', result)
        self.assertIn('href="../../../../css/blog-interior.css"', result)

    def test_search_script_rebases_without_affecting_external_urls(self):
        sample = '<script>var search_path = "search.xml"; var path = "/" + search_path;</script>'
        self.assertIn(
            'var path = "../../" + search_path;',
            rewrite(sample, "../../", True),
        )

    def test_rewrites_css_root_assets(self):
        raw = """body{background:url('/img/bg.jpg')} .icon{background:url(//cdn.example.org/a.png)}"""
        changed = rewrite(raw, "../", False)
        self.assertIn("url('../img/bg.jpg')", changed)
        self.assertIn("url(//cdn.example.org/a.png)", changed)

    def test_homepage_link_is_not_injected_twice(self):
        page = '<head><link href="./css/blog-refresh.css"></head>'
        changed = rewrite(page, "./", True)
        self.assertEqual(changed.count("blog-refresh.css"), 1)
        self.assertEqual(changed.count("blog-interior.css"), 1)


if __name__ == "__main__":
    unittest.main()

"""
Unit tests del motor de detección (sin red).

Cubren tres cosas que antes solo se verificaban a mano:
  1. Detección positiva por categoría (frontend, backend, cdn, server).
  2. El cap de scoring por categoría (MAX_CATEGORY_MATCHES).
  3. Los falsos positivos que se corrigieron al endurecer las firmas.
"""
from config.constants import MAX_CATEGORY_MATCHES
from detectors.detector_factory import DetectorFactory
from detectors.frontend_detector import FrontendDetector

factory = DetectorFactory()


def names(results):
    return {r["name"] for r in results}


# ── Cap de scoring (unidad sobre BaseDetector) ────────────────────────────────

class TestScoringCap:
    def test_score_is_capped_per_category(self):
        det = FrontendDetector({})
        patterns = ["aa", "bb", "cc", "dd"]      # 4 patrones
        haystack = "aa bb cc dd"                 # los 4 coinciden
        score, evidence = det._scan_text(patterns, 10, haystack, "p '", "'")
        # El score se topa en MAX_CATEGORY_MATCHES, no escala con los 4 matches.
        assert score == 10 * MAX_CATEGORY_MATCHES
        # ...pero la evidencia sí lista todas las coincidencias.
        assert len(evidence) == 4

    def test_no_weight_means_no_score(self):
        det = FrontendDetector({})
        score, evidence = det._scan_text(["aa"], 0, "aa", "p")
        assert score == 0
        assert evidence == []


# ── Detección positiva ────────────────────────────────────────────────────────

class TestFrontend:
    def setup_method(self):
        self.det = factory.create("frontend")

    def test_react_from_script_src(self):
        res = self.det.detect(html="", headers={}, scripts=["/static/react-dom.production.min.js"])
        assert "React" in names(res)

    def test_jquery_from_script_src(self):
        res = self.det.detect(html="", headers={}, scripts=["https://code.jquery.com/jquery-3.6.0.min.js"])
        assert "jQuery" in names(res)


class TestBackend:
    def setup_method(self):
        self.det = factory.create("backend")

    def test_rails_from_html_markers(self):
        html = '<form><input name="authenticity_token"><a data-pjax="true">x</a></form>'
        res = self.det.detect(html=html, headers={}, scripts=[], cookies={})
        assert "Ruby on Rails" in names(res)


class TestServer:
    def setup_method(self):
        self.det = factory.create("server")

    def test_nginx_from_server_header(self):
        res = self.det.detect(html="", headers={"Server": "nginx/1.25.3"}, scripts=[])
        assert "Nginx" in names(res)

    def test_apache_from_server_header(self):
        res = self.det.detect(html="", headers={"Server": "Apache/2.4.57 (Unix)"}, scripts=[])
        assert "Apache" in names(res)


class TestCDN:
    def setup_method(self):
        self.det = factory.create("cdn")

    def test_fastly_from_header_and_ip(self):
        res = self.det.detect(
            html="", headers={"x-served-by": "cache-bog123"}, scripts=[],
            nameservers=[], server_ip="151.101.0.223",
        )
        assert "Fastly" in names(res)


# ── Falsos positivos corregidos (regresión) ───────────────────────────────────

class TestFalsePositives:
    def test_django_not_detected_from_generic_headers_only(self):
        # x-frame-options / x-content-type-options los usa cualquier framework serio.
        det = factory.create("backend")
        headers = {"X-Frame-Options": "SAMEORIGIN", "X-Content-Type-Options": "nosniff"}
        res = det.detect(html="", headers=headers, scripts=[], cookies={})
        assert "Django" not in names(res)

    def test_remix_not_detected_from_react_router_dependency(self):
        # React Router v6 importa @remix-run/router sin ser el framework Remix.
        det = factory.create("frontend")
        res = det.detect(
            html="", headers={}, scripts=[],
            js_contents=['import {createBrowserRouter} from "@remix-run/router";'],
            resources=[],
        )
        assert "Remix" not in names(res)

    def test_angular_not_detected_from_substring_trap(self):
        # "ngcomponent" ⊂ "RenderingComponent" — ya no debe disparar Angular.
        det = factory.create("frontend")
        res = det.detect(
            html="", headers={}, scripts=[],
            js_contents=["class RenderingComponent extends Base {}"],
            resources=[],
        )
        assert "Angular" not in names(res)

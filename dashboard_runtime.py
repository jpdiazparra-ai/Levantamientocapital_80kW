"""Load the current Block 4 source after a Streamlit application update."""
import hashlib
import importlib
from pathlib import Path
import sys
from threading import RLock

APP_RELEASE = '2026.11.13.1'
_MODULES = ('display_currency', 'timeline_scroll', 'capital_charts', 'commercial_report', 'commercial_comparison', 'commercial_analysis', 'valuation_data', 'valuation_finance', 'lcoe_finance', 'valuation_lcoe', 'valuation_interactive', 'valuation_costs', 'valuation_report', 'valuation_view', 'valuation80_data', 'valuation80_project', 'valuation80_unit', 'valuation80_lcoe', 'valuation80_report', 'market_analytics', 'market_pdf', 'market_study', 'valuation80_view', 'valuation10_data', 'valuation10_costs', 'valuation10_project', 'valuation10_unit', 'valuation10_lcoe', 'valuation10_report', 'valuation10_view', 'analysis_option')
_ROOT = Path(__file__).resolve().parent
_reload_lock = RLock()
_loaded_revision = None
_renderer = None


def dashboard_revision():
    digest = hashlib.sha256()
    for name in _MODULES:
        digest.update(name.encode('utf-8'))
        digest.update((_ROOT / f'{name}.py').read_bytes())
    return digest.hexdigest()


def render_analysis_option(refresh_nonce, render_navigation):
    global _loaded_revision, _renderer
    revision = dashboard_revision()
    with _reload_lock:
        if revision != _loaded_revision:
            # Reload dependencies first: rerunning app.py alone can retain their
            # previous functions in Python's module cache on a running server.
            importlib.invalidate_caches()
            for name in _MODULES:
                module = importlib.reload(sys.modules[name]) if name in sys.modules else importlib.import_module(name)
            _renderer = module.render_analysis_option
            _loaded_revision = revision
        renderer = _renderer
    return renderer(refresh_nonce, render_navigation)

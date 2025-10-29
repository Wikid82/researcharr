import os
from pathlib import Path

from researcharr.plugins.registry import PluginRegistry


def test_discover_plugins_and_categories():
    root = Path(__file__).resolve().parents[1]
    plugins_dir = os.path.join(root, "plugins")
    reg = PluginRegistry()
    reg.discover_local(plugins_dir)

    # Some expected plugin names from the example plugins
    expected = {"radarr", "sonarr", "nzbget", "prowlarr", "jackett", "apprise"}
    found = set(reg.list_plugins())
    assert expected & found, f"expected some known plugins in registry, found: {found}"

    # Check categories are set for a few known plugins
    p_radarr = reg.get("radarr")
    assert p_radarr is not None and getattr(p_radarr, "category", None) == "media"
    p_nzb = reg.get("nzbget")
    assert p_nzb is not None and getattr(p_nzb, "category", None) == "clients"
    p_prow = reg.get("prowlarr")
    assert p_prow is not None and getattr(p_prow, "category", None) == "scrapers"

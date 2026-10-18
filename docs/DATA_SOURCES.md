# Public data sources

The supported public pipeline is `src/open_results.py`, `src/open_events.py`, `src/forecast_lab.py` and `src/build_site.py`.

OpenFootball provides CC0 results. The Pappalardo/Wyscout research release provides CC BY 4.0 historical 2017/18 events. Exact source IDs, checksums and attribution are in `data/open/source_registry.json` and `data/open/wyscout_sources.json`.

The scheduled workflow does not fetch ESPN, Football-Data.co.uk or StatsBomb. Legacy research scripts are excluded from the public pipeline and require separate source authorization. Data accessibility alone is not redistribution permission. Source freshness and independent verification limitations are described in [DATA_QUALITY.md](DATA_QUALITY.md).

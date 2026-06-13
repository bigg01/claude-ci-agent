#!/usr/bin/env python3
"""Generate the Kibana saved-objects NDJSON for the Claude CI Agent dashboard.

Builds two data views (logs + metrics) and a dashboard with cost, tool, status,
and recent-execution panels — matching the fields the OTel collector indexes.
Run `local/kibana-setup.sh` to import the output into a running Kibana.
"""
import json
import pathlib

DV_LOGS = "claude-agent-logs"
DV_METRICS = "claude-agent-metrics"
SRC = {"query": {"query": "", "language": "kuery"}, "filter": [],
       "indexRefName": "kibanaSavedObjectMeta.searchSourceJSON.index"}


def obj(id_, type_, attributes, references=None):
    return {"id": id_, "type": type_, "attributes": attributes,
            "references": references or [], "managed": False}


def dv(id_, title):
    return obj(id_, "index-pattern", {"title": title, "timeFieldName": "@timestamp"})


def vis(id_, title, dv_id, vis_state):
    return obj(id_, "visualization", {
        "title": title,
        "visState": json.dumps(vis_state),
        "uiStateJSON": "{}",
        "description": "",
        "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(SRC)},
    }, [{"name": "kibanaSavedObjectMeta.searchSourceJSON.index",
         "type": "index-pattern", "id": dv_id}])


def metric_vis(id_, title, dv_id, agg_type, field=None, fmt=None):
    agg = {"id": "1", "enabled": True, "type": agg_type, "schema": "metric",
           "params": {"field": field} if field else {}}
    return vis(id_, title, dv_id, {
        "title": title, "type": "metric", "aggs": [agg],
        "params": {"addTooltip": True, "addLegend": False, "type": "metric",
                   "metric": {"percentageMode": False, "metricColorMode": "None",
                              "colorsRange": [{"from": 0, "to": 100000}],
                              "labels": {"show": True}, "invertColors": False,
                              "style": {"bgColor": False, "labelColor": False,
                                        "subText": "", "fontSize": 48}}}})


def pie_vis(id_, title, dv_id, field):
    return vis(id_, title, dv_id, {
        "title": title, "type": "pie",
        "aggs": [
            {"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}},
            {"id": "2", "enabled": True, "type": "terms", "schema": "segment",
             "params": {"field": field, "size": 10, "order": "desc", "orderBy": "1"}},
        ],
        "params": {"type": "pie", "addTooltip": True, "addLegend": True,
                   "legendPosition": "right", "isDonut": True,
                   "labels": {"show": False, "values": True, "last_level": True, "truncate": 100}}})


def bar_over_time(id_, title, dv_id, split_field):
    return vis(id_, title, dv_id, {
        "title": title, "type": "histogram",
        "aggs": [
            {"id": "1", "enabled": True, "type": "count", "schema": "metric", "params": {}},
            {"id": "2", "enabled": True, "type": "date_histogram", "schema": "segment",
             "params": {"field": "@timestamp", "useNormalizedEsInterval": True,
                        "interval": "auto", "drop_partials": False, "min_doc_count": 1}},
            {"id": "3", "enabled": True, "type": "terms", "schema": "group",
             "params": {"field": split_field, "size": 5, "order": "desc", "orderBy": "1"}},
        ],
        "params": {"type": "histogram", "grid": {"categoryLines": False},
                   "categoryAxes": [{"id": "CategoryAxis-1", "type": "category",
                       "position": "bottom", "show": True, "scale": {"type": "linear"},
                       "labels": {"show": True, "filter": True, "truncate": 100}, "title": {}}],
                   "valueAxes": [{"id": "ValueAxis-1", "name": "LeftAxis-1", "type": "value",
                       "position": "left", "show": True, "scale": {"type": "linear", "mode": "normal"},
                       "labels": {"show": True, "rotate": 0, "filter": False, "truncate": 100},
                       "title": {"text": "Count"}}],
                   "seriesParams": [{"show": True, "type": "histogram", "mode": "stacked",
                       "data": {"label": "Count", "id": "1"}, "valueAxis": "ValueAxis-1",
                       "drawLinesBetweenPoints": True, "lineWidth": 2, "showCircles": True}],
                   "addTooltip": True, "addLegend": True, "legendPosition": "right",
                   "times": [], "addTimeMarker": False, "labels": {"show": False}}})


def table_cost(id_, title, dv_id):
    return vis(id_, title, dv_id, {
        "title": title, "type": "table",
        "aggs": [
            {"id": "1", "enabled": True, "type": "sum", "schema": "metric",
             "params": {"field": "cicd.claude.run.cost_usd"}},
            {"id": "3", "enabled": True, "type": "max", "schema": "metric",
             "params": {"field": "cicd.claude.run.tokens"}},
            {"id": "2", "enabled": True, "type": "terms", "schema": "bucket",
             "params": {"field": "run.id", "size": 50, "order": "desc", "orderBy": "1"}},
        ],
        "params": {"perPage": 10, "showPartialRows": False, "showMetricsAtAllLevels": False,
                   "showTotal": True, "totalFunc": "sum", "percentageCol": ""}})


def saved_search(id_, title, dv_id, columns):
    return obj(id_, "search", {
        "title": title, "description": "", "columns": columns,
        "sort": [["@timestamp", "desc"]],
        "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(SRC)},
    }, [{"name": "kibanaSavedObjectMeta.searchSourceJSON.index",
         "type": "index-pattern", "id": dv_id}])


def panel(i, w, h, x, y, ref):
    return {"version": "8.15.0", "type": "visualization" if ref != "search" else "search",
            "gridData": {"x": x, "y": y, "w": w, "h": h, "i": str(i)},
            "panelIndex": str(i), "embeddableConfig": {"enhancements": {}},
            "panelRefName": f"panel_{i}"}


def dashboard(panels, refs):
    return obj("claude-agent-overview", "dashboard", {
        "title": "Claude CI Agent — Overview",
        "description": "Runs, tool activity, status, and Anthropic cost for the Claude CI agent.",
        "panelsJSON": json.dumps(panels),
        "optionsJSON": json.dumps({"useMargins": True, "syncColors": False, "hidePanelTitles": False}),
        "timeRestore": True,
        "timeFrom": "now-7d", "timeTo": "now",
        "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})},
    }, refs)


def main():
    objects = [
        dv("cca-logs", f"{DV_LOGS}*"),
        dv("cca-metrics", "metrics-generic-default*"),
        metric_vis("cca-v-events", "Tool events", "cca-logs", "count"),
        metric_vis("cca-v-avgcost", "Avg run cost (USD)", "cca-metrics", "avg",
                   "cicd.claude.run.cost_usd"),
        metric_vis("cca-v-totcost", "Total cost (USD)", "cca-metrics", "sum",
                   "cicd.claude.run.cost_usd"),
        bar_over_time("cca-v-overtime", "Tool events over time (by status)", "cca-logs",
                      "Attributes.status.keyword"),
        pie_vis("cca-v-bytool", "Events by tool", "cca-logs", "Attributes.tool.name.keyword"),
        table_cost("cca-v-costbyrun", "Cost & tokens by run", "cca-metrics"),
        saved_search("cca-s-recent", "Recent tool executions (scrubbed)", "cca-logs",
                     ["Attributes.tool.name", "Attributes.status",
                      "Attributes.ci.flavor", "Attributes.duration_ms", "Body"]),
    ]

    layout = [
        ("cca-v-events", "visualization", 0, 0, 12, 8),
        ("cca-v-avgcost", "visualization", 12, 0, 12, 8),
        ("cca-v-totcost", "visualization", 24, 0, 12, 8),
        ("cca-v-bytool", "visualization", 36, 0, 12, 16),
        ("cca-v-overtime", "visualization", 0, 8, 36, 15),
        ("cca-v-costbyrun", "visualization", 0, 23, 24, 13),
        ("cca-s-recent", "search", 24, 23, 24, 13),
    ]
    panels, refs = [], []
    for i, (oid, otype, x, y, w, h) in enumerate(layout, 1):
        panels.append({
            "version": "8.15.0",
            "gridData": {"x": x, "y": y, "w": w, "h": h, "i": str(i)},
            "panelIndex": str(i), "embeddableConfig": {"enhancements": {}},
            "panelRefName": f"panel_{i}",
        })
        refs.append({"name": f"panel_{i}", "type": otype, "id": oid})
    objects.append(dashboard(panels, refs))

    out = pathlib.Path(__file__).parent / "kibana-dashboard.ndjson"
    out.write_text("\n".join(json.dumps(o) for o in objects) + "\n")
    print(f"wrote {out} ({len(objects)} objects)")


if __name__ == "__main__":
    main()

---
icon: lucide/network
---

# Architecture

Both CI flavors drive the same rootless, unprivileged sandbox container, which
emits OTLP telemetry to a collector sidecar and on to Elastic.

**The sandbox is the job container the runner starts** — not a wrapper this
project adds. The GitLab Runner runs the pipeline job *inside* the `claude-agent`
image (its container/Kubernetes executor), and `claude` runs directly as that
container's process. What provides the container varies by where the runner
lives: rootless **Podman** on a CI runner, or the **Kubernetes CRI** (e.g. CRI-O)
when the runner is a self-hosted one on **OpenShift** — where the `restricted-v2`
SCC enforces the non-root, no-escalation boundary. Claude is never wrapped in a
nested `podman run`.

The diagram traces one run. The CI platform starts a **Kubernetes Pod / CI job**
holding two sibling containers that share `localhost`: the **agent sandbox** (the
`claude-agent` image — where the Claude CLI runs) and the **OTel Collector
sidecar**. The agent emits OTLP telemetry to the sidecar, which scrubs secrets and
exports to **Elastic**; an optional **LLM Gateway** sits between the agent and the
**creation** and **review** models (which can be different models or vendors).

Nested Podman isn't drawn because it's incidental to the picture: it's used only
where needed — to start the sidecar, and for `podman build`/`run` when a task
builds or tests app images (rootless-in-rootless). Claude orchestrates those from
the sandbox; it never runs *inside* them. See **Nested child containers** below.

<div class="mxgraph" style="max-width:100%;border:1px solid transparent;" data-mxgraph="{&quot;dark&quot;: &quot;auto&quot;, &quot;highlight&quot;: &quot;#25e8ff&quot;, &quot;nav&quot;: true, &quot;resize&quot;: true, &quot;toolbar&quot;: &quot;zoom layers&quot;, &quot;xml&quot;: &quot;&lt;mxfile host=\&quot;65bd71144e\&quot;&gt;\n    &lt;diagram id=\&quot;ci-arch\&quot; name=\&quot;CI Architecture\&quot;&gt;\n        &lt;mxGraphModel dx=\&quot;1269\&quot; dy=\&quot;1061\&quot; grid=\&quot;1\&quot; gridSize=\&quot;10\&quot; guides=\&quot;1\&quot; tooltips=\&quot;1\&quot; connect=\&quot;1\&quot; arrows=\&quot;1\&quot; fold=\&quot;1\&quot; page=\&quot;1\&quot; pageScale=\&quot;1\&quot; pageWidth=\&quot;1169\&quot; pageHeight=\&quot;826\&quot; math=\&quot;0\&quot; shadow=\&quot;0\&quot;&gt;\n            &lt;root&gt;\n                &lt;mxCell id=\&quot;0\&quot;/&gt;\n                &lt;mxCell id=\&quot;1\&quot; parent=\&quot;0\&quot;/&gt;\n                &lt;mxCell id=\&quot;title\&quot; value=\&quot;Multi-Agent / OTel CI Architecture\&quot; style=\&quot;text;html=1;align=center;verticalAlign=middle;fontSize=20;fontStyle=1;fontColor=#25e8ff;fontFamily=Orbitron;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;360\&quot; y=\&quot;16\&quot; width=\&quot;440\&quot; height=\&quot;36\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;gitlab\&quot; value=\&quot;GitLab CI\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#071018;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=top;spacingTop=8;fontStyle=1;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;40\&quot; y=\&quot;150\&quot; width=\&quot;210\&quot; height=\&quot;110\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;github\&quot; value=\&quot;GitHub Actions\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#071018;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=top;spacingTop=8;fontStyle=1;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;40\&quot; y=\&quot;300\&quot; width=\&quot;210\&quot; height=\&quot;110\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;pod\&quot; value=\&quot;Kubernetes Pod / CI job  \u00b7  shared localhost\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#03121a;strokeColor=light-dark(#24ff50, #006a7e);fontColor=#9af6ff;fontFamily=Orbitron;align=center;verticalAlign=top;spacingTop=8;fontStyle=1;dashed=1;dashPattern=6 4;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;290\&quot; y=\&quot;92\&quot; width=\&quot;660\&quot; height=\&quot;348\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;sandbox\&quot; value=\&quot;Gitlab-runner Sandbox  \u00b7  claude-agent image\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#05101a;strokeColor=#FF9933;fontColor=#25e8ff;fontFamily=Orbitron;align=center;verticalAlign=top;spacingTop=8;fontStyle=1;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;310\&quot; y=\&quot;140\&quot; width=\&quot;420\&quot; height=\&quot;190\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;agent\&quot; value=\&quot;Claude CLI runs here\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#0a1c26;strokeColor=light-dark(#ff24ed, #006a7e);fontColor=#e7feff;fontFamily=Rajdhani;align=center;verticalAlign=middle;fontStyle=1;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;328\&quot; y=\&quot;180\&quot; width=\&quot;384\&quot; height=\&quot;60\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;otelflags\&quot; value=\&quot;OTel telemetry enabled\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#071018;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=middle;dashed=1;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;328\&quot; y=\&quot;262\&quot; width=\&quot;384\&quot; height=\&quot;40\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;otel\&quot; value=\&quot;OTel Collector&amp;#xa;localhost:4318\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#08161e;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=middle;fontStyle=1;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;752\&quot; y=\&quot;186\&quot; width=\&quot;180\&quot; height=\&quot;124\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;elastic\&quot; value=\&quot;Elastic\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#08161e;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=middle;fontStyle=1;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;1000\&quot; y=\&quot;200\&quot; width=\&quot;150\&quot; height=\&quot;110\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;gateway\&quot; value=\&quot;LLM Gateway (optional)\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#1a1206;strokeColor=#ff9d2e;fontColor=#ff9d2e;fontFamily=Rajdhani;align=center;verticalAlign=middle;fontStyle=1;dashed=1;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;310\&quot; y=\&quot;460\&quot; width=\&quot;420\&quot; height=\&quot;80\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;anthropic\&quot; value=\&quot;Creation model&amp;#xa;Anthropic API\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#071018;strokeColor=#25e8ff;fontColor=#e7feff;fontFamily=Rajdhani;align=center;verticalAlign=middle;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;300\&quot; y=\&quot;600\&quot; width=\&quot;200\&quot; height=\&quot;78\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;reviewer\&quot; value=\&quot;Review model&amp;#xa;(independent)\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#160a1f;strokeColor=#b388ff;fontColor=#d6c3ff;fontFamily=Rajdhani;align=center;verticalAlign=middle;dashed=1;\&quot; parent=\&quot;1\&quot; vertex=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry x=\&quot;550\&quot; y=\&quot;600\&quot; width=\&quot;220\&quot; height=\&quot;78\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;e1\&quot; value=\&quot;trigger\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; parent=\&quot;1\&quot; source=\&quot;gitlab\&quot; target=\&quot;pod\&quot; edge=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;e2\&quot; value=\&quot;trigger\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; parent=\&quot;1\&quot; source=\&quot;github\&quot; target=\&quot;pod\&quot; edge=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;e3\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; parent=\&quot;1\&quot; source=\&quot;agent\&quot; target=\&quot;otelflags\&quot; edge=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;e5\&quot; value=\&quot;OTLP events\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;entryX=0;entryY=0.5;entryDx=0;entryDy=0;\&quot; parent=\&quot;1\&quot; source=\&quot;otelflags\&quot; target=\&quot;otel\&quot; edge=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;e4\&quot; value=\&quot;export\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; parent=\&quot;1\&quot; source=\&quot;otel\&quot; target=\&quot;elastic\&quot; edge=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;e8\&quot; value=\&quot;&amp;lt;span&amp;gt;messages&amp;lt;/span&amp;gt;\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#ff9d2e;fontColor=#ffc785;fontFamily=Rajdhani;\&quot; parent=\&quot;1\&quot; source=\&quot;agent\&quot; target=\&quot;gateway\&quot; edge=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;e6\&quot; value=\&quot;create (Agent)\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; parent=\&quot;1\&quot; source=\&quot;gateway\&quot; target=\&quot;anthropic\&quot; edge=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n                &lt;mxCell id=\&quot;e7\&quot; value=\&quot;review (Advisor)\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#b388ff;fontColor=#d6c3ff;fontFamily=Rajdhani;\&quot; parent=\&quot;1\&quot; source=\&quot;gateway\&quot; target=\&quot;reviewer\&quot; edge=\&quot;1\&quot;&gt;\n                    &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot;/&gt;\n                &lt;/mxCell&gt;\n            &lt;/root&gt;\n        &lt;/mxGraphModel&gt;\n    &lt;/diagram&gt;\n&lt;/mxfile&gt;&quot;}"></div>
<script type="text/javascript" src="https://viewer.diagrams.net/js/viewer-static.min.js" async></script>
<script type="text/javascript">
  // Keep the draw.io diagram in sync with the Zensical/Material color-scheme
  // toggle: re-render it dark under the "slate" scheme, light otherwise.
  (function () {
    function isDark() {
      var s = document.body.getAttribute("data-md-color-scheme");
      return s ? s === "slate"
               : window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    function rebuild(el) {
      // Preserve the original config once, then render a fresh node so the
      // viewer never stacks multiple SVGs on re-render.
      var original = el.dataset.mxgraphOriginal || el.getAttribute("data-mxgraph");
      var cfg = JSON.parse(original);
      cfg.dark = isDark() ? 1 : 0;
      var fresh = document.createElement("div");
      fresh.className = "mxgraph";
      fresh.style.cssText = el.style.cssText;
      fresh.dataset.mxgraphOriginal = original;
      fresh.setAttribute("data-mxgraph", JSON.stringify(cfg));
      el.replaceWith(fresh);
      return fresh;
    }
    function applyTheme() {
      if (!(window.GraphViewer && GraphViewer.createViewerForElement)) {
        return setTimeout(applyTheme, 100);
      }
      document.querySelectorAll(".mxgraph").forEach(function (el) {
        GraphViewer.createViewerForElement(rebuild(el));
      });
    }
    new MutationObserver(applyTheme).observe(document.body, {
      attributes: true,
      attributeFilter: ["data-md-color-scheme"],
    });
    applyTheme();
  })();
</script>

!!! note "Editable source"

    A full, editable version of this diagram lives at
    [`architecture.drawio`](https://github.com/) in the repository root and can be
    opened with [draw.io](https://app.diagrams.net) or the draw.io VS Code extension.

## Components

| Component | Role |
| --- | --- |
| **GitLab CI / GitHub Actions** | Trigger pipelines; the agent detects which one via environment variables. |
| **Kubernetes Pod / CI job** | The outer unit the platform schedules — one network namespace holding the sandbox container **and** the collector sidecar (they reach each other over `localhost`). |
| **Sandbox container** *(Container 1)* | The job container the runner starts from the `claude-agent` image — rootless, unprivileged. **The Claude CLI runs here directly** (not in a nested `podman run`). The runtime is rootless Podman on a CI runner, or the Kubernetes CRI (e.g. CRI-O) on a self-hosted runner on OpenShift. No Docker. |
| **Claude CI Agent** | The `claude` process inside the sandbox — plans, edits files, makes atomic git commits, and drives Podman. |
| **Nested child containers** | `podman build`/`run` inside the sandbox spawns rootless-in-rootless containers that build and run the **app under test** (`app-test`). Claude orchestrates them; it does not run inside them. |
| **LLM Gateway** *(optional)* | Sits between the agent and the Anthropic API via `ANTHROPIC_BASE_URL`— adds prompt-response caching and request/response guardrails. See [LLM Gateway](llm-gateway.md). |
| **OTel Collector sidecar** *(Container 2)* | Sibling container in the same Pod; receives OTLP events at `localhost:4318`, scrubs secrets, exports to Elastic. |
| **Elastic** | Stores telemetry for audit. |

## Personalities

The **same sandbox image** runs in one of two personalities— the CI trigger that
started the pipeline decides which one. See [CLAUDE.md](https://github.com/) for the
authoritative definition.

| Personality | Trigger | Capability | Token scope |
| --- | --- | --- | --- |
| **Agent** *(read-write)* | A `@claude …` comment on a PR or issue | Applies a fix, commits, opens a **new** PR/MR branch | Repository **write** |
| **Advisor** *(read-only)* | A PR/MR **open** or **synchronize** event | Lints, tests, flags bugs, posts a review comment— never mutates | Repository **read** + review comments |

!!! warning "The boundary is enforced by the token, not by trust"

    The Advisor receives **no write token**— mutation is impossible even if the
    prompt is subverted. The Agent's write scope is confined to **new** branches;
    it never pushes to the default branch.

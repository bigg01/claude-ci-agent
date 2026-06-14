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
lives: rootless **Podman** on a CI runner, or the **Kubernetes CRI** (CRI-O on
OpenShift, containerd on AKS) when the runner is a private one on a cluster —
where the `restricted`/`restricted-v2` policy enforces the non-root, no-escalation
boundary. Claude is never wrapped in a nested `podman run`.

The diagram shows **two levels of nesting**. The CI platform starts a
**Kubernetes Pod / CI job** holding two sibling containers that share `localhost`:
the **agent sandbox** (the `claude-agent` image — where the Claude CLI actually
runs) and the **OTel Collector sidecar**. Inside the sandbox, the agent itself
drives `podman build`/`run`, which spawns **nested child containers**
(rootless-in-rootless) to build and test the app under review — the *only* place
nested Podman is used. Claude never runs *in* those child containers; it
orchestrates them from the sandbox.

<div class="mxgraph" style="max-width:100%;border:1px solid transparent;" data-mxgraph="{&quot;dark&quot;: &quot;auto&quot;, &quot;highlight&quot;: &quot;#25e8ff&quot;, &quot;nav&quot;: true, &quot;resize&quot;: true, &quot;toolbar&quot;: &quot;zoom layers&quot;, &quot;xml&quot;: &quot;&lt;mxfile host=\&quot;app.diagrams.net\&quot; agent=\&quot;claude-ci-agent\&quot; version=\&quot;24.0.0\&quot;&gt;\n  &lt;diagram id=\&quot;ci-arch\&quot; name=\&quot;CI Architecture\&quot;&gt;\n    &lt;mxGraphModel dx=\&quot;1100\&quot; dy=\&quot;700\&quot; grid=\&quot;1\&quot; gridSize=\&quot;10\&quot; guides=\&quot;1\&quot; tooltips=\&quot;1\&quot; connect=\&quot;1\&quot; arrows=\&quot;1\&quot; fold=\&quot;1\&quot; page=\&quot;1\&quot; pageScale=\&quot;1\&quot; pageWidth=\&quot;1169\&quot; pageHeight=\&quot;826\&quot; math=\&quot;0\&quot; shadow=\&quot;0\&quot;&gt;\n      &lt;root&gt;\n        &lt;mxCell id=\&quot;0\&quot; /&gt;\n        &lt;mxCell id=\&quot;1\&quot; parent=\&quot;0\&quot; /&gt;\n\n        &lt;!-- Title --&gt;\n        &lt;mxCell id=\&quot;title\&quot; value=\&quot;Multi-Agent / OTel CI Architecture\&quot; style=\&quot;text;html=1;align=center;verticalAlign=middle;fontSize=20;fontStyle=1;fontColor=#25e8ff;fontFamily=Orbitron;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;360\&quot; y=\&quot;16\&quot; width=\&quot;440\&quot; height=\&quot;36\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- GitLab CI --&gt;\n        &lt;mxCell id=\&quot;gitlab\&quot; value=\&quot;GitLab CI&amp;#10;&amp;#10;include: claude-agent component&amp;#10;$GITLAB_CI == true&amp;#10;OpenShift GitLab Runner\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#071018;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=top;spacingTop=8;fontStyle=1;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;40\&quot; y=\&quot;150\&quot; width=\&quot;210\&quot; height=\&quot;110\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- GitHub Actions --&gt;\n        &lt;mxCell id=\&quot;github\&quot; value=\&quot;GitHub Actions&amp;#10;&amp;#10;.github/workflows/*.yml&amp;#10;$GITHUB_ACTIONS == true&amp;#10;Hosted / self-hosted runner\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#071018;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=top;spacingTop=8;fontStyle=1;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;40\&quot; y=\&quot;300\&quot; width=\&quot;210\&quot; height=\&quot;110\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- ============ OUTER: Kubernetes Pod / CI job ============ --&gt;\n        &lt;mxCell id=\&quot;pod\&quot; value=\&quot;Kubernetes Pod  /  CI job   \u2014   one network namespace ( localhost shared between containers )\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#03121a;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Orbitron;align=center;verticalAlign=top;spacingTop=8;fontStyle=1;dashed=1;dashPattern=6 4;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;290\&quot; y=\&quot;92\&quot; width=\&quot;660\&quot; height=\&quot;404\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- MIDDLE: the agent sandbox container --&gt;\n        &lt;mxCell id=\&quot;sandbox\&quot; value=\&quot;Container 1 \u2014 Rootless, unprivileged Podman sandbox  \u00b7  claude-agent image\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#05101a;strokeColor=#25e8ff;fontColor=#25e8ff;fontFamily=Orbitron;align=center;verticalAlign=top;spacingTop=8;fontStyle=1;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;310\&quot; y=\&quot;140\&quot; width=\&quot;420\&quot; height=\&quot;336\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- Claude CLI: runs in the sandbox container itself --&gt;\n        &lt;mxCell id=\&quot;agent\&quot; value=\&quot;Claude CLI \u2014 RUNS HERE&amp;#10;&amp;#10;plans \u00b7 edits files \u00b7 git commits \u00b7 drives podman\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#0a1c26;strokeColor=#25e8ff;fontColor=#e7feff;fontFamily=Rajdhani;align=center;verticalAlign=middle;fontStyle=1;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;328\&quot; y=\&quot;180\&quot; width=\&quot;384\&quot; height=\&quot;72\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- OTel flags --&gt;\n        &lt;mxCell id=\&quot;otelflags\&quot; value=\&quot;CLAUDE_CODE_ENABLE_TELEMETRY=1 \u00b7 OTEL_LOG_TOOL_CONTENT=1\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#071018;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=middle;dashed=1;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;328\&quot; y=\&quot;262\&quot; width=\&quot;384\&quot; height=\&quot;40\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- INNER: nested child containers spawned by podman (rootless-in-rootless) --&gt;\n        &lt;mxCell id=\&quot;nested\&quot; value=\&quot;podman build / run   \u2192   nested child containers  ( rootless-in-rootless )\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#160d03;strokeColor=#ff9d2e;fontColor=#ff9d2e;fontFamily=Rajdhani;align=center;verticalAlign=top;spacingTop=6;fontStyle=1;dashed=1;dashPattern=6 4;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;328\&quot; y=\&quot;314\&quot; width=\&quot;384\&quot; height=\&quot;150\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;mxCell id=\&quot;childbuild\&quot; value=\&quot;app-test&amp;#10;&amp;#10;podman build&amp;#10;-f Containerfile\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#1a1206;strokeColor=#ff9d2e;fontColor=#ffd9a8;fontFamily=Rajdhani;align=center;verticalAlign=middle;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;344\&quot; y=\&quot;356\&quot; width=\&quot;172\&quot; height=\&quot;96\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;mxCell id=\&quot;childrun\&quot; value=\&quot;test / run container&amp;#10;&amp;#10;npm test \u00b7 pytest&amp;#10;app under test\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#1a1206;strokeColor=#ff9d2e;fontColor=#ffd9a8;fontFamily=Rajdhani;align=center;verticalAlign=middle;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;526\&quot; y=\&quot;356\&quot; width=\&quot;172\&quot; height=\&quot;96\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- OTel Collector sidecar \u2014 Container 2 in the SAME pod --&gt;\n        &lt;mxCell id=\&quot;otel\&quot; value=\&quot;Container 2&amp;#10;OTel Collector sidecar&amp;#10;&amp;#10;localhost:4318&amp;#10;(secret scrub)\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#08161e;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=middle;fontStyle=1;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;752\&quot; y=\&quot;186\&quot; width=\&quot;180\&quot; height=\&quot;124\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- Elastic \u2014 outside the pod --&gt;\n        &lt;mxCell id=\&quot;elastic\&quot; value=\&quot;Elastic&amp;#10;&amp;#10;claude-agent-&amp;lt;team&amp;gt;-*&amp;#10;per-team index / RBAC\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#08161e;strokeColor=#25e8ff;fontColor=#cdeef5;fontFamily=Rajdhani;align=center;verticalAlign=middle;fontStyle=1;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;1000\&quot; y=\&quot;200\&quot; width=\&quot;150\&quot; height=\&quot;110\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- Edges --&gt;\n        &lt;mxCell id=\&quot;e1\&quot; value=\&quot;trigger\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; edge=\&quot;1\&quot; parent=\&quot;1\&quot; source=\&quot;gitlab\&quot; target=\&quot;pod\&quot;&gt;\n          &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n        &lt;mxCell id=\&quot;e2\&quot; value=\&quot;trigger\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; edge=\&quot;1\&quot; parent=\&quot;1\&quot; source=\&quot;github\&quot; target=\&quot;pod\&quot;&gt;\n          &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n        &lt;mxCell id=\&quot;enest\&quot; value=\&quot;spawns\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#ff9d2e;fontColor=#ffc785;fontFamily=Rajdhani;\&quot; edge=\&quot;1\&quot; parent=\&quot;1\&quot; source=\&quot;agent\&quot; target=\&quot;nested\&quot;&gt;\n          &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n        &lt;mxCell id=\&quot;e3\&quot; value=\&quot;OTLP events&amp;#10;(via localhost)\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; edge=\&quot;1\&quot; parent=\&quot;1\&quot; source=\&quot;agent\&quot; target=\&quot;otel\&quot;&gt;\n          &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n        &lt;mxCell id=\&quot;e4\&quot; value=\&quot;export\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; edge=\&quot;1\&quot; parent=\&quot;1\&quot; source=\&quot;otel\&quot; target=\&quot;elastic\&quot;&gt;\n          &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- LLM Gateway (optional) --&gt;\n        &lt;mxCell id=\&quot;gateway\&quot; value=\&quot;LLM Gateway (optional)&amp;#10;&amp;#10;Prompt caching \u00b7 Guardrails \u00b7 ANTHROPIC_BASE_URL\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#1a1206;strokeColor=#ff9d2e;fontColor=#ff9d2e;fontFamily=Rajdhani;align=center;verticalAlign=middle;fontStyle=1;dashed=1;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;310\&quot; y=\&quot;540\&quot; width=\&quot;420\&quot; height=\&quot;80\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- Creation model (Agent personality) --&gt;\n        &lt;mxCell id=\&quot;anthropic\&quot; value=\&quot;Creation model&amp;#10;&amp;#10;Anthropic API&amp;#10;claude-opus-4-8\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#071018;strokeColor=#25e8ff;fontColor=#e7feff;fontFamily=Rajdhani;align=center;verticalAlign=middle;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;310\&quot; y=\&quot;672\&quot; width=\&quot;200\&quot; height=\&quot;78\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- Review model (Advisor personality) \u2014 independent model or vendor --&gt;\n        &lt;mxCell id=\&quot;reviewer\&quot; value=\&quot;Review model / vendor&amp;#10;&amp;#10;independent \u2014 a different&amp;#10;model or vendor\&quot; style=\&quot;rounded=1;whiteSpace=wrap;html=1;fillColor=#160a1f;strokeColor=#b388ff;fontColor=#d6c3ff;fontFamily=Rajdhani;align=center;verticalAlign=middle;dashed=1;\&quot; vertex=\&quot;1\&quot; parent=\&quot;1\&quot;&gt;\n          &lt;mxGeometry x=\&quot;560\&quot; y=\&quot;672\&quot; width=\&quot;220\&quot; height=\&quot;78\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n\n        &lt;!-- Edges: agent -&gt; gateway -&gt; creation / review models --&gt;\n        &lt;mxCell id=\&quot;e5\&quot; value=\&quot;messages\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#ff9d2e;fontColor=#ffc785;fontFamily=Rajdhani;\&quot; edge=\&quot;1\&quot; parent=\&quot;1\&quot; source=\&quot;agent\&quot; target=\&quot;gateway\&quot;&gt;\n          &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n        &lt;mxCell id=\&quot;e6\&quot; value=\&quot;create (Agent)\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#25e8ff;fontColor=#9af6ff;fontFamily=Rajdhani;\&quot; edge=\&quot;1\&quot; parent=\&quot;1\&quot; source=\&quot;gateway\&quot; target=\&quot;anthropic\&quot;&gt;\n          &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n        &lt;mxCell id=\&quot;e7\&quot; value=\&quot;review (Advisor)\&quot; style=\&quot;edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#b388ff;fontColor=#d6c3ff;fontFamily=Rajdhani;\&quot; edge=\&quot;1\&quot; parent=\&quot;1\&quot; source=\&quot;gateway\&quot; target=\&quot;reviewer\&quot;&gt;\n          &lt;mxGeometry relative=\&quot;1\&quot; as=\&quot;geometry\&quot; /&gt;\n        &lt;/mxCell&gt;\n      &lt;/root&gt;\n    &lt;/mxGraphModel&gt;\n  &lt;/diagram&gt;\n&lt;/mxfile&gt;\n&quot;}"></div>
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
| **Sandbox container** *(Container 1)* | The job container the runner starts from the `claude-agent` image — rootless, unprivileged. **The Claude CLI runs here directly** (not in a nested `podman run`). The runtime is rootless Podman on a CI runner, or the Kubernetes CRI (CRI-O/containerd) on a private runner on OpenShift/AKS. No Docker. |
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

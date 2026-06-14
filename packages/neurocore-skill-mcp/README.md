# neurocore-skill-mcp

Invoke [Model Context Protocol](https://modelcontextprotocol.io) server tools
from NeuroCore blueprints.

```bash
pip install neurocore-skill-mcp
```

## Blueprint usage

```yaml
components:
  - name: github_tool
    type: mcp-tool
    config:
      transport: stdio
      command: docker
      args: ["run", "-i", "--rm", "-e", "GITHUB_TOKEN", "ghcr.io/github/github-mcp-server"]
      env: { GITHUB_TOKEN: "${GITHUB_TOKEN}" }
      tool: create_issue
      arguments: { owner: octocat, repo: hello-world }
flow:
  type: sequential
  steps:
    - component: github_tool
```

Runtime values in the `mcp_arguments` context key are merged over `arguments`
(runtime wins). The tool's result is written to `mcp_result` (configurable via
`result_key`).

Streamable HTTP transport:

```yaml
config:
  transport: http
  url: https://example.com/mcp
  headers: { Authorization: "Bearer ${TOKEN}" }
  tool: search
```

## CLI

```bash
neurocore mcp list-tools --command docker --args "run,-i,--rm,ghcr.io/github/github-mcp-server"
neurocore mcp list-tools --url https://example.com/mcp
```

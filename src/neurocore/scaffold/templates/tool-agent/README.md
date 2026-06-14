# {{ project_name }}

A tool-calling agent that invokes a [Model Context Protocol](https://modelcontextprotocol.io)
server tool from a blueprint — here, creating a GitHub issue.

## Setup

```bash
pip install neurocore-ai neurocore-skill-mcp
export GITHUB_TOKEN=ghp_...
```

List a server's tools:

```bash
neurocore mcp list-tools --command docker \
  --args "run,-i,--rm,-e,GITHUB_TOKEN,ghcr.io/github/github-mcp-server"
```

## Run

```bash
neurocore run blueprints/tool.flow.yaml \
  --data title="Bug: ..." --data body="Steps to reproduce ..."
```

Runtime values in the `mcp_arguments` context key are merged over the static
`arguments` in the blueprint (runtime wins).

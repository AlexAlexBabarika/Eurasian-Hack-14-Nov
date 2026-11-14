# Groundtruth MCP server

`mcp/server.py` lets an AI assistant run the audit as a tool. It speaks MCP over stdio and has one tool:

`audit_product(repo_url, site_url, policy_url, jurisdictions)` returns the Markdown report. `jurisdictions` is optional: a list of `UK`, `EU`, `KZ`.

Run `make setup` first. The assistant starts the server itself; you do not run it by hand.

## Claude Code

The repo ships `.mcp.json`, so there is nothing to configure:

```sh
cd Eurasian-Hack-14-Nov
claude            # approve the "groundtruth" server when asked
claude mcp list   # should show: groundtruth ... Connected
```

## Cursor

The repo ships `.cursor/mcp.json`. Open the repo folder in Cursor, then switch on `groundtruth` under Customize in the sidebar (Settings > MCP in older versions).

## Claude Desktop

Claude Desktop has no project config, so it needs absolute paths. Add this to `claude_desktop_config.json` (Settings > Developer > Edit Config) and restart the app:

```json
{
  "mcpServers": {
    "groundtruth": {
      "command": "uv",
      "args": ["run", "--project", "/ABSOLUTE/PATH/Eurasian-Hack-14-Nov/api", "python", "/ABSOLUTE/PATH/Eurasian-Hack-14-Nov/mcp/server.py"]
    }
  }
}
```

If the app reports that it cannot find `uv`, replace `"uv"` with the full path printed by `which uv`.

## Try it

Ask the assistant:

> Audit https://github.com/AlexAlexBabarika/Eurasian-Hack-14-Nov/tree/main/demo/fixture-app with site http://localhost:4100/public/index.html and policy http://localhost:4100/privacy.html, for the UK and EU only.

That is the built-in demo product. Either run `make fixture` so those URLs are live, or set `DEMO_MODE=cached` in `.env` to get the saved report with no network.

## Notes

- Settings come from `.env` in the repo root (`LLM_API_KEY`, `DEMO_MODE`, ...). Assistants pass only a few environment variables to the server, so put them there, not in your shell.
- A live audit of a real repository can take a minute or more. If the assistant gives up early, raise its tool timeout (Claude Code: add `"timeout": 600000` to the server entry in `.mcp.json`).

PYTHON ?= python3
CLAUDE_HOME ?= $(HOME)/.claude
MCP_NAME ?= knowledge-database

.PHONY: test generate-graph validate-graph graph install-hooks install-global-claude install-mcp-claude

test:
	$(PYTHON) -m unittest discover -s tests

generate-graph:
	$(PYTHON) scripts/generate-graph.py

validate-graph:
	$(PYTHON) scripts/generate-graph.py --validate

graph: generate-graph validate-graph

install-hooks:
	chmod +x scripts/pre-commit
	ln -sf ../../scripts/pre-commit .git/hooks/pre-commit

# Link this vault's skills and agents into the global Claude context
# (~/.claude/skills, ~/.claude/agents) so they are invocable from any repo.
install-global-claude:
	mkdir -p "$(CLAUDE_HOME)/skills" "$(CLAUDE_HOME)/agents"
	@for d in skills/*/; do \
		name=$$(basename "$$d"); \
		[ -f "$$d/SKILL.md" ] || continue; \
		ln -sfn "$(CURDIR)/$$d" "$(CLAUDE_HOME)/skills/$$name"; \
		echo "skill  -> $(CLAUDE_HOME)/skills/$$name"; \
	done
	@for f in agents/*.md; do \
		name=$$(basename "$$f"); \
		[ "$$name" = "README.md" ] && continue; \
		ln -sfn "$(CURDIR)/$$f" "$(CLAUDE_HOME)/agents/$$name"; \
		echo "agent  -> $(CLAUDE_HOME)/agents/$$name"; \
	done

# Register scripts/mcp-server.py as an MCP server in Claude Code (user scope,
# so it is available from any repo). Re-run to update; removes stale entry first.
install-mcp-claude:
	-claude mcp remove --scope user "$(MCP_NAME)" 2>/dev/null
	claude mcp add --scope user "$(MCP_NAME)" -- $(PYTHON) "$(CURDIR)/scripts/mcp-server.py"
	@echo "mcp    -> $(MCP_NAME) ($(CURDIR)/scripts/mcp-server.py)"

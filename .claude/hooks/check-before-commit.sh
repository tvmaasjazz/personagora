#!/usr/bin/env bash
# PreToolUse hook on Bash: before a `git commit`, runs the checks for each side of the
# stack the change touches, and blocks the commit (exit 2) with their output when one
# fails. Any other command passes straight through.
#
# Checks run on the working tree, against every file changed since HEAD (staged or not).

input=$(cat)
command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')

if ! printf '%s' "$command" |
	grep -Eq '(^|[;&|(`[:space:]])git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?commit([[:space:]]|$)'; then
	exit 0
fi

cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
root=$(git -C "${cwd:-$CLAUDE_PROJECT_DIR}" rev-parse --show-toplevel 2>/dev/null) || exit 0

changed=$(
	git -C "$root" diff --name-only HEAD 2>/dev/null
	git -C "$root" diff --cached --name-only 2>/dev/null
)
failures=""

# Runs one check from a directory, and records its output if it fails.
run_check() {
	local dir=$1
	shift
	local output
	if ! output=$(cd "$root/$dir" && "$@" 2>&1); then
		failures="$failures
--- $dir: $* failed
$(printf '%s\n' "$output" | tail -40)
"
	fi
}

if printf '%s\n' "$changed" | grep -q '^backend/'; then
	if ! command -v uv >/dev/null; then
		echo "Commit blocked: uv isn't on PATH, so the backend checks can't run." >&2
		exit 2
	fi
	run_check backend uv run ruff check .
	run_check backend uv run ruff format --check .
	run_check backend uv run ty check
fi

if printf '%s\n' "$changed" | grep -q '^frontend/'; then
	installed="$root/frontend/node_modules/.package-lock.json"
	if [ ! -f "$installed" ] || [ "$root/frontend/package-lock.json" -nt "$installed" ]; then
		echo "Commit blocked: frontend/node_modules is missing or older than package-lock.json. Run \`npm ci\` in frontend/ first." >&2
		exit 2
	fi
	run_check frontend npm run fmt:check
	run_check frontend npm run lint
	run_check frontend npm run build
	run_check frontend npm run test
fi

if [ -n "$failures" ]; then
	{
		echo "Commit blocked by .claude/hooks/check-before-commit.sh. Fix these, then commit again"
		echo "(\`uv run ruff check --fix .\` and \`uv run ruff format .\` in backend/, \`npm run fmt\` in"
		echo "frontend/ fix most format and lint failures):"
		printf '%s\n' "$failures"
	} >&2
	exit 2
fi

exit 0

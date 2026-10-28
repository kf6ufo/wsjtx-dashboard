#!/bin/sh
# Parse the complete body before a fast-forward can replace this script itself.
{
    set -eu
    previous='not verified'
    updated='not changed'
    phase='repository checks'
    finish() {
        result=$?
        if [ "$result" -ne 0 ]; then
            printf >&2 'Update failed during %s.\nPrevious commit: %s\nUpdated commit: %s\n' "$phase" "$previous" "$updated"
            printf >&2 'Keep Dashboard stopped until the problem is resolved; no services were managed.\n'
        fi
    }
    trap finish 0
    fail() { printf >&2 '%s\n' "$1"; exit 1; }
    clean_tracked_files() {
        changes=$(git status --porcelain --untracked-files=no --ignore-submodules=none) || fail 'Cannot inspect tracked changes.'
        [ -z "$changes" ] || fail 'Tracked files have uncommitted changes. Inspect git status and save/commit your work before retrying. Nothing was stashed or overwritten.'
    }

    command -v git >/dev/null 2>&1 || fail 'Git is required.'
    cd -P "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)" || fail 'Cannot enter the installation directory.'
    root=$(pwd -P)
    top=$(git rev-parse --show-toplevel) || fail 'Run update.sh from a WSJT-X Dashboard Git checkout.'
    [ "$root" = "$top" ] || fail 'update.sh must be in the root of the WSJT-X Dashboard checkout.'
    git ls-files --error-unmatch install.sh config.example.toml backend/server.py >/dev/null 2>&1 || fail 'Expected Dashboard installation files are missing from Git.'
    origin=$(git config --get remote.origin.url) || fail 'The origin remote is missing.'
    origin=$(printf '%s' "${origin%/}" | tr '[:upper:]' '[:lower:]')
    case "$origin" in
        https://github.com/kf6ufo/wsjtx-dashboard|https://github.com/kf6ufo/wsjtx-dashboard.git|git@github.com:kf6ufo/wsjtx-dashboard|git@github.com:kf6ufo/wsjtx-dashboard.git|ssh://git@github.com/kf6ufo/wsjtx-dashboard.git|ssh://git@github.com:22/kf6ufo/wsjtx-dashboard.git) ;;
        *) fail 'origin must identify kf6ufo/wsjtx-dashboard on GitHub using HTTPS or SSH. The remote was not changed.' ;;
    esac
    branch=$(git symbolic-ref --quiet --short HEAD) || fail 'A main branch checkout is required; detached HEAD is not updated.'
    [ "$branch" = main ] || fail 'Switch to main yourself after saving your work; this updater does not switch branches.'
    previous=$(git rev-parse --verify HEAD) || fail 'Cannot determine the previous commit.'
    updated=$previous
    printf 'Previous commit: %s\n' "$previous"
    printf 'Dashboard must already be stopped. Run as the operator without sudo; no services are managed.\n'
    clean_tracked_files

    phase='fetching origin/main'
    git fetch origin refs/heads/main:refs/remotes/origin/main || fail 'Fetch failed. Check repository access and connectivity; installation was not run.'
    [ "$(git symbolic-ref --quiet --short HEAD)" = main ] && [ "$(git rev-parse HEAD)" = "$previous" ] || fail 'The checkout changed during fetch. Inspect it before retrying.'
    clean_tracked_files
    git merge-base --is-ancestor "$previous" refs/remotes/origin/main || fail 'Local main is ahead of or has diverged from origin/main. Review the commits manually; nothing was reset or rebased.'

    phase='fast-forward update'
    # Never autostash, or overwrite ignored operator files if upstream adds a path.
    git merge --ff-only --no-autostash --no-overwrite-ignore refs/remotes/origin/main || fail 'Fast-forward failed. Inspect git status for conflicting files; installation was not run.'
    updated=$(git rev-parse --verify HEAD) || fail 'Cannot determine the updated commit.'
    printf 'Updated commit: %s\n' "$updated"
    if [ "$previous" = "$updated" ]; then
        printf 'Already up to date; running the installer to verify/rebuild the installation.\n'
    fi
    phase='installation'
    if ./install.sh; then
        printf 'Update successful.\nPrevious commit: %s\nUpdated commit: %s\n' "$previous" "$updated"
        printf 'Restart Dashboard manually with your usual configuration or service only after success.\n'
    else
        code=$?
        fail "Installer failed (exit $code). Source remains at $updated; no rollback was attempted. Fix the error and rerun ./update.sh before restarting Dashboard."
    fi
    exit 0
}

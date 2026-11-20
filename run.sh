#!/bin/sh

set -eu

case "$0" in
    */*) cd "${0%/*}" ;;
esac

PY=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --python)
            shift
            [ "$#" -gt 0 ] || { echo "run.sh: --python требует аргумента" >&2; exit 2; }
            PY="$1"
            ;;
        *)
            break
            ;;
    esac
    shift
done
if [ -z "$PY" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PY=python3
    elif command -v python >/dev/null 2>&1; then
        PY=python
    else
        echo "run.sh: не найден python3/python" >&2
        exit 2
    fi
fi

if [ "$#" -eq 0 ]; then
    $PY -c "import os; os.makedirs('out', exist_ok=True)"
    for repo in chain diamond cycle deep broken; do
        echo
        echo "==================== $repo ===================="
        $PY -m depgrapher -p A -s "testrepos/$repo.txt" -m file \
            -o "out/$repo.png" -a tree || true
    done
    echo
    echo "==================== unit tests ===================="
    $PY -m unittest discover -s tests
    exit $?
fi

exec $PY -m depgrapher "$@"

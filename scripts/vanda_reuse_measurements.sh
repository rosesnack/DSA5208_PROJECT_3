#!/usr/bin/env bash

# Reuse saved five-repeat measurements; independent checks remain on the free queue.
run_or_reuse() {
    local folder="$1"
    shift
    if [[ "${PAGERANK_RESUME_EXISTING:-1}" == 1 &&
          -s "$folder/summary.json" && -s "$folder/ranks.csv" &&
          -s "$folder/history.csv" && -s "$folder/timings.csv" &&
          $(wc -l < "$folder/timings.csv") -eq $((PAGERANK_REPEATS + 1)) ]]; then
        printf 'Reusing saved measurement pending free validation: %s\n' "$folder"
    else
        "$@"
    fi
}

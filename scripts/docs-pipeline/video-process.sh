#!/usr/bin/env bash
# video-process.sh — Convert Playwright .webm recordings to .mp4 and extract GIF clips
# Finds videos in tests/ui-tutorials/test-results/ and matches them to tutorials
# Outputs to .captures/<tutorial>/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CAPTURES_DIR="${REPO_ROOT}/tests/ui-tutorials/.captures"
TEST_RESULTS_DIR="${REPO_ROOT}/tests/ui-tutorials/test-results"

echo "Captures directory:    ${CAPTURES_DIR}"
echo "Test results directory: ${TEST_RESULTS_DIR}"

if ! command -v ffmpeg &>/dev/null; then
    echo "ERROR: ffmpeg not found. Install with: sudo apt-get install ffmpeg"
    exit 1
fi

if [[ ! -d "${TEST_RESULTS_DIR}" ]]; then
    echo "WARNING: test-results directory not found: ${TEST_RESULTS_DIR}"
    echo "No videos to process."
    exit 0
fi

if [[ ! -d "${CAPTURES_DIR}" ]]; then
    echo "ERROR: Captures directory not found: ${CAPTURES_DIR}"
    exit 1
fi

# Find the webm file for a given tutorial number prefix (e.g. "tutorial-01")
find_webm_for_tutorial() {
    local tutorial_id="$1"   # e.g. tutorial-01
    # test-results directories are named like tutorial-01-hello-workflow-...-tutorials/video.webm
    local prefix="${tutorial_id}-"
    find "${TEST_RESULTS_DIR}" -maxdepth 2 -name "video.webm" | while read -r f; do
        local dir_name
        dir_name="$(basename "$(dirname "$f")")"
        if [[ "${dir_name}" == ${prefix}* ]]; then
            echo "${f}"
            return
        fi
    done
}

process_tutorial() {
    local tutorial_dir="$1"
    local tutorial_id
    tutorial_id="$(basename "${tutorial_dir}")"
    local manifest="${tutorial_dir}/manifest.json"

    if [[ ! -f "${manifest}" ]]; then
        echo "  [skip] No manifest.json in ${tutorial_id}"
        return
    fi

    local webm
    webm="$(find_webm_for_tutorial "${tutorial_id}")"

    if [[ -z "${webm}" ]]; then
        echo "  [skip] No video found for ${tutorial_id}"
        return
    fi

    echo "Processing ${tutorial_id}: ${webm}"

    local mp4_out="${tutorial_dir}/video.mp4"
    local gif_out="${tutorial_dir}/demo.gif"

    # --- Convert webm to mp4 (idempotent) ---
    if [[ -f "${mp4_out}" && "${mp4_out}" -nt "${webm}" ]]; then
        echo "  [skip] MP4 already up-to-date: video.mp4"
    else
        echo "  Converting to MP4..."

        # Build drawtext filters from manifest step timestamps
        local drawtext_filters
        drawtext_filters=$(python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    data = json.load(f)

steps = data.get('steps', [])
if not steps:
    print('')
    sys.exit(0)

# Get base timestamp (first step)
base_ms = steps[0]['timestamp_ms']
filters = []
for i, step in enumerate(steps):
    start_sec = (step['timestamp_ms'] - base_ms) / 1000.0
    # Duration until next step, or 3s for last
    if i + 1 < len(steps):
        end_sec = (steps[i + 1]['timestamp_ms'] - base_ms) / 1000.0
    else:
        end_sec = start_sec + 3.0

    title = step.get('title', '').replace(\"'\", \"'\\\\''\")
    step_num = step['step']
    label = f'Step {step_num}: {title}'
    # Escape colons and special chars for ffmpeg drawtext
    label = label.replace(':', r'\\:')

    f = (
        f\"drawtext=text='{label}':\"
        f\"fontsize=20:fontcolor=white:\"
        f\"box=1:boxcolor=black@0.6:boxborderw=6:\"
        f\"x=10:y=10:\"
        f\"enable='between(t,{start_sec:.3f},{end_sec:.3f})'\"
    )
    filters.append(f)

print(','.join(filters))
" "${manifest}")

        if [[ -n "${drawtext_filters}" ]]; then
            ffmpeg -y -i "${webm}" \
                -vf "${drawtext_filters}" \
                -c:v libx264 -preset fast -crf 23 \
                -c:a aac \
                -movflags +faststart \
                "${mp4_out}" \
                -loglevel warning
        else
            ffmpeg -y -i "${webm}" \
                -c:v libx264 -preset fast -crf 23 \
                -c:a aac \
                -movflags +faststart \
                "${mp4_out}" \
                -loglevel warning
        fi
        echo "  MP4 written: video.mp4"
    fi

    # --- Extract GIF for gif-start/gif-end ranges (idempotent) ---
    if [[ -f "${gif_out}" && "${gif_out}" -nt "${webm}" ]]; then
        echo "  [skip] GIF already up-to-date: demo.gif"
    else
        # Find gif-start and gif-end steps in manifest
        local gif_range
        gif_range=$(python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    data = json.load(f)

steps = data.get('steps', [])
base_ms = steps[0]['timestamp_ms'] if steps else 0

start_sec = None
end_sec = None

for step in steps:
    t = (step['timestamp_ms'] - base_ms) / 1000.0
    if step.get('format') == 'gif-start':
        start_sec = t
    elif step.get('format') == 'gif-end' and start_sec is not None:
        end_sec = t
        break

if start_sec is not None and end_sec is not None:
    print(f'{start_sec:.3f},{end_sec:.3f}')
else:
    print('')
" "${manifest}")

        if [[ -n "${gif_range}" ]]; then
            local gif_start gif_end gif_duration
            gif_start="${gif_range%%,*}"
            gif_end="${gif_range##*,}"
            gif_duration=$(python3 -c "print(round(${gif_end} - ${gif_start}, 3))")

            echo "  Extracting GIF (${gif_start}s → ${gif_end}s)..."

            local palette_file
            palette_file="$(mktemp /tmp/palette_XXXXXX.png)"

            # Generate palette (-update 1 suppresses the "no sequence pattern" warning for single-file output)
            ffmpeg -y -ss "${gif_start}" -t "${gif_duration}" -i "${webm}" \
                -vf "fps=10,scale=640:-1:flags=lanczos,palettegen" \
                -update 1 "${palette_file}" -loglevel warning

            # Generate GIF using palette
            ffmpeg -y -ss "${gif_start}" -t "${gif_duration}" -i "${webm}" \
                -i "${palette_file}" \
                -filter_complex "fps=10,scale=640:-1:flags=lanczos[x];[x][1:v]paletteuse" \
                "${gif_out}" -loglevel warning

            rm -f "${palette_file}"
            echo "  GIF written: demo.gif"
        else
            echo "  No gif-start/gif-end range found in manifest, skipping GIF"
        fi
    fi

    echo "  Done: ${tutorial_id}"
}

# Process all tutorial directories
found=0
for dir in "${CAPTURES_DIR}"/tutorial-*/; do
    process_tutorial "${dir}"
    found=1
done

if [[ "${found}" -eq 0 ]]; then
    echo "No tutorial directories found in ${CAPTURES_DIR}"
fi

echo "Video processing complete."

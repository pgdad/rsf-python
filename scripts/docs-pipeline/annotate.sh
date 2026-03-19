#!/usr/bin/env bash
# annotate.sh — Add step badges and highlight rectangles to tutorial screenshots
# Uses ImageMagick to annotate screenshots from manifest.json
# Outputs to .captures/<tutorial>/annotated/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CAPTURES_DIR="${REPO_ROOT}/tests/ui-tutorials/.captures"

# Detect ImageMagick command (magick on v7+, convert on v6)
if command -v magick &>/dev/null; then
    IM_CMD="magick"
else
    IM_CMD="convert"
fi

echo "Using ImageMagick command: ${IM_CMD}"
echo "Captures directory: ${CAPTURES_DIR}"

if [[ ! -d "${CAPTURES_DIR}" ]]; then
    echo "ERROR: Captures directory not found: ${CAPTURES_DIR}"
    exit 1
fi

# Badge style (matches config.yaml)
BADGE_SIZE=36
BADGE_FONT_SIZE=18
BADGE_BG="#3b82f6"
BADGE_FG="white"
BADGE_OFFSET_X=12
BADGE_OFFSET_Y=12

# Highlight style
HL_COLOR="#f59e0b"
HL_WIDTH=3
HL_LABEL_FONT_SIZE=14
HL_LABEL_BG="#f59e0b"
HL_LABEL_FG="#1e293b"
HL_LABEL_PAD=4

annotate_screenshot() {
    local src="$1"
    local dst="$2"
    local step_num="$3"
    local hl_json="$4"   # JSON string or empty

    # Build ImageMagick arguments
    local args=()
    args+=("${src}")

    # --- Step badge (circle with number, top-left) ---
    local badge_half=$(( BADGE_SIZE / 2 ))
    local cx=$(( BADGE_OFFSET_X + badge_half ))
    local cy=$(( BADGE_OFFSET_Y + badge_half ))
    local r=$(( badge_half - 1 ))

    args+=(
        -fill "${BADGE_BG}"
        -stroke none
        -draw "circle ${cx},${cy} ${cx},$(( cy - r ))"
        -fill "${BADGE_FG}"
        -font DejaVu-Sans-Bold
        -pointsize "${BADGE_FONT_SIZE}"
        -gravity NorthWest
        -annotate "+$(( cx - BADGE_FONT_SIZE / 2 ))+$(( BADGE_OFFSET_Y + badge_half - BADGE_FONT_SIZE / 2 + 1 ))" "${step_num}"
    )

    # --- Highlight rectangle (if present) ---
    if [[ -n "${hl_json}" && "${hl_json}" != "null" ]]; then
        local hl_x hl_y hl_w hl_h hl_label x2 y2
        # Use int() to truncate floats; compute x2/y2 in python to avoid bash float arithmetic
        hl_x=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(int(d['x']))" "${hl_json}")
        hl_y=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(int(d['y']))" "${hl_json}")
        hl_w=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(int(d['width']))" "${hl_json}")
        hl_h=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(int(d['height']))" "${hl_json}")
        hl_label=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('label',''))" "${hl_json}")

        local x2=$(( hl_x + hl_w ))
        local y2=$(( hl_y + hl_h ))

        # Draw highlight border
        args+=(
            -fill none
            -stroke "${HL_COLOR}"
            -strokewidth "${HL_WIDTH}"
            -draw "rectangle ${hl_x},${hl_y} ${x2},${y2}"
        )

        # Draw label background + text if label is non-empty
        if [[ -n "${hl_label}" ]]; then
            local label_x=$(( hl_x + HL_LABEL_PAD ))
            local label_y=$(( hl_y - HL_LABEL_FONT_SIZE - HL_LABEL_PAD * 2 ))
            # Clamp to top of image
            if [[ "${label_y}" -lt 2 ]]; then
                label_y=$(( hl_y + HL_LABEL_PAD ))
            fi
            local label_x2=$(( label_x + ${#hl_label} * HL_LABEL_FONT_SIZE / 2 + HL_LABEL_PAD * 2 ))
            local label_y2=$(( label_y + HL_LABEL_FONT_SIZE + HL_LABEL_PAD * 2 ))

            args+=(
                -fill "${HL_LABEL_BG}"
                -stroke none
                -draw "rectangle ${label_x},${label_y} ${label_x2},${label_y2}"
                -fill "${HL_LABEL_FG}"
                -font DejaVu-Sans
                -pointsize "${HL_LABEL_FONT_SIZE}"
                -gravity NorthWest
                -annotate "+$(( label_x + HL_LABEL_PAD ))+$(( label_y + HL_LABEL_PAD ))" "${hl_label}"
            )
        fi
    fi

    args+=("${dst}")

    "${IM_CMD}" "${args[@]}"
}

process_tutorial() {
    local tutorial_dir="$1"
    local tutorial_name
    tutorial_name="$(basename "${tutorial_dir}")"
    local manifest="${tutorial_dir}/manifest.json"

    if [[ ! -f "${manifest}" ]]; then
        echo "  [skip] No manifest.json in ${tutorial_name}"
        return
    fi

    local annotated_dir="${tutorial_dir}/annotated"
    mkdir -p "${annotated_dir}"

    echo "Processing ${tutorial_name}..."

    # Parse manifest with python3
    local steps_json
    steps_json=$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
for s in data['steps']:
    hl = json.dumps(s.get('highlight')) if s.get('highlight') else ''
    print('\t'.join([
        str(s['step']),
        s['screenshot'],
        hl
    ]))
" "${manifest}")

    while IFS=$'\t' read -r step_num screenshot hl_json; do
        local src="${tutorial_dir}/${screenshot}"
        local dst="${annotated_dir}/${screenshot}"

        if [[ ! -f "${src}" ]]; then
            echo "  [skip] Screenshot not found: ${screenshot}"
            continue
        fi

        # Idempotent: skip if output is newer than source
        if [[ -f "${dst}" && "${dst}" -nt "${src}" ]]; then
            echo "  [skip] Already annotated: ${screenshot}"
            continue
        fi

        echo "  Annotating step ${step_num}: ${screenshot}"
        annotate_screenshot "${src}" "${dst}" "${step_num}" "${hl_json}"

    done <<< "${steps_json}"

    echo "  Done: ${annotated_dir}"
}

# Process all tutorial directories
for dir in "${CAPTURES_DIR}"/tutorial-*/; do
    process_tutorial "${dir}"
done

echo "Annotation complete."

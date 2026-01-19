#!/bin/bash

# HSCode API Tester Script
# Usage: ./run-hscode-test.sh [limit] [--noimage] [--nodownload]
# Example: ./run-hscode-test.sh 100                    (test first 100 lines with images)
# Example: ./run-hscode-test.sh 100 --noimage          (test first 100 lines, no image input)
# Example: ./run-hscode-test.sh 100 --nodownload       (test first 100 lines, with image input, no download)

set -e

# Load environment configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/.env" ]; then
    source "${SCRIPT_DIR}/.env"
else
    echo "Error: .env file not found in ${SCRIPT_DIR}"
    exit 1
fi

# Get project root (parent of bin/)
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# Resolve TARGET_DIR (can be relative or absolute)
if [[ "${TARGET_DIR}" = /* ]]; then
    # Absolute path
    WORK_DIR="${TARGET_DIR}"
else
    # Relative path from project root
    WORK_DIR="${PROJECT_ROOT}/${TARGET_DIR}"
fi

# Configuration
INPUT_FILE="${WORK_DIR}/hscode.jl"

# Create timestamped result folder
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
RESULT_DIR="${WORK_DIR}/results_${TIMESTAMP}"
OUTPUT_FILE="${RESULT_DIR}/results.jsonl"
IMAGE_DIR="${RESULT_DIR}/images"
LOG_FILE="${RESULT_DIR}/api.log"

API_URL="${API_URL:-http://localhost:3100}"
API_ENDPOINT="${API_URL}/sz-openai-tester/hscode"
DELAY="${DELAY:-0.5}"  # Delay between requests in seconds

# Parse arguments
LIMIT=""
NOIMAGE=false  # Default: send image to API
NODOWNLOAD=false  # Default: download images

for arg in "$@"; do
    if [[ "${arg}" == "--noimage" ]]; then
        NOIMAGE=true
    elif [[ "${arg}" == "--nodownload" ]]; then
        NODOWNLOAD=true
    elif [[ "${arg}" =~ ^[0-9]+$ ]]; then
        LIMIT="${arg}"
    fi
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check dependencies
command -v jq >/dev/null 2>&1 || { echo -e "${RED}Error: jq is required but not installed.${NC}" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo -e "${RED}Error: curl is required but not installed.${NC}" >&2; exit 1; }

# Check if input file exists
if [ ! -f "${INPUT_FILE}" ]; then
    echo -e "${RED}Error: Input file not found: ${INPUT_FILE}${NC}"
    exit 1
fi

# Create directories
mkdir -p "${RESULT_DIR}"
mkdir -p "${IMAGE_DIR}"

# Create output file and log file
> "${OUTPUT_FILE}"
> "${LOG_FILE}"

# Function to log output (both to console and file)
# Console output includes colors, log file gets plain text
log() {
    # Print to console with colors
    echo -e "$@"
    # Remove ANSI color codes and save to log file
    echo -e "$@" | sed -e 's/\x1b\[[0-9;]*m//g' >> "${LOG_FILE}"
}

# Count total lines
TOTAL_LINES=$(wc -l < "${INPUT_FILE}" | tr -d ' ')

# Apply limit with max cap of 200
if [[ -n "${LIMIT}" ]]; then
    if [[ ${LIMIT} -gt 200 ]]; then
        LIMIT=200
        log "${YELLOW}Limit capped at maximum 200${NC}"
    fi
    
    if [[ ${LIMIT} -lt ${TOTAL_LINES} ]]; then
        TOTAL_LINES="${LIMIT}"
    fi
    log "${YELLOW}Processing first ${TOTAL_LINES} lines${NC}"
else
    # No limit specified, but still cap at 200
    if [[ ${TOTAL_LINES} -gt 200 ]]; then
        TOTAL_LINES=200
        log "${YELLOW}No limit specified, capped at maximum 200${NC}"
    fi
fi

log "${GREEN}Starting HSCode API Test${NC}"
log "Work directory: ${WORK_DIR}"
log "Input file: ${INPUT_FILE}"
log "Result directory: ${RESULT_DIR}"
log "Output file: ${OUTPUT_FILE}"
log "Image directory: ${IMAGE_DIR}"
log "Log file: ${LOG_FILE}"
log "API endpoint: ${API_ENDPOINT}"
log "Total lines: ${TOTAL_LINES}"
log "Send image to API: $([ "${NOIMAGE}" = true ] && echo "No" || echo "Yes")"
log "Download images: $([ "${NODOWNLOAD}" = true ] && echo "No" || echo "Yes")"
log "---"

# Process each line
LINE_NUM=0
SUCCESS_COUNT=0
FAIL_COUNT=0

while IFS= read -r line; do
    LINE_NUM=$((LINE_NUM + 1))
    
    # Check limit
    if [[ ${LINE_NUM} -gt ${TOTAL_LINES} ]]; then
        break
    fi
    
    log "${YELLOW}[${LINE_NUM}/${TOTAL_LINES}]${NC} Processing..."
    
    # Extract data.input from JSONL
    INPUT_DATA=$(echo "${line}" | jq -r '.data | fromjson | .input')
    
    if [[ -z "${INPUT_DATA}" || "${INPUT_DATA}" == "null" ]]; then
        log "${RED}[${LINE_NUM}/${TOTAL_LINES}] Error: Failed to extract input data${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi
    
    # Parse input data: "Title: ...\nCategory: ...\nImage: ..."
    PRODUCT_NAME=$(echo "${INPUT_DATA}" | sed -n 's/^Title: //p')
    CATEGORY=$(echo "${INPUT_DATA}" | sed -n 's/^Category: //p')
    IMAGE_URL=$(echo "${INPUT_DATA}" | sed -n 's/^Image: //p')
    
    IMAGE_PATH=""
    
    # Handle image download based on flags
    if [ "${NODOWNLOAD}" = false ] && [[ -n "${IMAGE_URL}" && "${IMAGE_URL}" != "null" ]]; then
        # Extract original filename from URL
        ORIGINAL_FILENAME=$(basename "${IMAGE_URL}" | sed 's/?.*$//' | sed 's/{.*}//g')
        
        # Get file extension from original filename or URL
        IMAGE_EXT=$(echo "${ORIGINAL_FILENAME}" | grep -o '\.\(jpg\|jpeg\|png\|gif\|webp\)' | head -1)
        if [[ -z "${IMAGE_EXT}" ]]; then
            IMAGE_EXT=".jpg"
        fi
        
        # Remove extension from original filename to get base name
        ORIGINAL_BASENAME=$(basename "${ORIGINAL_FILENAME}" "${IMAGE_EXT}")
        
        # Create filename with 4-digit number prefix
        IMAGE_FILENAME=$(printf "%04d__%s%s" "${LINE_NUM}" "${ORIGINAL_BASENAME}" "${IMAGE_EXT}")
        IMAGE_PATH="${IMAGE_DIR}/${IMAGE_FILENAME}"
        
        # Download image
        if curl -s -f -L -o "${IMAGE_PATH}" "${IMAGE_URL}"; then
            log "${GREEN}[${LINE_NUM}/${TOTAL_LINES}] Image downloaded: ${IMAGE_FILENAME}${NC}"
        else
            log "${RED}[${LINE_NUM}/${TOTAL_LINES}] Failed to download image${NC}"
            IMAGE_PATH=""
        fi
    else
        if [ "${NODOWNLOAD}" = true ]; then
            log "${YELLOW}[${LINE_NUM}/${TOTAL_LINES}] Skipping image download (--nodownload flag)${NC}"
        fi
    fi
    
    # Clear image URL if noimage flag is set
    if [ "${NOIMAGE}" = true ]; then
        IMAGE_URL=""
    fi
    
    # Build JSON request body for API
    REQUEST_BODY=$(jq -n \
        --arg productName "${PRODUCT_NAME}" \
        --arg category "${CATEGORY}" \
        --arg imageUrl "${IMAGE_URL}" \
        '{productName: $productName, category: $category, imageUrl: $imageUrl}')
    
    # Debug: print request
    log "${YELLOW}Request to ${API_ENDPOINT}:${NC}"
    log "$(echo "${REQUEST_BODY}" | jq -c .)"
    
    # Call API using curl
    RESPONSE=$(curl -s -X POST "${API_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "${REQUEST_BODY}" \
        -w "\n%{http_code}" || echo "000")
    
    # Extract HTTP status code (last line)
    HTTP_CODE=$(echo "${RESPONSE}" | tail -1)
    RESPONSE_BODY=$(echo "${RESPONSE}" | sed '$d')
    
    # Check if API call was successful
    if [[ "${HTTP_CODE}" == "200" || "${HTTP_CODE}" == "201" ]]; then
        log "${GREEN}[${LINE_NUM}/${TOTAL_LINES}] API call successful (${HTTP_CODE})${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        
        # Save result to output file
        jq -n \
            --argjson line "${LINE_NUM}" \
            --arg input "${INPUT_DATA}" \
            --argjson output "${RESPONSE_BODY}" \
            --arg image_path "${IMAGE_PATH}" \
            '{line: $line, input: $input, output: $output, image_path: $image_path}' \
            >> "${OUTPUT_FILE}"
    else
        log "${RED}[${LINE_NUM}/${TOTAL_LINES}] API call failed (${HTTP_CODE})${NC}"
        log "${RED}Response: ${RESPONSE_BODY}${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        
        # Save error to output file
        jq -n \
            --argjson line "${LINE_NUM}" \
            --arg input "${INPUT_DATA}" \
            --arg error "HTTP ${HTTP_CODE}: ${RESPONSE_BODY}" \
            --arg image_path "${IMAGE_PATH}" \
            '{line: $line, input: $input, error: $error, image_path: $image_path}' \
            >> "${OUTPUT_FILE}"
    fi
    
    # Delay to avoid overwhelming the API
    sleep "${DELAY}"
    
done < "${INPUT_FILE}"

# Summary
log ""
log "${GREEN}===== Summary =====${NC}"
log "Total processed: ${LINE_NUM}"
log "${GREEN}Success: ${SUCCESS_COUNT}${NC}"
log "${RED}Failed: ${FAIL_COUNT}${NC}"
log "Results saved to: ${OUTPUT_FILE}"
log "Images saved to: ${IMAGE_DIR}/"
log "Log saved to: ${LOG_FILE}"

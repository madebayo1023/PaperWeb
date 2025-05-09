CATEGORIES=(
  # "acc-phys"
  # "adap-org"
  # "alg-geom"
  # "ao-sci"
  "arxiv" 
  # "astro-ph"
  # "atom-ph"
  # "bayes-an"
  # "chao-dyn"
  # "chem-ph"
  # "cmp-lg"
  # "comp-gas"
  # "cond-mat"
  # "cs"
  # "dg-ga"
  # "funct-an"
  # "gr-qc"
  # "hep-ex"
  # "hep-lat"
  # "hep-ph"
  # "hep-th"
  # "math-ph"
  # "math"
  # "mtrl-th"
  # "nlin"
  # "nucl-ex"
  # "nucl-th"
  # "patt-sol"
  # "physics"
  # "plasm-ph"
  # "q-alg"
  # "q-bio"
  # "quant-ph"
  # "solv-int"
  # "supr-con"
)

GCS_BASE="gs://arxiv-dataset/arxiv"
DEST_BASE="/Volumes/My Passport/arxiv_data"

if [[ "$(uname)" == "Darwin" ]]; then
  export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
  GSUTIL_OPTIONS="-o GSUtil:parallel_process_count=1 -o GSUtil:parallel_thread_count=100 -o GSUtil:parallel_composite_upload_threshold=150M"
  export CLOUDSDK_CORE_DISABLE_PROMPTS=1
  echo "Running on macOS: Using multithreading only (no multiprocessing) to prevent crashes"
else
  GSUTIL_OPTIONS="-m"
fi

export PARALLEL_COMPOSITE_UPLOAD_THRESHOLD=150G
export BOTO_CONFIG=/dev/null

mkdir -p "$DEST_BASE" || { echo "FATAL: Cannot create base destination directory: $DEST_BASE"; exit 1; }

for category in "${CATEGORIES[@]}"; do
  SOURCE_BASE="${GCS_BASE}/${category}/pdf"
  TARGET_BASE="${DEST_BASE}/${category}/pdf"

  echo "Processing category: $category"
  
  echo "  Checking ${SOURCE_BASE}/"
  subdirs=$(gsutil ls "${SOURCE_BASE}/" 2>/dev/null)
  
  if [ $? -ne 0 ] || [ -z "$subdirs" ]; then
    echo "  Source directory ${SOURCE_BASE}/ does not exist or is empty. Skipping."
    continue
  fi
  
  for item in $subdirs; do
    if [[ "$item" != */ ]]; then
      continue
    fi
    
    subdir_name=$(basename "${item%/}")
    TARGET_DIR="${TARGET_BASE}/${subdir_name}"
    
    echo "  Processing subdirectory: ${subdir_name}"
    
    mkdir -p "$TARGET_DIR" || { 
      echo "    ERROR: Could not create target directory: $TARGET_DIR. Skipping."
      continue
    }
    
    if [ -d "$TARGET_DIR" ]; then
      echo "    Checking if directory needs updating..."
      
      # Use gsutil to check if the directory is up to date
      source_count=$(gsutil ls "${item}" | grep -v '/$' | wc -l)
      target_count=$(find "$TARGET_DIR" -type f | wc -l)
      
      if [ "$source_count" -le "$target_count" ]; then
        echo "    SKIPPING: Target directory already has same or more files than source ($target_count vs $source_count)"
        continue
      fi
    fi
    
    echo "    Copying entire directory with recursive transfer: ${item} -> ${TARGET_DIR}"
    gsutil $GSUTIL_OPTIONS cp -r "${item}*" "${TARGET_DIR}/" 2>&1 | grep -v "run significantly faster if you instead use gsutil -m"
    
    if [ $? -eq 0 ]; then
      echo "    SUCCESS: Copied directory ${subdir_name}"
    else
      echo "    ERROR: Failed to copy directory ${subdir_name}"
    fi
    
    echo "    Completed processing subdirectory: ${subdir_name}"
  done
  
  echo "  Completed processing for category: $category"
done

echo "-----------------------------------------"
echo "All categories processed."
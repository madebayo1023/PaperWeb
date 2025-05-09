#!/bin/bash

# arXiv Pipeline Runner
# Runs arxiv_ripper/arxiv_ripper.py followed by arxiv_ripper/upload_csv.py

# Colors for output
RED='\033[0;31m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Running arXiv pipeline processor"
echo ""

# Step 1: Run arxiv_ripper.py from subdirectory
echo -e "${CYAN}"
echo "    _       __  ___         _____    _       _     "
echo "   / \   _ _\ \/ (_)_   __ |  ___|__| |_ ___| |__  "
echo "  / _ \ | '__\  /| \ \ / / | |_ / _ \ __/ __| '_ \ "
echo " / ___ \| |  /  \| |\ V /  |  _|  __/ || (__| | | |"
echo "/_/   \_\_| /_/\_\_| \_/   |_|  \___|\__\___|_| |_|"
echo "                                                   "
echo -e "${NC}"

if [ $# -eq 0 ]; then
    python3 arxiv_ripper/arxiv_ripper.py
else
    python3 arxiv_ripper/arxiv_ripper.py "$1"
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}Error in arxiv_ripper.py${NC}"
    exit 1
fi

# Small delay between scripts
sleep 1

# Step 2: Run upload_csv.py from subdirectory
echo -e "${BLUE}"
echo " _   _       _                 _ _             "
echo "| | | |_ __ | | ___   __ _  __| (_)_ __   __ _ "
echo "| | | | '_ \| |/ _ \ / _\` |/ _\` | | '_ \ / _\` |"
echo "| |_| | |_) | | (_) | (_| | (_| | | | | | (_| |"
echo " \___/| .__/|_|\___/ \__,_|\__,_|_|_| |_|\__, |"
echo "      |_|                                |___/ "
echo "                                               "                                               
echo -e "${NC}"

python3 arxiv_ripper/upload_csv.py

if [ $? -ne 0 ]; then
    echo -e "${RED}Error in upload_csv.py${NC}"
    exit 1
fi

# Completion message
echo -e "${GREEN}"
echo "  ____                      _      _       _ "
echo " / ___|___  _ __ ___  _ __ | | ___| |_ ___| |"
echo "| |   / _ \| '_ \` _ \| '_ \| |/ _ \ __/ _ \ |"
echo "| |__| (_) | | | | | | |_) | |  __/ ||  __/_|"
echo " \____\___/|_| |_| |_| .__/|_|\___|\__\___(_)"
echo "                     |_|                     "
echo -e "${NC}"
exit 0
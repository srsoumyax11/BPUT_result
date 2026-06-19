#!/bin/bash
# run_cli.sh - Runs the python app and then pauses so the user can read the final output

python -u -m cli.main

echo ""
echo "========================================================"
echo "✅ Scraping Completed!"
echo "📂 You can download your Excel files by visiting the /exports/ path."
echo "   (Just add /exports/ to the end of the current website URL)"
echo "========================================================"
echo ""
echo "You can safely close this tab now. The session will disconnect automatically in 10 minutes."
sleep 600

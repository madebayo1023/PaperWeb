echo "Starting rebuild of embeddings database..."

if [ -f embeddings.db ]; then
    echo "Deleting existing embeddings.db file..."
    rm embeddings.db
    echo "embeddings.db deleted successfully."
else
    echo "No existing embeddings.db found."
fi

echo "Rebuilding embeddings database..."
python embed.py

echo "Process completed." 
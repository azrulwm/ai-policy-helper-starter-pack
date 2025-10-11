#!/bin/bash

# Start Ollama server in background
echo "🚀 Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama server to start..."
sleep 5
echo "✅ Ollama server should be ready now!"

echo "✅ Ollama server is ready!"

# Check if llama3.2:1b model exists
echo "🔍 Checking if llama3.2:1b model exists..."
if ollama list | grep -q "llama3.2:1b"; then
    echo "✅ llama3.2:1b model already exists, skipping download"
else
    echo "📥 Downloading llama3.2:1b model (this may take a few minutes)..."
    ollama pull llama3.2:1b
    if [ $? -eq 0 ]; then
        echo "✅ Successfully downloaded llama3.2:1b model!"
    else
        echo "❌ Failed to download llama3.2:1b model"
        exit 1
    fi
fi

# Keep the server running
echo "🎉 Ollama setup complete! Server is running with llama3.2:1b model available."
wait $OLLAMA_PID
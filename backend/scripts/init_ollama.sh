#!/bin/bash
# Script per inizializzare modelli Ollama

echo "🚀 Scaricamento modelli Ollama..."

# Aspetta che Ollama sia pronto
echo "⏳ Attendo che Ollama sia disponibile..."
until curl -f http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done

echo "✅ Ollama disponibile!"

# Scarica modelli
echo "📥 Scaricamento llama3.2:3b (categorizzazione)..."
ollama pull llama3.2:3b

echo "📥 Scaricamento mistral:7b (interpretazione)..."
ollama pull mistral:7b

echo "✅ Modelli Ollama pronti!"
echo ""
echo "Modelli disponibili:"
ollama list

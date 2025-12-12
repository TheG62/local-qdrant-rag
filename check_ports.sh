#!/bin/bash
echo "=== Belegte Ports ===" > /Users/guneyyilmaz/local-qdrant-rag/ports.log
lsof -i -P -n | grep LISTEN | grep -E ':(8[0-9]{3}|3000|5000|11434|6333|6334|9[0-9]{3})' >> /Users/guneyyilmaz/local-qdrant-rag/ports.log 2>&1
echo "" >> /Users/guneyyilmaz/local-qdrant-rag/ports.log
echo "=== Freie Ports Test ===" >> /Users/guneyyilmaz/local-qdrant-rag/ports.log
for port in 8001 8002 8080 8888 9000 9001; do
    if ! lsof -i :$port > /dev/null 2>&1; then
        echo "✓ Port $port ist FREI" >> /Users/guneyyilmaz/local-qdrant-rag/ports.log
    else
        echo "✗ Port $port ist BELEGT" >> /Users/guneyyilmaz/local-qdrant-rag/ports.log
    fi
done
cat /Users/guneyyilmaz/local-qdrant-rag/ports.log

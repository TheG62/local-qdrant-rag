# RAG System Architektur

## Grundkonzept

Retrieval Augmented Generation (RAG) kombiniert Information Retrieval mit generativen Sprachmodellen. Das System besteht aus drei Hauptkomponenten:

1. **Ingestion Pipeline**: Dokumente werden geladen, in Chunks aufgeteilt und als Vektoren gespeichert
2. **Retrieval Engine**: Relevante Chunks werden basierend auf der Nutzeranfrage gefunden
3. **Generation**: Ein LLM generiert Antworten basierend auf den gefundenen Kontextinformationen

## Hybrid Search mit RRF

Reciprocal Rank Fusion (RRF) kombiniert mehrere Ranking-Signale zu einem finalen Score:

```
RRF_Score = Σ 1/(k + rank_i)
```

Dabei ist k typischerweise 60 (empirisch ermittelter Wert). Die Formel gewichtet höhere Ränge stärker und ermöglicht die Fusion von:

- Semantischer Suche (Vector Similarity)
- Volltextsuche (BM25 oder TF-basiert)

## Embedding-Modelle

BGE-M3 ist ein multilinguales Embedding-Modell mit 1024 Dimensionen. Es eignet sich besonders für:

- Deutsche Texte
- Mehrsprachige Dokumente
- Technische Dokumentation

## Chunking-Strategien

Effektives Chunking ist entscheidend für RAG-Qualität:

- **Fixed-Size**: Einfach, aber kann Sätze trennen
- **Sentence-Based**: Respektiert Satzgrenzen
- **Semantic**: Gruppiert thematisch zusammenhängende Abschnitte

Die optimale Chunk-Größe liegt typischerweise zwischen 500 und 1500 Zeichen.

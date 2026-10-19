# Semantic job matching (v0.4.9)

## How the score works

The default score remains explainable and uses four evidence components: role relevance (30 points), skills alignment (35), experience fit (20), and location/work-mode fit (15). When local semantic embeddings are available, the final ranking score is: `70% × rule-based score + 30% × semantic-fit score`.

The semantic-fit score is a heuristic calibration of cosine similarity for ranking job descriptions against the candidate profile. It is not a probability of being hired, and its scale may differ by embedding model. The UI labels the scoring method so users can tell when semantic embeddings were used.

## Enable local embeddings

1. Start Ollama.
2. Pull the embedding model: `ollama pull nomic-embed-text`.
3. In `backend/.env`, set:

```dotenv
SEMANTIC_MATCHING_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

4. Restart the backend.

Ollama's `/api/embed` endpoint returns embeddings for semantic search. This feature uses the candidate profile as a query and job text as documents.

## Fallback behavior

If semantic matching is disabled, the embedding endpoint is unavailable, the model is not installed, the vectors are invalid, or more than 80 jobs need scoring in one request, the relevant rows retain the rule-based score. The UI note should explain which method was used. No job source or application outcome depends on embeddings being available.

## Privacy

Resume/profile text is sent to the local Ollama process configured by the user for embedding. It is not sent to a cloud embedding provider by this feature. Keep Ollama bound to a trusted local/network interface and protect the local machine and resume directory.

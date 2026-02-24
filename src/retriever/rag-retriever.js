/**
 * RAG Retriever
 * Finds similar historical SOWs using vector similarity
 */

const GeminiClient = require('../llm/gemini');
const logger = require('../utils/logger');

class RagRetriever {
  constructor(geminiApiKey) {
    this.gemini = new GeminiClient(geminiApiKey);
    this.index = [];
  }

  /**
   * Load index from file or Qdrant
   */
  loadIndex(indexData) {
    if (Array.isArray(indexData)) {
      this.index = indexData;
    } else if (typeof indexData === 'string') {
      const fs = require('fs');
      this.index = JSON.parse(fs.readFileSync(indexData, 'utf-8'));
    }
    logger.info(`RAG index loaded with ${this.index.length} documents`);
  }

  /**
   * Find similar SOWs based on query text
   */
  async findSimilar(queryText, topK = 5) {
    if (this.index.length === 0) {
      logger.warn('Index is empty, returning empty results');
      return [];
    }

    // Generate embedding for query
    const queryEmbedding = await this.gemini.generateEmbedding(queryText);

    // Calculate similarities
    const similarities = this.index.map(doc => ({
      ...doc,
      score: this.cosineSimilarity(queryEmbedding, doc.embedding)
    }));

    // Sort by similarity and return top K
    const results = similarities
      .sort((a, b) => b.score - a.score)
      .slice(0, topK)
      .map(({ embedding, ...rest }) => rest); // Remove embedding from results

    logger.info(`Found ${results.length} similar SOWs (top score: ${results[0]?.score?.toFixed(3)})`);
    return results;
  }

  /**
   * Find similar SOWs based on structured requirements
   */
  async findSimilarByRequirements(requirements, topK = 5) {
    // Build search query from requirements
    const queryText = this.buildQueryFromRequirements(requirements);
    return this.findSimilar(queryText, topK);
  }

  /**
   * Build search query from requirements
   */
  buildQueryFromRequirements(requirements) {
    const parts = [];

    if (requirements.customer) {
      parts.push(`Customer: ${requirements.customer}`);
    }
    if (requirements.project) {
      parts.push(`Project: ${requirements.project}`);
    }
    if (requirements.industry) {
      parts.push(`Industry: ${requirements.industry}`);
    }
    if (requirements.features && requirements.features.length > 0) {
      parts.push(`Features: ${requirements.features.join(', ')}`);
    }
    if (requirements.integrations && requirements.integrations.length > 0) {
      parts.push(`Integrations: ${requirements.integrations.join(', ')}`);
    }
    if (requirements.modules && requirements.modules.length > 0) {
      parts.push(`Modules: ${requirements.modules.join(', ')}`);
    }
    if (requirements.summary) {
      parts.push(`Summary: ${requirements.summary}`);
    }

    return parts.join('\n');
  }

  /**
   * Calculate cosine similarity between two vectors
   */
  cosineSimilarity(vecA, vecB) {
    if (!vecA || !vecB || vecA.length !== vecB.length) {
      return 0;
    }

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < vecA.length; i++) {
      dotProduct += vecA[i] * vecB[i];
      normA += vecA[i] * vecA[i];
      normB += vecB[i] * vecB[i];
    }

    if (normA === 0 || normB === 0) {
      return 0;
    }

    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  /**
   * Filter results by criteria
   */
  filterResults(results, criteria) {
    return results.filter(doc => {
      if (criteria.industry && doc.industry !== criteria.industry) {
        return false;
      }
      if (criteria.minComplexity) {
        const complexityOrder = { low: 1, medium: 2, high: 3 };
        if (complexityOrder[doc.complexity] < complexityOrder[criteria.minComplexity]) {
          return false;
        }
      }
      if (criteria.requiredFeatures) {
        const hasAllFeatures = criteria.requiredFeatures.every(f =>
          doc.features?.includes(f)
        );
        if (!hasAllFeatures) {
          return false;
        }
      }
      return true;
    });
  }

  /**
   * Get statistics about the index
   */
  getIndexStats() {
    if (this.index.length === 0) {
      return { total: 0 };
    }

    const industries = {};
    const features = {};
    const complexities = {};

    this.index.forEach(doc => {
      // Count industries
      industries[doc.industry || 'unknown'] = (industries[doc.industry || 'unknown'] || 0) + 1;

      // Count features
      (doc.features || []).forEach(f => {
        features[f] = (features[f] || 0) + 1;
      });

      // Count complexity
      complexities[doc.complexity || 'unknown'] = (complexities[doc.complexity || 'unknown'] || 0) + 1;
    });

    return {
      total: this.index.length,
      byIndustry: industries,
      topFeatures: Object.entries(features)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10),
      byComplexity: complexities
    };
  }
}

module.exports = RagRetriever;

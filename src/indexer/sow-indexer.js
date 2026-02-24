/**
 * SOW Indexer
 * Processes historical SOWs and creates embeddings for RAG retrieval
 */

const fs = require('fs');
const path = require('path');
const mammoth = require('mammoth');
const pdfParse = require('pdf-parse');
const GeminiClient = require('../llm/gemini');
const logger = require('../utils/logger');

class SowIndexer {
  constructor(geminiApiKey) {
    this.gemini = new GeminiClient(geminiApiKey);
    this.index = [];
  }

  /**
   * Index all SOWs from a directory
   */
  async indexDirectory(inputDir, outputPath) {
    logger.info(`Indexing SOWs from: ${inputDir}`);

    const files = this.findSowFiles(inputDir);
    logger.info(`Found ${files.length} SOW files`);

    let processed = 0;
    let failed = 0;

    for (const file of files) {
      try {
        const sowData = await this.processSowFile(file);
        if (sowData) {
          this.index.push(sowData);
          processed++;
          if (processed % 50 === 0) {
            logger.info(`Processed ${processed}/${files.length} SOWs`);
          }
        }
      } catch (error) {
        logger.warn(`Failed to process ${file}: ${error.message}`);
        failed++;
      }
    }

    // Save index
    this.saveIndex(outputPath);
    logger.info(`Indexing complete. Processed: ${processed}, Failed: ${failed}`);

    return { processed, failed, total: files.length };
  }

  /**
   * Find all SOW files recursively
   */
  findSowFiles(dir, files = []) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        this.findSowFiles(fullPath, files);
      } else if (this.isSowFile(entry.name)) {
        files.push(fullPath);
      }
    }

    return files;
  }

  /**
   * Check if file is a SOW
   */
  isSowFile(filename) {
    const lower = filename.toLowerCase();
    return (lower.endsWith('.docx') || lower.endsWith('.pdf')) &&
           (lower.includes('sow') || lower.includes('scope') || lower.includes('statement'));
  }

  /**
   * Process a single SOW file
   */
  async processSowFile(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    let text;

    if (ext === '.docx') {
      text = await this.extractTextFromDocx(filePath);
    } else if (ext === '.pdf') {
      text = await this.extractTextFromPdf(filePath);
    } else {
      return null;
    }

    if (!text || text.length < 100) {
      return null;
    }

    // Extract metadata using LLM
    const metadata = await this.extractMetadata(text, filePath);

    // Generate embedding
    const embedding = await this.gemini.generateEmbedding(
      this.createEmbeddingText(metadata)
    );

    return {
      id: path.basename(filePath),
      filePath,
      ...metadata,
      embedding,
      textLength: text.length
    };
  }

  /**
   * Extract text from DOCX
   */
  async extractTextFromDocx(filePath) {
    const buffer = fs.readFileSync(filePath);
    const result = await mammoth.extractRawText({ buffer });
    return result.value;
  }

  /**
   * Extract text from PDF
   */
  async extractTextFromPdf(filePath) {
    const buffer = fs.readFileSync(filePath);
    const data = await pdfParse(buffer);
    return data.text;
  }

  /**
   * Extract metadata from SOW text using LLM
   */
  async extractMetadata(text, filePath) {
    // Truncate text if too long
    const truncatedText = text.substring(0, 15000);

    const prompt = `Extract key information from this SOW document.

Document: ${path.basename(filePath)}

Content (truncated):
${truncatedText}

Return JSON with:
{
  "customer": "Customer name",
  "project": "Project name/description",
  "industry": "Industry (banking/healthcare/ecommerce/telecom/other)",
  "modules": ["List of module IDs or types mentioned"],
  "integrations": ["CRM/API integrations mentioned"],
  "features": ["Key features: IVR, queue, blaster, etc."],
  "complexity": "low/medium/high",
  "summary": "2-3 sentence summary",
  "keywords": ["searchable keywords"]
}`;

    try {
      const result = await this.gemini.model.generateContent(prompt);
      const response = await result.response;
      const responseText = response.text();

      const jsonMatch = responseText.match(/```json\n?([\s\S]*?)\n?```/) ||
                        responseText.match(/\{[\s\S]*\}/);

      if (jsonMatch) {
        return JSON.parse(jsonMatch[1] || jsonMatch[0]);
      }
    } catch (error) {
      logger.warn(`Metadata extraction failed for ${filePath}`);
    }

    // Return basic metadata if LLM fails
    return {
      customer: this.extractCustomerFromFilename(filePath),
      project: path.basename(filePath, path.extname(filePath)),
      industry: 'unknown',
      modules: [],
      integrations: [],
      features: [],
      complexity: 'medium',
      summary: '',
      keywords: []
    };
  }

  /**
   * Extract customer name from filename
   */
  extractCustomerFromFilename(filePath) {
    const filename = path.basename(filePath, path.extname(filePath));
    // Common patterns: "SOW_CustomerName_Project" or "CustomerName_SOW_v1"
    const parts = filename.split(/[_\-\s]+/);
    const filtered = parts.filter(p =>
      !p.toLowerCase().match(/^(sow|scope|v\d|version|\d+)$/)
    );
    return filtered[0] || 'Unknown';
  }

  /**
   * Create text for embedding
   */
  createEmbeddingText(metadata) {
    return `
Customer: ${metadata.customer}
Project: ${metadata.project}
Industry: ${metadata.industry}
Features: ${metadata.features?.join(', ')}
Integrations: ${metadata.integrations?.join(', ')}
Modules: ${metadata.modules?.join(', ')}
Summary: ${metadata.summary}
Keywords: ${metadata.keywords?.join(', ')}
    `.trim();
  }

  /**
   * Save index to file
   */
  saveIndex(outputPath) {
    // Save full index
    fs.writeFileSync(
      outputPath,
      JSON.stringify(this.index, null, 2)
    );

    // Save lightweight version (without embeddings) for inspection
    const lightIndex = this.index.map(({ embedding, ...rest }) => rest);
    fs.writeFileSync(
      outputPath.replace('.json', '_metadata.json'),
      JSON.stringify(lightIndex, null, 2)
    );

    logger.info(`Index saved to ${outputPath}`);
  }

  /**
   * Load existing index
   */
  loadIndex(indexPath) {
    if (fs.existsSync(indexPath)) {
      this.index = JSON.parse(fs.readFileSync(indexPath, 'utf-8'));
      logger.info(`Loaded ${this.index.length} SOWs from index`);
    }
    return this.index;
  }
}

module.exports = SowIndexer;

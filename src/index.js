/**
 * SOW Generator - Main Entry Point
 * Orchestrates the full SOW generation pipeline
 */

const fs = require('fs');
const path = require('path');
const GeminiClient = require('./llm/gemini');
const RagRetriever = require('./retriever/rag-retriever');
const SowDocxGenerator = require('./generators/sow-docx');
const FlowchartDrawioGenerator = require('./generators/flowchart-drawio');
const { parseTranscript } = require('./utils/pdf-parser');
const logger = require('./utils/logger');

class SowGenerator {
  constructor(apiKey, options = {}) {
    this.gemini = new GeminiClient(apiKey, options.model);
    this.retriever = new RagRetriever(apiKey);
    this.sowGenerator = new SowDocxGenerator();
    this.flowchartGenerator = new FlowchartDrawioGenerator();
    this.moduleCatalog = this.loadModuleCatalog();
  }

  /**
   * Load module catalog
   */
  loadModuleCatalog() {
    const catalogPath = path.join(__dirname, '../data/module-catalog.json');
    if (fs.existsSync(catalogPath)) {
      return JSON.parse(fs.readFileSync(catalogPath, 'utf-8'));
    }
    return {};
  }

  /**
   * Load SOW index for RAG retrieval
   */
  loadIndex(indexPath) {
    if (fs.existsSync(indexPath)) {
      this.retriever.loadIndex(indexPath);
      return true;
    }
    logger.warn(`Index not found at ${indexPath}`);
    return false;
  }

  /**
   * Generate SOW from transcript
   */
  async generate(transcriptPath, options = {}) {
    const {
      outputDir = './output',
      customerOverride,
      projectOverride,
      topK = 5,
      generateFlowchart = true
    } = options;

    // Ensure output directory exists
    fs.mkdirSync(outputDir, { recursive: true });

    // Step 1: Parse transcript
    logger.info('Step 1: Parsing transcript...');
    const transcript = await parseTranscript(transcriptPath);

    // Step 2: Find similar SOWs (if index loaded)
    logger.info('Step 2: Finding similar SOWs...');
    let similarSows = [];
    if (this.retriever.index.length > 0) {
      similarSows = await this.retriever.findSimilar(transcript, topK);
      logger.info(`Found ${similarSows.length} similar SOWs for context`);
    }

    // Step 3: Extract requirements using LLM
    logger.info('Step 3: Extracting requirements...');
    const requirements = await this.gemini.extractRequirements(transcript, similarSows);

    // Apply overrides
    if (customerOverride) requirements.customer = customerOverride;
    if (projectOverride) requirements.project = projectOverride;

    // Step 4: Generate SOW content
    logger.info('Step 4: Generating SOW content...');
    const sowContent = await this.gemini.generateSowContent(
      requirements,
      similarSows,
      this.moduleCatalog
    );

    // Step 5: Generate Word document
    logger.info('Step 5: Creating Word document...');
    const sowFilename = this.generateFilename(sowContent, 'docx');
    const sowPath = path.join(outputDir, sowFilename);
    await this.sowGenerator.generate(sowContent, sowPath);

    const result = { sowPath, sowContent, requirements };

    // Step 6: Generate flowchart (optional)
    if (generateFlowchart) {
      logger.info('Step 6: Generating flowchart...');
      const flowchartStructure = await this.gemini.generateFlowchartStructure(requirements);
      const flowchartFilename = this.generateFilename(sowContent, 'drawio', '_flow');
      const flowchartPath = path.join(outputDir, flowchartFilename);
      this.flowchartGenerator.generate(flowchartStructure, flowchartPath);
      result.flowchartPath = flowchartPath;
      result.flowchartStructure = flowchartStructure;
    }

    // Save metadata
    const metadataPath = path.join(outputDir, this.generateFilename(sowContent, 'json', '_metadata'));
    fs.writeFileSync(metadataPath, JSON.stringify({
      generatedAt: new Date().toISOString(),
      requirements,
      similarSows: similarSows.map(s => ({ customer: s.customer, project: s.project, score: s.score })),
      files: {
        sow: sowFilename,
        flowchart: result.flowchartPath ? path.basename(result.flowchartPath) : null
      }
    }, null, 2));

    result.metadataPath = metadataPath;
    return result;
  }

  /**
   * Generate consistent filename
   */
  generateFilename(sowContent, extension, suffix = '') {
    const customer = (sowContent.customer || 'Unknown')
      .replace(/[^a-zA-Z0-9]/g, '_')
      .substring(0, 30);
    const project = (sowContent.project || 'Project')
      .replace(/[^a-zA-Z0-9]/g, '_')
      .substring(0, 30);
    const version = sowContent.version || '1.0.0';

    return `SOW_${customer}_${project}${suffix}_v${version}.${extension}`;
  }

  /**
   * Generate from structured requirements (skip extraction)
   */
  async generateFromRequirements(requirements, options = {}) {
    const {
      outputDir = './output',
      topK = 5,
      generateFlowchart = true
    } = options;

    fs.mkdirSync(outputDir, { recursive: true });

    // Find similar SOWs
    let similarSows = [];
    if (this.retriever.index.length > 0) {
      similarSows = await this.retriever.findSimilarByRequirements(requirements, topK);
    }

    // Generate SOW content
    const sowContent = await this.gemini.generateSowContent(
      requirements,
      similarSows,
      this.moduleCatalog
    );

    // Generate documents
    const sowPath = path.join(outputDir, this.generateFilename(sowContent, 'docx'));
    await this.sowGenerator.generate(sowContent, sowPath);

    const result = { sowPath, sowContent };

    if (generateFlowchart) {
      const flowchartStructure = await this.gemini.generateFlowchartStructure(requirements);
      const flowchartPath = path.join(outputDir, this.generateFilename(sowContent, 'drawio', '_flow'));
      this.flowchartGenerator.generate(flowchartStructure, flowchartPath);
      result.flowchartPath = flowchartPath;
    }

    return result;
  }
}

module.exports = SowGenerator;

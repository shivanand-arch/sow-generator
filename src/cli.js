#!/usr/bin/env node

/**
 * SOW Generator CLI
 * Command-line interface for generating SOWs from transcripts
 */

const { program } = require('commander');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const SowGenerator = require('./index');
const SowIndexer = require('./indexer/sow-indexer');
const logger = require('./utils/logger');

program
  .name('sow-gen')
  .description('AI-powered SOW generator with RAG-based learning')
  .version('1.0.0');

// Generate command
program
  .command('generate')
  .description('Generate SOW from a call transcript')
  .requiredOption('-t, --transcript <path>', 'Path to transcript file (PDF or text)')
  .option('-o, --output <dir>', 'Output directory', './output')
  .option('-c, --customer <name>', 'Customer name (overrides extracted)')
  .option('-p, --project <name>', 'Project name (overrides extracted)')
  .option('-k, --top-k <number>', 'Number of similar SOWs to use', '5')
  .option('--no-flowchart', 'Skip flowchart generation')
  .action(async (options) => {
    try {
      const apiKey = process.env.GEMINI_API_KEY;
      if (!apiKey) {
        logger.error('GEMINI_API_KEY environment variable is required');
        process.exit(1);
      }

      const generator = new SowGenerator(apiKey);

      // Load index if available
      const indexPath = path.join(__dirname, '../data/embeddings/index.json');
      if (fs.existsSync(indexPath)) {
        generator.loadIndex(indexPath);
      }

      // Read transcript
      const transcriptPath = path.resolve(options.transcript);
      if (!fs.existsSync(transcriptPath)) {
        logger.error(`Transcript not found: ${transcriptPath}`);
        process.exit(1);
      }

      logger.info(`Generating SOW from: ${transcriptPath}`);

      const result = await generator.generate(transcriptPath, {
        outputDir: path.resolve(options.output),
        customerOverride: options.customer,
        projectOverride: options.project,
        topK: parseInt(options.topK),
        generateFlowchart: options.flowchart
      });

      logger.info('Generation complete!');
      logger.info(`SOW: ${result.sowPath}`);
      if (result.flowchartPath) {
        logger.info(`Flowchart: ${result.flowchartPath}`);
      }
    } catch (error) {
      logger.error(`Generation failed: ${error.message}`);
      process.exit(1);
    }
  });

// Index command
program
  .command('index')
  .description('Index historical SOWs for RAG retrieval')
  .requiredOption('-i, --input <dir>', 'Directory containing SOW files')
  .option('-o, --output <path>', 'Output index file', './data/embeddings/index.json')
  .action(async (options) => {
    try {
      const apiKey = process.env.GEMINI_API_KEY;
      if (!apiKey) {
        logger.error('GEMINI_API_KEY environment variable is required');
        process.exit(1);
      }

      const indexer = new SowIndexer(apiKey);
      const inputDir = path.resolve(options.input);
      const outputPath = path.resolve(options.output);

      // Create output directory if needed
      fs.mkdirSync(path.dirname(outputPath), { recursive: true });

      logger.info(`Indexing SOWs from: ${inputDir}`);
      const result = await indexer.indexDirectory(inputDir, outputPath);

      logger.info('Indexing complete!');
      logger.info(`Processed: ${result.processed}, Failed: ${result.failed}, Total: ${result.total}`);
    } catch (error) {
      logger.error(`Indexing failed: ${error.message}`);
      process.exit(1);
    }
  });

// Stats command
program
  .command('stats')
  .description('Show statistics about indexed SOWs')
  .option('-i, --index <path>', 'Index file path', './data/embeddings/index.json')
  .action(async (options) => {
    try {
      const indexPath = path.resolve(options.index);
      if (!fs.existsSync(indexPath)) {
        logger.error(`Index not found: ${indexPath}`);
        process.exit(1);
      }

      const RagRetriever = require('./retriever/rag-retriever');
      const retriever = new RagRetriever(process.env.GEMINI_API_KEY);
      retriever.loadIndex(indexPath);

      const stats = retriever.getIndexStats();

      console.log('\n📊 SOW Index Statistics\n');
      console.log(`Total SOWs: ${stats.total}`);

      console.log('\nBy Industry:');
      Object.entries(stats.byIndustry).forEach(([industry, count]) => {
        console.log(`  ${industry}: ${count}`);
      });

      console.log('\nTop Features:');
      stats.topFeatures.forEach(([feature, count]) => {
        console.log(`  ${feature}: ${count}`);
      });

      console.log('\nBy Complexity:');
      Object.entries(stats.byComplexity).forEach(([complexity, count]) => {
        console.log(`  ${complexity}: ${count}`);
      });
    } catch (error) {
      logger.error(`Stats failed: ${error.message}`);
      process.exit(1);
    }
  });

// Search command
program
  .command('search')
  .description('Search for similar SOWs')
  .requiredOption('-q, --query <text>', 'Search query')
  .option('-k, --top-k <number>', 'Number of results', '5')
  .option('-i, --index <path>', 'Index file path', './data/embeddings/index.json')
  .action(async (options) => {
    try {
      const apiKey = process.env.GEMINI_API_KEY;
      if (!apiKey) {
        logger.error('GEMINI_API_KEY environment variable is required');
        process.exit(1);
      }

      const indexPath = path.resolve(options.index);
      if (!fs.existsSync(indexPath)) {
        logger.error(`Index not found: ${indexPath}`);
        process.exit(1);
      }

      const RagRetriever = require('./retriever/rag-retriever');
      const retriever = new RagRetriever(apiKey);
      retriever.loadIndex(indexPath);

      const results = await retriever.findSimilar(options.query, parseInt(options.topK));

      console.log(`\n🔍 Search Results for: "${options.query}"\n`);
      results.forEach((result, i) => {
        console.log(`${i + 1}. ${result.customer} - ${result.project}`);
        console.log(`   Score: ${result.score?.toFixed(3)} | Industry: ${result.industry}`);
        console.log(`   Features: ${result.features?.slice(0, 3).join(', ')}`);
        console.log(`   File: ${result.filePath}\n`);
      });
    } catch (error) {
      logger.error(`Search failed: ${error.message}`);
      process.exit(1);
    }
  });

program.parse();

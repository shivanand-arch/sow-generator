#!/usr/bin/env node

/**
 * Google Drive SOW Indexer
 * Downloads and indexes SOWs from Google Drive
 *
 * Prerequisites:
 * 1. Enable Google Drive API in Google Cloud Console
 * 2. Create OAuth credentials (Desktop application)
 * 3. Download credentials.json to this directory
 *
 * Usage:
 * node gdrive-indexer.js --folder-id "0AFw1rcSDgqHiUk9PVA" --output ./data/embeddings
 */

const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { program } = require('commander');
require('dotenv').config();

const GeminiClient = require('../llm/gemini');
const logger = require('../utils/logger');

// OAuth2 scopes
const SCOPES = ['https://www.googleapis.com/auth/drive.readonly'];
const TOKEN_PATH = path.join(__dirname, '../../config/gdrive-token.json');
const CREDENTIALS_PATH = path.join(__dirname, '../../config/credentials.json');

class GDriveIndexer {
  constructor(apiKey) {
    this.gemini = new GeminiClient(apiKey);
    this.drive = null;
    this.index = [];
  }

  /**
   * Authorize with Google Drive
   */
  async authorize() {
    const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf-8'));
    const { client_secret, client_id, redirect_uris } = credentials.installed;
    const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

    // Check for existing token
    if (fs.existsSync(TOKEN_PATH)) {
      const token = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf-8'));
      oAuth2Client.setCredentials(token);
    } else {
      await this.getAccessToken(oAuth2Client);
    }

    this.drive = google.drive({ version: 'v3', auth: oAuth2Client });
    logger.info('Google Drive authorized');
  }

  /**
   * Get new access token
   */
  async getAccessToken(oAuth2Client) {
    const authUrl = oAuth2Client.generateAuthUrl({
      access_type: 'offline',
      scope: SCOPES,
    });

    console.log('Authorize this app by visiting:', authUrl);

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    return new Promise((resolve, reject) => {
      rl.question('Enter the code from that page: ', async (code) => {
        rl.close();
        try {
          const { tokens } = await oAuth2Client.getToken(code);
          oAuth2Client.setCredentials(tokens);
          fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens));
          resolve();
        } catch (err) {
          reject(err);
        }
      });
    });
  }

  /**
   * List all SOW files in a folder
   */
  async listSowFiles(folderId, pageToken = null) {
    const query = `'${folderId}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false`;

    const response = await this.drive.files.list({
      q: query,
      pageSize: 100,
      pageToken,
      fields: 'nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, webViewLink)',
    });

    return {
      files: response.data.files,
      nextPageToken: response.data.nextPageToken,
    };
  }

  /**
   * Get all SOW files recursively
   */
  async getAllSowFiles(folderId) {
    const allFiles = [];
    let pageToken = null;

    do {
      const { files, nextPageToken } = await this.listSowFiles(folderId, pageToken);
      allFiles.push(...files.filter(f => this.isSowFile(f.name)));
      pageToken = nextPageToken;
      logger.info(`Found ${allFiles.length} SOW files so far...`);
    } while (pageToken);

    return allFiles;
  }

  /**
   * Check if file is a SOW
   */
  isSowFile(filename) {
    const lower = filename.toLowerCase();
    return lower.includes('sow') || lower.includes('scope') || lower.includes('statement');
  }

  /**
   * Download and extract text from a Google Doc
   */
  async downloadGoogleDoc(fileId, fileName) {
    try {
      const response = await this.drive.files.export({
        fileId,
        mimeType: 'text/plain',
      });
      return response.data;
    } catch (error) {
      logger.warn(`Failed to download ${fileName}: ${error.message}`);
      return null;
    }
  }

  /**
   * Download and extract text from a file
   */
  async downloadFile(fileId, fileName, mimeType) {
    if (mimeType === 'application/vnd.google-apps.document') {
      return this.downloadGoogleDoc(fileId, fileName);
    }

    // For other file types (docx, pdf), download as bytes
    try {
      const response = await this.drive.files.get({
        fileId,
        alt: 'media',
      }, { responseType: 'arraybuffer' });

      // TODO: Parse docx/pdf - for now return null
      return null;
    } catch (error) {
      logger.warn(`Failed to download ${fileName}: ${error.message}`);
      return null;
    }
  }

  /**
   * Extract metadata from SOW text using LLM
   */
  async extractMetadata(text, fileName) {
    const truncatedText = text.substring(0, 15000);

    const prompt = `Extract key information from this SOW document.

Document: ${fileName}

Content (truncated):
${truncatedText}

Return JSON:
{
  "customer": "Customer name",
  "project": "Project name/description",
  "industry": "banking/healthcare/ecommerce/telecom/education/insurance/other",
  "modules": ["Module types or IDs mentioned"],
  "integrations": ["CRM/API integrations"],
  "features": ["Key features: IVR, queue, blaster, voicebot, etc."],
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
      logger.warn(`Metadata extraction failed for ${fileName}`);
    }

    return this.extractMetadataFromFilename(fileName);
  }

  /**
   * Extract basic metadata from filename
   */
  extractMetadataFromFilename(fileName) {
    // Pattern: SOW_CustomerName_v1.0.0 or similar
    const parts = fileName.replace(/\.docx?$|\.pdf$/i, '').split(/[_\-\s]+/);
    const filtered = parts.filter(p => !p.match(/^(sow|scope|v\d|version|\d+|setup|inline)$/i));

    return {
      customer: filtered[0] || 'Unknown',
      project: filtered.join(' '),
      industry: 'unknown',
      modules: [],
      integrations: [],
      features: [],
      complexity: 'medium',
      summary: '',
      keywords: filtered
    };
  }

  /**
   * Index all SOWs from a Google Drive folder
   */
  async indexFolder(folderId, outputPath) {
    logger.info(`Starting Google Drive indexing for folder: ${folderId}`);

    // Authorize
    await this.authorize();

    // Get all files
    const files = await this.getAllSowFiles(folderId);
    logger.info(`Found ${files.length} SOW files total`);

    let processed = 0;
    let failed = 0;

    for (const file of files) {
      try {
        // Download text
        const text = await this.downloadFile(file.id, file.name, file.mimeType);

        let metadata;
        if (text && text.length > 100) {
          // Extract metadata using LLM
          metadata = await this.extractMetadata(text, file.name);

          // Generate embedding
          const embeddingText = this.createEmbeddingText(metadata);
          const embedding = await this.gemini.generateEmbedding(embeddingText);
          metadata.embedding = embedding;
        } else {
          // Use filename-based metadata
          metadata = this.extractMetadataFromFilename(file.name);
        }

        this.index.push({
          id: file.id,
          fileName: file.name,
          webViewLink: file.webViewLink,
          createdTime: file.createdTime,
          modifiedTime: file.modifiedTime,
          ...metadata
        });

        processed++;
        if (processed % 50 === 0) {
          logger.info(`Processed ${processed}/${files.length} SOWs`);
          // Save intermediate progress
          this.saveIndex(outputPath);
        }
      } catch (error) {
        logger.warn(`Failed to process ${file.name}: ${error.message}`);
        failed++;
      }

      // Rate limiting
      await this.delay(100);
    }

    // Save final index
    this.saveIndex(outputPath);
    logger.info(`Indexing complete. Processed: ${processed}, Failed: ${failed}`);

    return { processed, failed, total: files.length };
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
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, JSON.stringify(this.index, null, 2));

    // Save lightweight version
    const lightIndex = this.index.map(({ embedding, ...rest }) => rest);
    fs.writeFileSync(
      outputPath.replace('.json', '_metadata.json'),
      JSON.stringify(lightIndex, null, 2)
    );

    logger.info(`Index saved: ${this.index.length} documents`);
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// CLI
program
  .requiredOption('-f, --folder-id <id>', 'Google Drive folder ID containing SOWs')
  .option('-o, --output <path>', 'Output index file path', './data/embeddings/gdrive-index.json')
  .parse();

const options = program.opts();

async function main() {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    console.error('GEMINI_API_KEY environment variable required');
    process.exit(1);
  }

  const indexer = new GDriveIndexer(apiKey);
  await indexer.indexFolder(options.folderId, options.output);
}

main().catch(console.error);

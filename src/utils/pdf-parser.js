/**
 * PDF and transcript parser utility
 */

const fs = require('fs');
const path = require('path');
const pdfParse = require('pdf-parse');
const logger = require('./logger');

/**
 * Parse transcript from various file formats
 */
async function parseTranscript(filePath) {
  const ext = path.extname(filePath).toLowerCase();

  if (ext === '.pdf') {
    return parsePdf(filePath);
  } else if (ext === '.txt' || ext === '.md') {
    return parseText(filePath);
  } else if (ext === '.json') {
    return parseJson(filePath);
  } else {
    throw new Error(`Unsupported file format: ${ext}`);
  }
}

/**
 * Parse PDF file
 */
async function parsePdf(filePath) {
  logger.info(`Parsing PDF: ${filePath}`);
  const buffer = fs.readFileSync(filePath);
  const data = await pdfParse(buffer);
  return data.text;
}

/**
 * Parse text file
 */
function parseText(filePath) {
  logger.info(`Parsing text file: ${filePath}`);
  return fs.readFileSync(filePath, 'utf-8');
}

/**
 * Parse JSON file (for structured input)
 */
function parseJson(filePath) {
  logger.info(`Parsing JSON: ${filePath}`);
  const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));

  // If it's structured requirements, convert to text for processing
  if (data.transcript) {
    return data.transcript;
  }

  // Convert structured data to text representation
  const parts = [];
  if (data.customer) parts.push(`Customer: ${data.customer}`);
  if (data.project) parts.push(`Project: ${data.project}`);
  if (data.summary) parts.push(`Summary: ${data.summary}`);
  if (data.requirements) {
    parts.push('Requirements:');
    data.requirements.forEach(r => parts.push(`- ${r}`));
  }

  return parts.join('\n');
}

module.exports = { parseTranscript, parsePdf, parseText, parseJson };

/**
 * Gemini API Wrapper
 * Handles all LLM interactions using Google's Gemini 3 Flash
 */

const { GoogleGenerativeAI } = require('@google/generative-ai');
const logger = require('../utils/logger');

class GeminiClient {
  constructor(apiKey, model = 'gemini-3-flash') {
    this.genAI = new GoogleGenerativeAI(apiKey);
    this.model = this.genAI.getGenerativeModel({ model });
    this.modelName = model;
  }

  /**
   * Extract structured requirements from a call transcript
   */
  async extractRequirements(transcript, similarSows = []) {
    const systemPrompt = this.buildExtractionPrompt(similarSows);

    const prompt = `${systemPrompt}

## Call Transcript to Analyze:

${transcript}

## Output Format:
Return a valid JSON object with the extracted requirements.`;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      const text = response.text();

      // Extract JSON from response
      const jsonMatch = text.match(/```json\n?([\s\S]*?)\n?```/) ||
                        text.match(/\{[\s\S]*\}/);

      if (jsonMatch) {
        const jsonStr = jsonMatch[1] || jsonMatch[0];
        return JSON.parse(jsonStr);
      }

      throw new Error('No valid JSON found in response');
    } catch (error) {
      logger.error('Failed to extract requirements:', error);
      throw error;
    }
  }

  /**
   * Generate SOW content based on requirements
   */
  async generateSowContent(requirements, similarSows = [], moduleCatalog = {}) {
    const prompt = `You are an expert technical writer for Exotel, a cloud communications platform.

## Task
Generate a detailed Statement of Work (SOW) based on the requirements below.

## Similar Past SOWs for Reference:
${similarSows.map((sow, i) => `
### Example ${i + 1}: ${sow.customer} - ${sow.project}
Modules Used: ${sow.modules?.join(', ') || 'N/A'}
Summary: ${sow.summary || 'N/A'}
`).join('\n')}

## Module Catalog (use exact module IDs):
${JSON.stringify(moduleCatalog, null, 2)}

## Requirements:
${JSON.stringify(requirements, null, 2)}

## Output Format:
Return a JSON object with this structure:
{
  "customer": "Customer Name",
  "project": "Project Name",
  "date": "YYYY-MM-DD",
  "version": "1.0.0",
  "attendees": [{"name": "Name", "role": "Role", "company": "Company"}],
  "businessGoals": ["Goal 1", "Goal 2"],
  "prerequisites": [{"item": "Description", "status": "Required/Optional"}],
  "modules": [
    {
      "id": "MODULE-ID",
      "name": "Module Name",
      "description": "What it does",
      "configuration": "Specific configuration details",
      "dependencies": ["Other module IDs if any"]
    }
  ],
  "timeline": [
    {"phase": "Phase Name", "activities": "Description", "duration": "X days"}
  ],
  "totalDuration": "X days",
  "notes": ["Note 1", "Note 2"],
  "assumptions": ["Assumption 1", "Assumption 2"],
  "escalationMatrix": [
    {"level": "L1", "contact": "Name", "role": "Role", "responseTime": "X hours"}
  ]
}`;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      const text = response.text();

      const jsonMatch = text.match(/```json\n?([\s\S]*?)\n?```/) ||
                        text.match(/\{[\s\S]*\}/);

      if (jsonMatch) {
        const jsonStr = jsonMatch[1] || jsonMatch[0];
        return JSON.parse(jsonStr);
      }

      throw new Error('No valid JSON found in response');
    } catch (error) {
      logger.error('Failed to generate SOW content:', error);
      throw error;
    }
  }

  /**
   * Generate flowchart structure
   */
  async generateFlowchartStructure(requirements) {
    const prompt = `You are an expert at creating IVR and call flow diagrams.

## Task
Generate a flowchart structure for the following requirements.

## Requirements:
${JSON.stringify(requirements, null, 2)}

## Output Format:
Return a JSON object with this structure:
{
  "title": "Flowchart Title",
  "nodes": [
    {
      "id": "unique_id",
      "type": "start|end|process|decision|api|queue|disconnect",
      "label": "Node Label",
      "sublabel": "Optional subtitle",
      "color": "#HEX_COLOR"
    }
  ],
  "edges": [
    {
      "from": "source_node_id",
      "to": "target_node_id",
      "label": "Optional edge label (Yes/No/etc)",
      "color": "#HEX_COLOR"
    }
  ]
}

Node Types and Colors:
- start/end: #D5E8D4 (green) - ellipse
- process: #DAE8FC (blue) - rectangle
- decision: #FFF2CC (yellow) - diamond
- api: #E1D5E7 (purple) - rectangle
- queue: #D5E8FC (cyan) - rectangle
- disconnect: #F8CECC (red) - ellipse

Generate a complete flow covering all the requirements.`;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      const text = response.text();

      const jsonMatch = text.match(/```json\n?([\s\S]*?)\n?```/) ||
                        text.match(/\{[\s\S]*\}/);

      if (jsonMatch) {
        const jsonStr = jsonMatch[1] || jsonMatch[0];
        return JSON.parse(jsonStr);
      }

      throw new Error('No valid JSON found in response');
    } catch (error) {
      logger.error('Failed to generate flowchart structure:', error);
      throw error;
    }
  }

  /**
   * Build extraction prompt with similar SOW context
   */
  buildExtractionPrompt(similarSows) {
    let prompt = `You are an expert at analyzing call transcripts and meeting notes for Exotel, a cloud communications platform.

## Task
Extract structured requirements from the call transcript below.

## What to Extract:
1. Customer name and contact details
2. Project name and description
3. IVR flow requirements (menu options, prompts, routing)
4. Integration requirements (CRM, API, webhooks)
5. Queue/agent configuration
6. Reporting requirements
7. Timeline expectations
8. Any specific configurations mentioned

## Module Categories to Look For:
- IVR: Welcome messages, DTMF input, language selection, menus
- Integration: CRM (Salesforce, Freshdesk, Zoho), custom APIs, webhooks
- Blaster: Outbound campaigns, voice blasts, SMS
- Queue: Agent routing, callbacks, overflow handling
- Data: Reporting, CDR, analytics`;

    if (similarSows.length > 0) {
      prompt += `

## Similar Past Projects (for context):
${similarSows.map((sow, i) => `
${i + 1}. ${sow.customer} - ${sow.project}
   Industry: ${sow.industry || 'N/A'}
   Modules: ${sow.modules?.slice(0, 5).join(', ') || 'N/A'}
`).join('')}`;
    }

    return prompt;
  }

  /**
   * Generate embeddings for a text (for indexing)
   */
  async generateEmbedding(text) {
    const embeddingModel = this.genAI.getGenerativeModel({
      model: 'text-embedding-004'
    });

    try {
      const result = await embeddingModel.embedContent(text);
      return result.embedding.values;
    } catch (error) {
      logger.error('Failed to generate embedding:', error);
      throw error;
    }
  }
}

module.exports = GeminiClient;

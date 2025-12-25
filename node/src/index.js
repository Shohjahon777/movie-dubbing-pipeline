#!/usr/bin/env node

/**
 * CLI Entry Point
 * Command-line interface for the dubbing pipeline
 */

import { Command } from 'commander';
import { existsSync } from 'fs';
import { resolve, dirname, basename, extname } from 'path';
import { runPipeline } from './pipeline.js';
import config, { ensureDirectories } from './config.js';

const program = new Command();

program
  .name('dubbing-pipeline')
  .description('Movie dubbing pipeline - Translate and dub videos')
  .version('1.0.0');

program
  .requiredOption('-i, --input <path>', 'Input video file path')
  .option('-o, --output <path>', 'Output video file path', null)
  .option('-l, --language <code>', 'Target language code (uzb_Latn or uzb_Cyrl)', config.targetLang)
  .option('--cloud', 'Skip local file validation (for cloud deployment)', false)
  .action(async (options) => {
    try {
      // Ensure directories exist
      ensureDirectories();
      
      // Resolve input path
      const inputPath = resolve(options.input);
      
      // Validate input file
      if (!options.cloud && !existsSync(inputPath)) {
        console.error(`Error: Input file not found: ${inputPath}`);
        process.exit(1);
      }
      
      // Determine output path
      let outputPath = options.output;
      if (!outputPath) {
        const inputDir = dirname(inputPath);
        const inputName = basename(inputPath, extname(inputPath));
        const outputName = `${inputName}_dubbed.mp4`;
        outputPath = resolve(config.outputDir, outputName);
      } else {
        outputPath = resolve(outputPath);
      }
      
      // Update target language if specified
      if (options.language) {
        config.targetLang = options.language;
      }
      
      console.log('\nStarting dubbing pipeline...');
      console.log(`Input: ${inputPath}`);
      console.log(`Output: ${outputPath}`);
      console.log(`Target language: ${config.targetLang}`);
      console.log(`API: ${config.pythonApiUrl}\n`);
      
      // Check if API is available
      try {
        const axios = (await import('axios')).default;
        const response = await axios.get(`${config.pythonApiUrl}/health`, { timeout: 5000 });
        if (response.data.status !== 'healthy') {
          console.error('Error: API is not healthy');
          process.exit(1);
        }
      } catch (error) {
        console.error(`Error: Cannot connect to API at ${config.pythonApiUrl}`);
        console.error('Make sure the Python FastAPI server is running:');
        console.error('  cd python && python app.py');
        process.exit(1);
      }
      
      // Run pipeline
      const result = await runPipeline(inputPath, outputPath);
      
      console.log('\n✓ Pipeline completed successfully!');
      console.log(`Output video: ${result.outputPath}`);
      process.exit(0);
      
    } catch (error) {
      console.error('\n✗ Pipeline failed:', error.message);
      if (error.stack && process.env.DEBUG) {
        console.error(error.stack);
      }
      process.exit(1);
    }
  });

// Parse arguments
program.parse(process.argv);

// Show help if no arguments
if (process.argv.length === 2) {
  program.help();
}

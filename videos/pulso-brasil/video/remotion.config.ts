import { Config } from '@remotion/cli/config';
Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(92);
Config.setConcurrency(3); // MacBook Air 16 GB
Config.setEntryPoint("src/index.ts");

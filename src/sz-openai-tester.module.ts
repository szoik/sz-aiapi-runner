import {Module, Logger} from '@nestjs/common';
import {SzOpenAITesterController} from './sz-openai-tester.controller';
import {SzOpenAIService} from './services/sz-openai.service';

@Module({
  controllers: [SzOpenAITesterController],
  providers: [Logger, SzOpenAIService],
})
export class SzOpenAITesterModule {}

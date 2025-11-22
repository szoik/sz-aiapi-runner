import {Controller, Post, Body, Get, Logger} from '@nestjs/common';
import {ApiTags, ApiOperation, ApiResponse} from '@nestjs/swagger';
import {SzOpenAIService} from './services/sz-openai.service';
import {ProductInfoRequestDto} from './dtos/openai-request.dto';
import {HsCodeResponse, EstimateResponse, EstimateInfoResponse} from './interfaces/openai-response.interface';

@ApiTags('SZ-Tools: OpenAI Tester')
@Controller('sz-openai-tester')
export class SzOpenAITesterController {
  constructor(
    private readonly szOpenAIService: SzOpenAIService,
    private readonly logger: Logger
  ) {}

  @Get('health')
  @ApiOperation({summary: '헬스체크'})
  @ApiResponse({status: 200, description: '정상'})
  healthCheck() {
    return {
      status: 'ok',
      service: 'SZ-OpenAI-Tester',
      timestamp: new Date().toISOString(),
    };
  }

  @Post('hscode')
  @ApiOperation({summary: 'HSCode 조회'})
  @ApiResponse({status: 200, description: 'HSCode 조회 성공', type: Object})
  async getHsCode(@Body() body: ProductInfoRequestDto): Promise<HsCodeResponse> {
    this.logger.log(`[POST /sz-openai-tester/hscode] Request: ${JSON.stringify(body)}`);
    const result = await this.szOpenAIService.getHsCode(body);
    this.logger.log(`[POST /sz-openai-tester/hscode] Response: ${JSON.stringify(result)}`);
    return result;
  }

  @Post('weight-volume')
  @ApiOperation({summary: '무게 및 부피 조회'})
  @ApiResponse({status: 200, description: '무게 및 부피 조회 성공', type: Object})
  async getWeightVolume(@Body() body: ProductInfoRequestDto): Promise<EstimateResponse> {
    this.logger.log(`[POST /sz-openai-tester/weight-volume] Request: ${JSON.stringify(body)}`);
    const result = await this.szOpenAIService.getWeightVolume(body);
    this.logger.log(`[POST /sz-openai-tester/weight-volume] Response: ${JSON.stringify(result)}`);
    return result;
  }

  @Post('estimate-info')
  @ApiOperation({summary: '통합 조회 (HSCode + 무게/부피)'})
  @ApiResponse({status: 200, description: '통합 조회 성공', type: Object})
  async getEstimateInfo(@Body() body: ProductInfoRequestDto): Promise<EstimateInfoResponse> {
    this.logger.log(`[POST /sz-openai-tester/estimate-info] Request: ${JSON.stringify(body)}`);
    const result = await this.szOpenAIService.getEstimateInfo(body);
    this.logger.log(`[POST /sz-openai-tester/estimate-info] Response: ${JSON.stringify(result)}`);
    return result;
  }
}

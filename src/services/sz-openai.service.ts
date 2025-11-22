import {Injectable, Logger} from '@nestjs/common';
import {OpenAI} from 'openai';
import {HsCodeResponse, EstimateResponse, EstimateInfoResponse} from '../interfaces/openai-response.interface';
import {ProductInfoRequestDto} from '../dtos/openai-request.dto';

/**
 * OpenAI 테스트용 서비스 - 독립 실행 버전
 */
@Injectable()
export class SzOpenAIService {
  private readonly openAiClient: OpenAI;

  constructor(private readonly logger: Logger) {
    // 환경변수에서 API 키 가져오기
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error('OPENAI_API_KEY 환경변수가 설정되지 않았습니다.');
    }

    this.openAiClient = new OpenAI({
      apiKey: apiKey,
    });

    this.logger.log('SzOpenAIService 초기화 완료');
  }

  /**
   * HSCode 조회 - Chat Completions API 사용
   * @param params 상품 정보 요청 DTO
   * @returns HSCode 조회 결과
   */
  async getHsCode(params: ProductInfoRequestDto): Promise<HsCodeResponse> {
    const {productName, category, imageUrl} = params;

    try {
      const systemPrompt = `
        You are an expert in HS codes (Harmonized System codes). 
        Analyze the product information and return accurate HS code data in JSON format.
        I need to get the HS code based on Korea because I am purchasing Japanese products and shipping them to Korea.

        1. Instruction
        You receive the following product data as input from the user 
        - Title
        - Category
        - Image URL
        For Image URLs, we'll get an image from the web for interpretation.  

        Use the image's description and the rest of the text data to generate the most appropriate HSCODE for the product entered by the user. 

        2. Output
        Once you have found the appropriate product classification, output the hscode, description of the hscode, probability of the estimation   and the reason for the estimate in JSON format.

        !Don't describe the reasoning process
        !Answers should be in JSON format only. 
        
        Your response must be a valid JSON object with these exact fields:
        - hscode: A string consisting only of numbers without spaces (10-digit HS code). If a valid 10-digit HS code cannot be determined, a 4-digit HS code may be returned instead.
        - hscodeDescription: string (description of what this HS code covers)
        - probability: number (confidence level between 0 and 1)
        - reason: string (explanation for why this HS code was chosen)

        Example response:
        {
          "hscode": "8471601030",
          "hscodeDescription": "Computer mouse is classified under this HS Code. It is an item classified as an input device for a computer.",
          "probability": 0.78,
          "reason": "Based on the product name and category information provided, the product is identified as a mouse. The HS code 8471601030 is based on '84: Machinery (Section XVI - Machinery and mechanical appliances), 8471: Automatic data processing machines and their units, 60: Input devices and output devices, 10: Input devices, 30: Mice'."
        }
      `;

      const userMessage = `Please analyze this product and provide the HS code:

Title: ${productName}
Category: ${category}
Image: ${imageUrl || 'No image provided'}`;

      this.logger.log(`HSCode 조회 요청: ${productName}`);

      const completion = await this.openAiClient.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {role: 'system', content: systemPrompt},
          {role: 'user', content: userMessage},
        ],
        response_format: {type: 'json_object'},
        temperature: 0.01,
      });

      const responseText = completion.choices[0].message.content;
      if (!responseText) {
        throw new Error('OpenAI로부터 응답이 없습니다.');
      }

      const result = JSON.parse(responseText);

      this.logger.log(`HSCode 조회 완료: ${productName} -> ${result.hscode}`);

      return {
        hscode: result.hscode,
        hscodeDescription: result.hscodeDescription,
        probability: result.probability,
        reason: result.reason,
      };
    } catch (error) {
      this.logger.error(`HSCode 조회 실패: ${productName}`, error);
      throw error;
    }
  }

  /**
   * 무게 및 부피 조회 - Chat Completions API 사용
   * @param params 상품 정보 요청 DTO
   * @returns 무게 및 부피 조회 결과
   */
  async getWeightVolume(params: ProductInfoRequestDto): Promise<EstimateResponse> {
    const {productName, category, imageUrl} = params;

    try {
      const systemPrompt = `
        You are a bot responsible for estimating the volume and weight of a product based on its data, focusing on packed volume estimation for items that can be folded, stacked, or compressed.

        # Instructions
        You will receive the following product data from the user:
        - Title
        - Category
        - Image URL
        - Detailed Description

        For Image URLs, retrieve an image from the web for interpretation.
        Use the text data and the image description to generate the most appropriate volume and weight for the product entered by the user.

        # Estimation Process
        Estimate the volume and weight based on the product's category, description, and image analysis. For items that can be folded, stacked, or compressed (e.g., clothing, towels, bedding, bags), estimate a reduced packed volume based on typical packing practices.

        - **Clothing Items:** Use a standard packed volume of 3x15x15 cm and weight of 0.5 kg.
        - **Foldable Items (e.g., towels, bags):** Estimate packed volume based on 50% reduction from their actual size if details indicate foldability or compressibility.
        - **Stackable Items (e.g., boxes, storage containers):** Estimate packed volume considering stacking with a 30% volume reduction.
        - **Non-Foldable/Non-Compressible Items:** Use actual dimensions without reduction.
        - **Papers:** If the product can be reduced in volume by folding or rolling, take that into account and estimate the volume.

        # Output Format
        Provide the estimated weight and volume (including packed volume for foldable/compressible items) in JSON format. The output should include the volume in cm (width, length, depth), the weight in kg, and a brief reason for the estimate.

        # Cautions
        !Do not describe the reasoning process.
        !Keep in mind that foldable or stackable sizes should be standardized for packaging.
        !Answers should be in JSON format only.

        # Example Input and Output
        Input:
        Title: Large Beach Towel
        Category: Home > Towels
        (+image file)

        Output:
        {
          "volume": "20x40x2",
          "packed_volume": "10x20x2",
          "weight": 0.6,
          "reason": "Based on foldability and image analysis."
        }

        Input:
        Title: Collapsible Storage Box
        Category: Home > Storage
        (+image file)

        Output:
        {
          "volume": "40x20x15",
          "packed_volume": "28x15x10",
          "weight": 1.2,
          "reason": "Stacking applied for packed volume estimation."
        }

        Input:
        Title: 1000ml Drink × 12 Bottles
        Category: Food > Beverages
        (+image file)

        Output:
        {
          "volume": "25x35x30",
          "packed_volume": "25x35x30",
          "weight": 12.6,
          "reason": "Quantity from title multiplied for total package estimation."
        }
      `;

      const userMessage = `Please analyze this product and provide volume and weight estimates:

Title: ${productName}
Category: ${category}
Image: ${imageUrl || 'No image provided'}`;

      this.logger.log(`무게/부피 조회 요청: ${productName}`);

      const completion = await this.openAiClient.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {role: 'system', content: systemPrompt},
          {role: 'user', content: userMessage},
        ],
        response_format: {type: 'json_object'},
        temperature: 0.01,
      });

      const responseText = completion.choices[0].message.content;
      if (!responseText) {
        throw new Error('OpenAI로부터 응답이 없습니다.');
      }

      const result = JSON.parse(responseText);

      this.logger.log(`무게/부피 조회 완료: ${productName} -> ${result.weight}kg, ${result.packed_volume}`);

      return {
        volume: result.volume,
        packed_volume: result.packed_volume,
        weight: result.weight,
        reason: result.reason,
      };
    } catch (error) {
      this.logger.error(`무게/부피 조회 실패: ${productName}`, error);
      throw error;
    }
  }

  /**
   * 상품 무게 및 부피 조회 - Chat Completions API 사용
   * @param params 상품 정보 요청 DTO
   * @returns 상품 무게 및 부피 조회 결과
   */
  async getEstimateInfo(params: ProductInfoRequestDto): Promise<EstimateInfoResponse> {
    this.logger.log(`통합 조회 시작: ${params.productName}`);

    const [hsCode, estimate] = await Promise.all([this.getHsCode(params), this.getWeightVolume(params)]);

    this.logger.log(`통합 조회 완료: ${params.productName}`);

    return {hsCode, estimate};
  }
}

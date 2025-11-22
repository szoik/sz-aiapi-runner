export interface HsCodeResponse {
  hscode: string;
  hscodeDescription: string;
  probability: number;
  reason: string;
}

export interface EstimateResponse {
  volume: string;
  packed_volume: string;
  weight: number;
  reason: string;
}

export interface EstimateInfoResponse {
  hsCode: HsCodeResponse;
  estimate: EstimateResponse;
}

import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type {
  AddProviderModelInput,
  CreateProviderRequest,
  Model,
  Provider,
  SetProviderModelPricingInput,
} from "./types";

export async function createProvider(request: CreateProviderRequest): Promise<Provider> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/providers", {
      body: request,
    }),
  );
}

export async function addProviderModel(request: AddProviderModelInput): Promise<Model> {
  const { providerId, ...body } = request;

  return unwrapApiResponse(
    await hifyApiClient.POST("/providers/{provider_id}/models", {
      body,
      params: {
        path: {
          provider_id: providerId,
        },
      },
    }),
  );
}

export async function setProviderModelPricing(
  request: SetProviderModelPricingInput,
): Promise<Model> {
  const { modelId, ...body } = request;

  return unwrapApiResponse(
    await hifyApiClient.PUT("/providers/models/{model_id}/pricing", {
      body,
      params: {
        path: {
          model_id: modelId,
        },
      },
    }),
  );
}

import type { components } from "@/lib/api/generated/schema";

export type AddProviderModelRequest = components["schemas"]["AddProviderModelRequest"];
export type CreateProviderRequest = components["schemas"]["CreateProviderRequest"];
export type Model = components["schemas"]["ModelResponse"];
export type Provider = components["schemas"]["ProviderResponse"];
export type SetProviderModelPricingRequest =
  components["schemas"]["SetProviderModelPricingRequest"];

export type AddProviderModelInput = AddProviderModelRequest & {
  providerId: string;
};

export type SetProviderModelPricingInput = SetProviderModelPricingRequest & {
  modelId: string;
};

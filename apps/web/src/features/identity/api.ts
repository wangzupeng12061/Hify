import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type {
  ActorContext,
  AddTeamMemberInput,
  AuthSession,
  CreateTeamRequest,
  CreateUserRequest,
  DevLoginRequest,
  Membership,
  Team,
  User,
} from "./types";

export async function getCurrentUser(): Promise<ActorContext> {
  return unwrapApiResponse(await hifyApiClient.GET("/auth/me"));
}

export async function createDevSession(
  request: DevLoginRequest = {
    display_name: "Hify Dev User",
    email: "dev@hify.local",
    team_name: "Hify Dev Team",
  },
): Promise<AuthSession> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/auth/dev/session", {
      body: request,
    }),
  );
}

export async function logout(): Promise<void> {
  const result = await hifyApiClient.POST("/auth/logout");
  if (result.error !== undefined || !result.response.ok) {
    await unwrapApiResponse(result);
  }
}

export async function createUser(request: CreateUserRequest): Promise<User> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/identity/users", {
      body: request,
    }),
  );
}

export async function createTeam(request: CreateTeamRequest): Promise<Team> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/identity/teams", {
      body: request,
    }),
  );
}

export async function addTeamMember(request: AddTeamMemberInput): Promise<Membership> {
  const { teamId, ...body } = request;

  return unwrapApiResponse(
    await hifyApiClient.POST("/identity/teams/{team_id}/members", {
      body,
      params: {
        path: {
          team_id: teamId,
        },
      },
    }),
  );
}

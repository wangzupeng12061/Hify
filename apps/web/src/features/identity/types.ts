import type { components } from "@/lib/api/generated/schema";

export type ActorContext = components["schemas"]["ActorContextResponse"];
export type AddTeamMemberRequest = components["schemas"]["AddTeamMemberRequest"];
export type AuthSession = components["schemas"]["AuthSessionResponse"];
export type CreateTeamRequest = components["schemas"]["CreateTeamRequest"];
export type CreateUserRequest = components["schemas"]["CreateUserRequest"];
export type DevLoginRequest = components["schemas"]["DevLoginRequest"];
export type Membership = components["schemas"]["MembershipResponse"];
export type Team = components["schemas"]["TeamResponse"];
export type User = components["schemas"]["UserResponse"];

export type AddTeamMemberInput = AddTeamMemberRequest & {
  teamId: string;
};

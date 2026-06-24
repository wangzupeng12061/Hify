import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { hifyApiClient } from "@/lib/api/client";
import { createHifyQueryClient } from "@/lib/query/query-client";
import {
  useAddTeamMember,
  useCreateDevSession,
  useCreateTeam,
  useCreateUser,
  useCurrentUser,
  useLogout,
} from "@/features/identity";

const apiClientMock = vi.hoisted(() => ({
  GET: vi.fn(),
  POST: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();

  return {
    ...actual,
    hifyApiClient: apiClientMock,
  };
});

describe("identity hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads the current actor context", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: {
        membership_id: "membership-1",
        permissions: ["runs:create"],
        role: "admin",
        team_id: "team-1",
        user_id: "user-1",
      },
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useCurrentUser(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/auth/me");
    expect(result.current.data?.team_id).toBe("team-1");
  });

  it("creates a developer session through the auth API", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: {
        actor: {
          membership_id: "membership-1",
          permissions: ["runs.execute"],
          role: "owner",
          team_id: "team-1",
          user_id: "user-1",
        },
        expires_at: "2026-06-30T00:00:00Z",
      },
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateDevSession(), {
      wrapper: createQueryWrapper(),
    });

    const session = await result.current.mutateAsync({
      display_name: "Hify Dev User",
      email: "dev@hify.local",
      team_name: "Hify Dev Team",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/auth/dev/session", {
      body: {
        display_name: "Hify Dev User",
        email: "dev@hify.local",
        team_name: "Hify Dev Team",
      },
    });
    expect(session.actor.role).toBe("owner");
  });

  it("logs out through the auth API", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: undefined,
      response: new Response(null, { status: 204 }),
    });

    const { result } = renderHook(() => useLogout(), {
      wrapper: createQueryWrapper(),
    });

    await result.current.mutateAsync();

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/auth/logout");
  });

  it("creates a user through the identity API", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: {
        created_at: "2026-06-23T00:00:00Z",
        display_name: "Ada Lovelace",
        email: "ada@example.com",
        id: "user-1",
        status: "active",
        updated_at: "2026-06-23T00:00:00Z",
      },
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateUser(), {
      wrapper: createQueryWrapper(),
    });

    const user = await result.current.mutateAsync({
      display_name: "Ada Lovelace",
      email: "ada@example.com",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/identity/users", {
      body: {
        display_name: "Ada Lovelace",
        email: "ada@example.com",
      },
    });
    expect(user.id).toBe("user-1");
  });

  it("creates a team and adds team members with stable request shapes", async () => {
    apiClientMock.POST
      .mockResolvedValueOnce({
        data: {
          created_at: "2026-06-23T00:00:00Z",
          id: "team-1",
          name: "Platform",
          status: "active",
          updated_at: "2026-06-23T00:00:00Z",
        },
        response: new Response(null, { status: 201 }),
      })
      .mockResolvedValueOnce({
        data: {
          created_at: "2026-06-23T00:00:00Z",
          id: "membership-1",
          role: "member",
          status: "active",
          team_id: "team-1",
          updated_at: "2026-06-23T00:00:00Z",
          user_id: "user-2",
        },
        response: new Response(null, { status: 201 }),
      });

    const wrapper = createQueryWrapper();
    const createTeamHook = renderHook(() => useCreateTeam(), { wrapper });
    const addTeamMemberHook = renderHook(() => useAddTeamMember(), { wrapper });

    await createTeamHook.result.current.mutateAsync({
      name: "Platform",
      owner_user_id: "user-1",
    });
    await addTeamMemberHook.result.current.mutateAsync({
      role: "member",
      teamId: "team-1",
      user_id: "user-2",
    });

    expect(hifyApiClient.POST).toHaveBeenNthCalledWith(1, "/identity/teams", {
      body: {
        name: "Platform",
        owner_user_id: "user-1",
      },
    });
    expect(hifyApiClient.POST).toHaveBeenNthCalledWith(2, "/identity/teams/{team_id}/members", {
      body: {
        role: "member",
        user_id: "user-2",
      },
      params: {
        path: {
          team_id: "team-1",
        },
      },
    });
  });
});

function createQueryWrapper() {
  const queryClient = createHifyQueryClient();

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

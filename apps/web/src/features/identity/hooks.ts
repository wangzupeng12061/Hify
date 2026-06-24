"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { addTeamMember, createDevSession, createTeam, createUser, getCurrentUser, logout } from "./api";

export const identityQueryKeys = {
  all: ["identity"] as const,
  currentUser: () => [...identityQueryKeys.all, "current-user"] as const,
};

export function useCurrentUser() {
  return useQuery({
    queryFn: getCurrentUser,
    queryKey: identityQueryKeys.currentUser(),
  });
}

export function useCreateDevSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createDevSession,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: identityQueryKeys.currentUser() });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: identityQueryKeys.currentUser() });
    },
  });
}

export function useCreateUser() {
  return useMutation({
    mutationFn: createUser,
  });
}

export function useCreateTeam() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createTeam,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: identityQueryKeys.currentUser() });
    },
  });
}

export function useAddTeamMember() {
  return useMutation({
    mutationFn: addTeamMember,
  });
}

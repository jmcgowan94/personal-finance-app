import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filterParams, type DashboardFilters } from "../lib/filters";
import { api } from "./client";
import type {
  Account,
  AccountType,
  BalanceSeries,
  Category,
  CategoryKind,
  CategoryRule,
  CategorySpend,
  MatchType,
  MonthlyPoint,
  Parser,
  Summary,
  TransactionPage,
  Upload,
  User,
} from "./types";

export const useMe = () => useQuery({ queryKey: ["me"], queryFn: () => api.get<User>("/me") });

export function useUpdateMe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<User, "first_name" | "last_name" | "theme" | "default_range" | "default_account_id">>) =>
      api.patch<User>("/me", body),
    onSuccess: (user) => qc.setQueryData(["me"], user),
  });
}

/** Version of the code the server is running; it can't change without a restart. */
export const useVersion = () =>
  useQuery({
    queryKey: ["version"],
    queryFn: () => api.get<{ version: string; commit: string | null }>("/version"),
    staleTime: Infinity,
  });

export const useAccounts = () => useQuery({ queryKey: ["accounts"], queryFn: () => api.get<Account[]>("/accounts") });
export const useParsers = () => useQuery({ queryKey: ["parsers"], queryFn: () => api.get<Parser[]>("/parsers") });
export const useUploads = () => useQuery({ queryKey: ["uploads"], queryFn: () => api.get<Upload[]>("/uploads") });
export const useCategories = () =>
  useQuery({ queryKey: ["categories"], queryFn: () => api.get<Category[]>("/categories") });
export const useRules = () =>
  useQuery({ queryKey: ["category-rules"], queryFn: () => api.get<CategoryRule[]>("/category-rules") });

export interface TransactionQuery {
  date_from?: string;
  account_id?: number;
  category_id?: number;
  q?: string;
  page: number;
  page_size: number;
}

// `enabled` lets pages wait until the user's default time window is known.
export const useTransactions = (params: TransactionQuery, enabled = true) =>
  useQuery({
    queryKey: ["transactions", params],
    queryFn: () => api.get<TransactionPage>("/transactions", { ...params }),
    placeholderData: keepPreviousData,
    enabled,
  });

function useAnalytics<T>(name: string, filters: DashboardFilters, enabled: boolean) {
  return useQuery({
    queryKey: ["analytics", name, filters],
    queryFn: () => api.get<T>(`/analytics/${name}`, filterParams(filters)),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export const useSummary = (f: DashboardFilters, enabled = true) => useAnalytics<Summary>("summary", f, enabled);
export const useMonthly = (f: DashboardFilters, enabled = true) => useAnalytics<MonthlyPoint[]>("monthly", f, enabled);
export const useByCategory = (f: DashboardFilters, enabled = true) =>
  useAnalytics<CategorySpend[]>("by-category", f, enabled);
export const useBalance = (f: DashboardFilters, enabled = true) =>
  useAnalytics<BalanceSeries[]>("balance", f, enabled);

/** Most writes change what the dashboard and transaction list show. */
function useInvalidateData() {
  const qc = useQueryClient();
  return (...extra: string[]) =>
    Promise.all(
      ["transactions", "analytics", ...extra].map((key) => qc.invalidateQueries({ queryKey: [key] })),
    );
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; account_type: AccountType; institution?: string }) =>
      api.post<Account>("/accounts", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  });
}

export function useUploadStatement() {
  const invalidate = useInvalidateData();
  return useMutation({
    mutationFn: ({ file, accountId }: { file: File; accountId: number }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("account_id", String(accountId));
      return api.upload<Upload>("/uploads", form);
    },
    onSuccess: () => invalidate("uploads"),
  });
}

export function useDeleteUpload() {
  const invalidate = useInvalidateData();
  return useMutation({
    mutationFn: (id: number) => api.del(`/uploads/${id}`),
    onSuccess: () => invalidate("uploads"),
  });
}

/** Change a transaction's category and/or use date (null use_date = reset to posting date). */
export function useUpdateTransaction() {
  const invalidate = useInvalidateData();
  return useMutation({
    mutationFn: ({ id, ...changes }: { id: number; category_id?: number | null; use_date?: string | null }) =>
      api.patch(`/transactions/${id}`, changes),
    onSuccess: () => invalidate(),
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; kind: CategoryKind }) => api.post<Category>("/categories", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}

export function useUpdateCategory() {
  const invalidate = useInvalidateData();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; name?: string; kind?: CategoryKind }) =>
      api.patch<Category>(`/categories/${id}`, body),
    onSuccess: () => invalidate("categories"),
  });
}

export function useDeleteCategory() {
  const invalidate = useInvalidateData();
  return useMutation({
    mutationFn: (id: number) => api.del(`/categories/${id}`),
    onSuccess: () => invalidate("categories", "category-rules"),
  });
}

export function useCreateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { category_id: number; pattern: string; match_type: MatchType; priority: number }) =>
      api.post<CategoryRule>("/category-rules", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["category-rules"] }),
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.del(`/category-rules/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["category-rules"] }),
  });
}

export function useApplyRules() {
  const invalidate = useInvalidateData();
  return useMutation({
    mutationFn: () => api.post<{ updated: number }>("/category-rules/apply"),
    onSuccess: () => invalidate(),
  });
}

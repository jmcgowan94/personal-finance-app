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
    mutationFn: (body: Partial<Pick<User, "first_name" | "last_name" | "theme">>) => api.patch<User>("/me", body),
    onSuccess: (user) => qc.setQueryData(["me"], user),
  });
}

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

export const useTransactions = (params: TransactionQuery) =>
  useQuery({
    queryKey: ["transactions", params],
    queryFn: () => api.get<TransactionPage>("/transactions", { ...params }),
    placeholderData: keepPreviousData,
  });

function useAnalytics<T>(name: string, filters: DashboardFilters) {
  return useQuery({
    queryKey: ["analytics", name, filters],
    queryFn: () => api.get<T>(`/analytics/${name}`, filterParams(filters)),
    placeholderData: keepPreviousData,
  });
}

export const useSummary = (f: DashboardFilters) => useAnalytics<Summary>("summary", f);
export const useMonthly = (f: DashboardFilters) => useAnalytics<MonthlyPoint[]>("monthly", f);
export const useByCategory = (f: DashboardFilters) => useAnalytics<CategorySpend[]>("by-category", f);
export const useBalance = (f: DashboardFilters) => useAnalytics<BalanceSeries[]>("balance", f);

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

export function useSetTransactionCategory() {
  const invalidate = useInvalidateData();
  return useMutation({
    mutationFn: ({ id, categoryId }: { id: number; categoryId: number | null }) =>
      api.patch(`/transactions/${id}`, { category_id: categoryId }),
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

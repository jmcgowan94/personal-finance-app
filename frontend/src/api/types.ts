import type { RangePreset } from "../lib/filters";

// Mirrors backend/app/schemas.py. Money values arrive as decimal strings.

export type AccountType = "checking" | "savings" | "credit" | "other";
export type CategoryKind = "expense" | "income" | "transfer";
export type MatchType = "contains" | "regex";

export interface User {
  id: number;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  /** null = follow the device's light/dark setting */
  theme: ThemePreference;
  /** Dashboard time window on launch; null = all time */
  default_range: RangePreset | null;
  /** Account the pages start filtered to; null = all accounts */
  default_account_id: number | null;
}

export type ThemePreference = "light" | "dark" | null;

export interface Account {
  id: number;
  name: string;
  institution: string;
  account_type: AccountType;
  last4: string | null;
}

export interface Parser {
  name: string;
  label: string;
  institution: string;
  account_type: string;
}

export interface Upload {
  id: number;
  account_id: number;
  filename: string;
  parser_name: string;
  rows_total: number;
  rows_imported: number;
  rows_duplicate: number;
  rows_error: number;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  kind: CategoryKind;
}

export interface CategoryRule {
  id: number;
  category_id: number;
  pattern: string;
  match_type: MatchType;
  priority: number;
}

export interface Transaction {
  id: number;
  account_id: number;
  /** Date the bank posted it */
  posting_date: string;
  /** Date it counts under; starts as the posting date, adjustable */
  use_date: string;
  description: string;
  amount: string;
  txn_type: string | null;
  balance: string | null;
  check_number: string | null;
  bank_category: string | null;
  category_id: number | null;
  category_locked: boolean;
}

export interface TransactionPage {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
}

export interface Summary {
  income: string;
  spending: string;
  net: string;
  transaction_count: number;
}

export interface MonthlyPoint {
  month: string;
  income: string;
  spending: string;
  net: string;
  /** Total balance at month end (accounts that report one); null if none yet */
  end_balance: string | null;
}

export interface CategorySpend {
  category_id: number | null;
  category: string;
  spending: string;
}

export interface BalanceSeries {
  account_id: number;
  account: string;
  points: { date: string; balance: string }[];
}

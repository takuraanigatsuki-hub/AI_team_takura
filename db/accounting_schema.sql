-- Бухгалтерия: план счетов, контрагенты, документы и проводки (двойная запись)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounting_accounts (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name_ru TEXT NOT NULL,
    account_type TEXT NOT NULL CHECK (
        account_type IN ('asset', 'liability', 'equity', 'income', 'expense')
    ),
    parent_id TEXT REFERENCES accounting_accounts(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounting_accounts_type
    ON accounting_accounts(account_type);

CREATE INDEX IF NOT EXISTS idx_accounting_accounts_parent
    ON accounting_accounts(parent_id);

CREATE TABLE IF NOT EXISTS accounting_counterparties (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    inn TEXT,
    counterparty_type TEXT NOT NULL DEFAULT 'both' CHECK (
        counterparty_type IN ('client', 'supplier', 'both')
    ),
    email TEXT,
    phone TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounting_counterparties_name
    ON accounting_counterparties(name);

CREATE TABLE IF NOT EXISTS accounting_documents (
    id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL CHECK (
        doc_type IN ('invoice', 'payment', 'receipt', 'act', 'other')
    ),
    number TEXT NOT NULL,
    doc_date TEXT NOT NULL,
    counterparty_id TEXT REFERENCES accounting_counterparties(id),
    description TEXT,
    amount_rub REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (
        status IN ('draft', 'posted', 'cancelled')
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(doc_type, number)
);

CREATE INDEX IF NOT EXISTS idx_accounting_documents_date
    ON accounting_documents(doc_date);

CREATE INDEX IF NOT EXISTS idx_accounting_documents_counterparty
    ON accounting_documents(counterparty_id);

CREATE TABLE IF NOT EXISTS accounting_journal_entries (
    id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES accounting_documents(id),
    entry_date TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (
        status IN ('draft', 'posted', 'cancelled')
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounting_journal_entries_date
    ON accounting_journal_entries(entry_date);

CREATE INDEX IF NOT EXISTS idx_accounting_journal_entries_document
    ON accounting_journal_entries(document_id);

CREATE TABLE IF NOT EXISTS accounting_journal_lines (
    id TEXT PRIMARY KEY,
    entry_id TEXT NOT NULL REFERENCES accounting_journal_entries(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL REFERENCES accounting_accounts(id),
    debit REAL NOT NULL DEFAULT 0,
    credit REAL NOT NULL DEFAULT 0,
    description TEXT,
    line_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    CHECK (debit >= 0 AND credit >= 0),
    CHECK (NOT (debit > 0 AND credit > 0))
);

CREATE INDEX IF NOT EXISTS idx_accounting_journal_lines_entry
    ON accounting_journal_lines(entry_id);

CREATE INDEX IF NOT EXISTS idx_accounting_journal_lines_account
    ON accounting_journal_lines(account_id);

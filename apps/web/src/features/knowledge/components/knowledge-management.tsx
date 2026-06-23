"use client";

import { useMemo, useState, type FormEvent } from "react";

import { HifyApiError } from "@/lib/api/errors";

import {
  useCreateKnowledgeBase,
  useIngestDocument,
  useKnowledgeBases,
  useKnowledgeDocuments,
} from "../hooks";
import type { KnowledgeBase, KnowledgeDocument } from "../types";

type KnowledgeBaseFormState = {
  description: string;
  embeddingModelId: string;
  name: string;
};

type DocumentFormState = {
  content: string;
  sourceUri: string;
  title: string;
};

const initialKnowledgeBaseForm: KnowledgeBaseFormState = {
  description: "",
  embeddingModelId: "",
  name: "",
};

const initialDocumentForm: DocumentFormState = {
  content: "",
  sourceUri: "",
  title: "",
};

const EMPTY_KNOWLEDGE_BASES: KnowledgeBase[] = [];

export function KnowledgeManagement() {
  const knowledgeBasesQuery = useKnowledgeBases();
  const createKnowledgeBaseMutation = useCreateKnowledgeBase();
  const ingestDocumentMutation = useIngestDocument();
  const [knowledgeBaseForm, setKnowledgeBaseForm] = useState(initialKnowledgeBaseForm);
  const [documentForm, setDocumentForm] = useState(initialDocumentForm);
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const knowledgeBases = knowledgeBasesQuery.data ?? EMPTY_KNOWLEDGE_BASES;
  const effectiveKnowledgeBaseId = useMemo(() => {
    if (knowledgeBases.some((knowledgeBase) => knowledgeBase.id === selectedKnowledgeBaseId)) {
      return selectedKnowledgeBaseId;
    }

    return knowledgeBases[0]?.id ?? "";
  }, [knowledgeBases, selectedKnowledgeBaseId]);

  const documentsQuery = useKnowledgeDocuments(
    effectiveKnowledgeBaseId === ""
      ? null
      : {
          knowledgeBaseId: effectiveKnowledgeBaseId,
        },
  );
  const selectedKnowledgeBase = useMemo(
    () => knowledgeBases.find((knowledgeBase) => knowledgeBase.id === effectiveKnowledgeBaseId),
    [effectiveKnowledgeBaseId, knowledgeBases],
  );
  const documents = documentsQuery.data ?? [];

  async function handleCreateKnowledgeBase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      const knowledgeBase = await createKnowledgeBaseMutation.mutateAsync({
        description: knowledgeBaseForm.description.trim() || null,
        embedding_model_id: knowledgeBaseForm.embeddingModelId.trim(),
        name: knowledgeBaseForm.name.trim(),
      });
      setSelectedKnowledgeBaseId(knowledgeBase.id);
      setKnowledgeBaseForm(initialKnowledgeBaseForm);
    } catch (error) {
      if (!(error instanceof HifyApiError)) {
        setFormError(error instanceof Error ? error.message : "Unable to create knowledge base.");
      }
    }
  }

  async function handleIngestDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    if (effectiveKnowledgeBaseId === "") {
      setFormError("Select or create a knowledge base before ingesting a document.");
      return;
    }

    try {
      await ingestDocumentMutation.mutateAsync({
        content: documentForm.content.trim(),
        knowledgeBaseId: effectiveKnowledgeBaseId,
        source_uri: documentForm.sourceUri.trim() || null,
        title: documentForm.title.trim(),
      });
      setDocumentForm(initialDocumentForm);
    } catch (error) {
      if (!(error instanceof HifyApiError)) {
        setFormError(error instanceof Error ? error.message : "Unable to ingest document.");
      }
    }
  }

  const operationError =
    knowledgeBasesQuery.error ??
    documentsQuery.error ??
    createKnowledgeBaseMutation.error ??
    ingestDocumentMutation.error;
  const isSubmitting = createKnowledgeBaseMutation.isPending || ingestDocumentMutation.isPending;

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Knowledge</p>
        <h2>Manage knowledge bases and ingest text documents.</h2>
        <p>
          This first version covers the RAG management surface exposed by the backend: create a
          knowledge base, ingest text content, and inspect indexed documents for a selected base.
        </p>
      </section>

      {formError ? <KnowledgeErrorBanner message={formError} /> : null}
      {operationError ? <KnowledgeErrorBanner error={operationError} /> : null}

      <section className="provider-layout">
        <CreateKnowledgeBaseForm
          form={knowledgeBaseForm}
          isSubmitting={createKnowledgeBaseMutation.isPending}
          onChange={setKnowledgeBaseForm}
          onSubmit={handleCreateKnowledgeBase}
        />
        <IngestDocumentForm
          form={documentForm}
          isDisabled={effectiveKnowledgeBaseId === ""}
          isSubmitting={ingestDocumentMutation.isPending}
          knowledgeBases={knowledgeBases}
          onChange={setDocumentForm}
          onKnowledgeBaseChange={setSelectedKnowledgeBaseId}
          onSubmit={handleIngestDocument}
          selectedKnowledgeBaseId={effectiveKnowledgeBaseId}
        />
      </section>

      <KnowledgeBaseSummary
        isLoading={knowledgeBasesQuery.isLoading}
        isSubmitting={isSubmitting}
        knowledgeBases={knowledgeBases}
        onSelect={setSelectedKnowledgeBaseId}
        selectedKnowledgeBaseId={effectiveKnowledgeBaseId}
      />

      <KnowledgeDocumentsPanel
        documents={documents}
        isLoading={documentsQuery.isLoading}
        selectedKnowledgeBase={selectedKnowledgeBase}
      />
    </div>
  );
}

function CreateKnowledgeBaseForm({
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: {
  form: KnowledgeBaseFormState;
  isSubmitting: boolean;
  onChange: (form: KnowledgeBaseFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 1</p>
      <h2>Create knowledge base</h2>
      <label className="form-field">
        Knowledge base name
        <input
          name="name"
          onChange={(event) => onChange({ ...form, name: event.target.value })}
          required
          value={form.name}
        />
      </label>
      <label className="form-field">
        Description
        <input
          name="description"
          onChange={(event) => onChange({ ...form, description: event.target.value })}
          placeholder="Optional"
          value={form.description}
        />
      </label>
      <label className="form-field">
        Embedding model ID
        <input
          name="embeddingModelId"
          onChange={(event) => onChange({ ...form, embeddingModelId: event.target.value })}
          required
          value={form.embeddingModelId}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating..." : "Create knowledge base"}
      </button>
    </form>
  );
}

function IngestDocumentForm({
  form,
  isDisabled,
  isSubmitting,
  knowledgeBases,
  onChange,
  onKnowledgeBaseChange,
  onSubmit,
  selectedKnowledgeBaseId,
}: {
  form: DocumentFormState;
  isDisabled: boolean;
  isSubmitting: boolean;
  knowledgeBases: KnowledgeBase[];
  onChange: (form: DocumentFormState) => void;
  onKnowledgeBaseChange: (knowledgeBaseId: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  selectedKnowledgeBaseId: string;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 2</p>
      <h2>Ingest document</h2>
      <label className="form-field">
        Knowledge base
        <select
          disabled={knowledgeBases.length === 0}
          name="knowledgeBaseId"
          onChange={(event) => onKnowledgeBaseChange(event.target.value)}
          required
          value={selectedKnowledgeBaseId}
        >
          {knowledgeBases.length === 0 ? <option value="">No knowledge base</option> : null}
          {knowledgeBases.map((knowledgeBase) => (
            <option key={knowledgeBase.id} value={knowledgeBase.id}>
              {knowledgeBase.name}
            </option>
          ))}
        </select>
      </label>
      <label className="form-field">
        Document title
        <input
          disabled={isDisabled}
          name="title"
          onChange={(event) => onChange({ ...form, title: event.target.value })}
          required
          value={form.title}
        />
      </label>
      <label className="form-field">
        Source URI
        <input
          disabled={isDisabled}
          name="sourceUri"
          onChange={(event) => onChange({ ...form, sourceUri: event.target.value })}
          placeholder="Optional"
          value={form.sourceUri}
        />
      </label>
      <label className="form-field">
        Document content
        <textarea
          disabled={isDisabled}
          name="content"
          onChange={(event) => onChange({ ...form, content: event.target.value })}
          required
          rows={9}
          value={form.content}
        />
      </label>
      <button className="button" disabled={isDisabled || isSubmitting} type="submit">
        {isSubmitting ? "Ingesting..." : "Ingest document"}
      </button>
    </form>
  );
}

function KnowledgeBaseSummary({
  isLoading,
  isSubmitting,
  knowledgeBases,
  onSelect,
  selectedKnowledgeBaseId,
}: {
  isLoading: boolean;
  isSubmitting: boolean;
  knowledgeBases: KnowledgeBase[];
  onSelect: (knowledgeBaseId: string) => void;
  selectedKnowledgeBaseId: string;
}) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Knowledge bases</p>
          <h2>RAG sources</h2>
        </div>
        <span className="status-pill">{isSubmitting ? "Updating" : "Ready"}</span>
      </div>
      {isLoading ? <p className="muted">Loading knowledge bases...</p> : null}
      {!isLoading && knowledgeBases.length === 0 ? (
        <p className="muted">No knowledge bases yet. Create one to start ingesting documents.</p>
      ) : null}
      {knowledgeBases.length > 0 ? (
        <ul className="timeline-list">
          {knowledgeBases.map((knowledgeBase) => (
            <li className="timeline-list__item conversation-list-item" key={knowledgeBase.id}>
              <div>
                <span>{knowledgeBase.status}</span>
                <h3>{knowledgeBase.name}</h3>
                <p className="muted">{knowledgeBase.description ?? "No description"}</p>
                <p className="form-result">
                  <strong>Documents:</strong> {knowledgeBase.document_count} ·{" "}
                  <strong>Chunks:</strong> {knowledgeBase.chunk_count} ·{" "}
                  <strong>Embedding model:</strong> <code>{knowledgeBase.embedding_model_id}</code>
                </p>
              </div>
              <button
                className="button button--secondary"
                disabled={knowledgeBase.id === selectedKnowledgeBaseId}
                onClick={() => onSelect(knowledgeBase.id)}
                type="button"
              >
                {knowledgeBase.id === selectedKnowledgeBaseId ? "Selected" : "View documents"}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function KnowledgeDocumentsPanel({
  documents,
  isLoading,
  selectedKnowledgeBase,
}: {
  documents: KnowledgeDocument[];
  isLoading: boolean;
  selectedKnowledgeBase?: KnowledgeBase;
}) {
  const summaryItems = useMemo(
    () => [
      { label: "Selected base", value: selectedKnowledgeBase?.name ?? "Not selected" },
      { label: "Knowledge base ID", value: selectedKnowledgeBase?.id ?? "Not available" },
      { label: "Documents", value: `${selectedKnowledgeBase?.document_count ?? 0}` },
      { label: "Chunks", value: `${selectedKnowledgeBase?.chunk_count ?? 0}` },
    ],
    [selectedKnowledgeBase],
  );

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Documents</p>
          <h2>Indexed document list</h2>
        </div>
        <span className="status-pill">{isLoading ? "Loading" : `${documents.length} loaded`}</span>
      </div>
      <dl className="identity-grid">
        {summaryItems.map((item) => (
          <ResultField key={item.label} label={item.label} value={item.value} />
        ))}
      </dl>
      {selectedKnowledgeBase === undefined ? (
        <p className="muted">Select a knowledge base to view its documents.</p>
      ) : null}
      {selectedKnowledgeBase !== undefined && documents.length === 0 && !isLoading ? (
        <p className="muted">No documents have been ingested into this knowledge base yet.</p>
      ) : null}
      {documents.length > 0 ? (
        <ul className="timeline-list">
          {documents.map((document) => (
            <li className="timeline-list__item" key={document.id}>
              <span>{document.status}</span>
              <p>{document.title}</p>
              <p className="form-result">
                <strong>Document ID:</strong> <code>{document.id}</code>
              </p>
              <p className="form-result">
                <strong>Chunks:</strong> {document.chunk_count} · <strong>Source:</strong>{" "}
                {document.source_uri ?? "Not provided"}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function KnowledgeErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Knowledge operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Knowledge error</p>
      <h2>Operation failed</h2>
      <p className="muted">{errorMessage}</p>
    </section>
  );
}

function ResultField({ label, value }: { label: string; value: string }) {
  return (
    <div className="identity-field">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

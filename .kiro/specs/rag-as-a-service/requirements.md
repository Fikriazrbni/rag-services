# Requirements Document

## Introduction

RAG-as-a-Service is a Knowledge Base Builder platform that enables users to upload documents, process them into vector embeddings, and interact with the content through an AI-powered chat interface. The platform is model-agnostic, allowing users to swap LLM providers (OpenAI, Anthropic, Gemini, Groq, Ollama) and embedding models without changing the workflow. It is deployed as a single-tenant Docker-based instance per customer, targeting SMBs to enterprise users. The MVP focuses on core RAG functionality, an analytics dashboard, and API access — without auth or billing systems.

## Glossary

- **Platform**: The RAG-as-a-Service application comprising the Backend, Frontend, and Vector_Store
- **Backend**: The FastAPI-based server handling document ingestion, retrieval, and LLM orchestration
- **Frontend**: The Next.js or React-based web interface for user interaction
- **Vector_Store**: The pgvector or Qdrant database storing document embeddings
- **Document_Processor**: The component responsible for parsing, chunking, and embedding uploaded documents
- **Provider_Adapter**: The abstraction layer (LiteLLM-based) that provides a unified interface to multiple LLM and embedding providers
- **Retriever**: The component that searches the Vector_Store for relevant chunks based on a user query
- **Chat_Interface**: The Frontend component enabling conversational interaction with the knowledge base
- **Analytics_Dashboard**: The Frontend component displaying usage metrics and system statistics
- **API_Gateway**: The Backend component exposing RESTful endpoints for headless and integration use cases
- **Chunk**: A segment of a parsed document, sized for embedding and retrieval
- **Source_Reference**: Metadata linking an answer back to the originating document, page, and paragraph
- **Knowledge_Base**: A collection of processed documents and their embeddings belonging to a single instance

## Requirements

### Requirement 1: Document Upload

**User Story:** As a user, I want to upload documents in common formats, so that I can build a knowledge base from my existing content.

#### Acceptance Criteria

1. WHEN a user uploads a file in PDF, DOCX, or TXT format, THE Document_Processor SHALL accept the file and return an upload confirmation with a unique document identifier
2. WHEN a user uploads a file in an unsupported format, THE Backend SHALL reject the upload and return an error message specifying the supported formats (PDF, DOCX, TXT)
3. WHEN a user uploads multiple files in a single request, THE Document_Processor SHALL process each file independently, up to a maximum of 20 files per request, and return individual status for each file
4. IF a user uploads a file exceeding 50MB, THEN THE Backend SHALL reject the upload and return an error message indicating the maximum allowed file size of 50MB
5. IF a file upload is interrupted or corrupted, THEN THE Backend SHALL discard the partial upload and return an error indicating the upload was incomplete
6. IF a user uploads a file that is empty (zero bytes), THEN THE Backend SHALL reject the upload and return an error indicating that empty files are not accepted
7. IF a user uploads more than 20 files in a single request, THEN THE Backend SHALL reject the entire request and return an error indicating the maximum number of files per request

### Requirement 2: Document Parsing and Chunking

**User Story:** As a user, I want my uploaded documents to be automatically parsed and split into retrievable segments, so that the system can find relevant information efficiently.

#### Acceptance Criteria

1. WHEN a document is successfully uploaded, THE Document_Processor SHALL extract text content from the file while preserving structural metadata (page numbers, headings, paragraphs) and SHALL complete extraction within 60 seconds per 100 pages
2. WHEN text is extracted from a document, THE Document_Processor SHALL split the content into chunks using configurable chunk size (default 512 tokens, minimum 64 tokens, maximum 4096 tokens) and overlap (default 50 tokens, minimum 0 tokens), where the overlap value SHALL be less than the chunk size
3. THE Document_Processor SHALL store chunk metadata including source document identifier, page number, paragraph position, and character offset for each chunk
4. IF a document contains no extractable text, THEN THE Document_Processor SHALL mark the document status as "failed" and provide an error reason indicating why text could not be extracted (e.g., image-only content, password-protected file, or corrupted file structure)
5. WHEN chunking is complete, THE Document_Processor SHALL update the document status to "completed" and record the total number of chunks created, accessible via the document status API endpoint
6. IF a document contains a mix of extractable and non-extractable pages (e.g., image-only pages within a PDF), THEN THE Document_Processor SHALL extract text from all processable pages, skip non-extractable pages, and record the list of skipped page numbers in the document metadata
7. IF chunk size or overlap configuration values are outside the permitted range or overlap is greater than or equal to chunk size, THEN THE Document_Processor SHALL reject the configuration and return an error message indicating the valid ranges

### Requirement 3: Embedding Generation

**User Story:** As a user, I want my document chunks to be converted into vector embeddings, so that semantic search can be performed against my knowledge base.

#### Acceptance Criteria

1. WHEN chunks are created from a document, THE Document_Processor SHALL generate vector embeddings for each chunk using the configured embedding model and store them in the Vector_Store alongside chunk metadata (source document identifier, page number, paragraph position, character offset, and chunk text content)
2. THE Provider_Adapter SHALL support embedding models from OpenAI, Anthropic, Gemini, Groq, and Ollama providers through a unified interface
3. WHEN embeddings are generated, THE Document_Processor SHALL store each embedding vector in the Vector_Store with dimensions matching the configured embedding model output
4. IF the configured embedding provider is unavailable, THEN THE Document_Processor SHALL retry the embedding request up to 3 times with exponential backoff (initial delay 1 second, doubling each retry) before marking the document as "failed" with an error reason indicating provider unavailability
5. WHEN a user changes the embedding model configuration, THE Platform SHALL require re-embedding of existing documents and notify the user of this requirement
6. IF no embedding model is configured, THEN THE Document_Processor SHALL reject the processing request and return an error indicating that an embedding provider must be configured before documents can be processed
7. IF embedding generation fails for some chunks after all retries are exhausted, THEN THE Document_Processor SHALL mark the document as "failed", discard any partially stored embeddings for that document, and include the count of failed chunks in the error reason

### Requirement 4: LLM Provider Configuration

**User Story:** As a user, I want to configure and swap LLM providers and API keys, so that I can use the model that best fits my needs and budget.

#### Acceptance Criteria

1. THE Provider_Adapter SHALL expose a configuration endpoint accepting a provider name, model identifier, and API key for LLM generation
2. THE Provider_Adapter SHALL support the following LLM providers: OpenAI, Anthropic, Gemini, Groq, and Ollama
3. WHEN a user updates the LLM provider configuration, THE Provider_Adapter SHALL validate the API key by performing a test request to the selected provider within a 10-second timeout
4. IF an API key validation fails or times out, THEN THE Provider_Adapter SHALL return an error message indicating the key is invalid or the provider is unreachable, and SHALL preserve the previously active configuration
5. WHEN a user switches LLM providers, THE Platform SHALL apply the new provider to all subsequent chat interactions without requiring changes to existing knowledge bases
6. THE Provider_Adapter SHALL expose a configuration endpoint accepting a provider name, model identifier, and API key for embedding generation, separate from the LLM generation configuration
7. WHEN the provider is Ollama (local), THE Provider_Adapter SHALL skip API key validation and instead verify connectivity to the Ollama endpoint
8. THE Provider_Adapter SHALL expose a read endpoint returning the current active LLM and embedding provider configurations (provider name and model identifier, excluding the API key)

### Requirement 5: Chat-Based Query and Retrieval

**User Story:** As a user, I want to ask questions about my uploaded documents via a chat interface, so that I can get AI-generated answers grounded in my content.

#### Acceptance Criteria

1. WHEN a user submits a question (maximum 2000 characters) through the Chat_Interface, THE Retriever SHALL convert the question into a vector embedding and search the Vector_Store for the top-k most relevant chunks (default k=5, configurable between 1 and 20)
2. WHEN relevant chunks are retrieved, THE Backend SHALL construct a prompt combining the user question and retrieved chunks, and send the prompt to the configured LLM provider
3. WHEN the LLM returns a response, THE Backend SHALL deliver the answer to the user via streaming (Server-Sent Events) along with Source_References for each chunk used in generating the answer, with a maximum response timeout of 60 seconds
4. THE Source_Reference SHALL include the document name, page number, and a paragraph excerpt of up to 200 characters for each cited source
5. IF no relevant chunks are found above the similarity threshold (default 0.7, configurable between 0.0 and 1.0), THEN THE Backend SHALL inform the user that no relevant information was found in the knowledge base
6. IF the configured LLM provider is unavailable, THEN THE Backend SHALL return an error message indicating the provider is unreachable and suggest checking the provider configuration
7. IF the knowledge base contains no documents (zero chunks), THEN THE Backend SHALL return a message indicating the knowledge base is empty and suggesting the user upload documents first

### Requirement 6: Conversation History

**User Story:** As a user, I want my chat conversations to maintain context, so that I can ask follow-up questions without repeating background information.

#### Acceptance Criteria

1. WHEN a user sends a message in an existing conversation, THE Backend SHALL include the previous messages from that conversation (both user and assistant messages, up to a configurable context window, default 10 messages counted individually) in chronological order in the LLM prompt
2. THE Backend SHALL store conversation history per session, associating each message with a session identifier, role (user or assistant), content, and timestamp
3. WHEN a user sends a request to create a new conversation, THE Backend SHALL create a new session with a unique session identifier and an empty history, returning the session identifier in the response
4. THE Backend SHALL provide a paginated endpoint to list previous conversations (default 20 conversations per page) and their messages (default 50 messages per conversation page), ordered by most recent activity
5. IF a user sends a message referencing a session identifier that does not exist, THEN THE Backend SHALL return an error indicating the session was not found

### Requirement 7: Source Referencing

**User Story:** As a user, I want to see exactly where in my documents the answer came from, so that I can verify accuracy and find additional context.

#### Acceptance Criteria

1. THE Backend SHALL include with every chat response a list of Source_References (maximum equal to the configured top-k value) ranked by relevance score in descending order
2. WHEN a Source_Reference is provided, THE Frontend SHALL display the document name, page number, and a text excerpt of the referenced chunk (up to 200 characters)
3. WHEN a user clicks on a Source_Reference, THE Frontend SHALL display the full chunk text in an expandable panel alongside the document name, page number, and paragraph position
4. THE Backend SHALL include a confidence score (0.0 to 1.0, derived from cosine similarity) for each Source_Reference indicating the relevance of the chunk to the query
5. IF the LLM response does not reference any specific chunks, THEN THE Backend SHALL still return all retrieved Source_References with their relevance scores so the user can verify source material

### Requirement 8: Knowledge Base Management

**User Story:** As a user, I want to manage my knowledge base by adding, removing, or listing documents, so that I can keep my content current and relevant.

#### Acceptance Criteria

1. THE Backend SHALL provide a paginated endpoint to list all documents in the Knowledge_Base with their processing status (pending, processing, completed, failed), returning a default of 20 documents per page and a maximum of 100 documents per page
2. WHEN a user requests deletion of a document that is in "completed" or "failed" status, THE Backend SHALL remove the document, its chunks, and associated embeddings from the Vector_Store
3. WHEN a document is successfully deleted, THE Backend SHALL return a confirmation response including the document identifier and the number of chunks removed
4. THE Backend SHALL provide an endpoint to retrieve metadata for a specific document including upload date, file size, chunk count, and processing status
5. IF a user requests deletion or metadata retrieval of a document identifier that does not exist in the Knowledge_Base, THEN THE Backend SHALL return an error indicating the document was not found
6. IF a user requests deletion of a document that is currently in "pending" or "processing" status, THEN THE Backend SHALL reject the deletion and return an error indicating the document is still being processed

### Requirement 9: API Access

**User Story:** As a developer, I want programmatic API access to all platform capabilities, so that I can integrate the RAG service into existing applications and workflows.

#### Acceptance Criteria

1. THE API_Gateway SHALL expose RESTful endpoints for document upload, document management, chat queries, provider configuration, conversation history, and analytics retrieval
2. THE API_Gateway SHALL return responses in JSON format with consistent error structures including error code, message, and request identifier
3. THE API_Gateway SHALL provide an OpenAPI/Swagger specification documenting all available endpoints, request schemas, and response schemas
4. WHEN an API request is malformed or missing required fields, THE API_Gateway SHALL return a 400 status code with a validation error describing the missing or invalid fields
5. THE API_Gateway SHALL support streaming responses for chat queries using Server-Sent Events (SSE), delivering tokens incrementally as they are generated by the LLM provider
6. WHEN a list endpoint returns more results than the page size (default 20, maximum 100), THE API_Gateway SHALL paginate the response and include total count, current page, and total pages in the response metadata
7. IF an API request exceeds a 60-second processing timeout, THEN THE API_Gateway SHALL terminate the request and return a 504 status code with an error message indicating the request timed out

### Requirement 10: Analytics Dashboard

**User Story:** As a user, I want to view usage analytics, so that I can understand how my knowledge base is being used and optimize its content.

#### Acceptance Criteria

1. THE Analytics_Dashboard SHALL display the total number of documents, chunks, and queries processed since knowledge base creation
2. THE Analytics_Dashboard SHALL display query volume over time with daily, weekly, and monthly view options, showing up to 12 months of historical data with the default view set to the last 30 days
3. THE Analytics_Dashboard SHALL display the top 10 most frequently queried topics or keywords within the currently selected time range
4. THE Analytics_Dashboard SHALL display the average response time in milliseconds for chat queries within the currently selected time range
5. WHEN a chat query is processed, THE Backend SHALL log the query with timestamp, response time in milliseconds, number of chunks retrieved, and provider used
6. THE API_Gateway SHALL expose the same analytics metrics available on the dashboard (total counts, query volume over time, top keywords, and average response time) through a dedicated endpoint for programmatic access
7. IF no queries have been recorded for the knowledge base, THEN THE Analytics_Dashboard SHALL display zero values for all numeric metrics and an empty state indication for the query volume chart and top keywords list

### Requirement 11: Docker-Based Deployment

**User Story:** As a user, I want to deploy the platform locally using Docker, so that I can run the service on my own infrastructure without complex setup.

#### Acceptance Criteria

1. THE Platform SHALL provide a Docker Compose configuration that starts all required services (Backend, Frontend, Vector_Store) with a single command
2. THE Platform SHALL use environment variables for all configurable settings including LLM provider keys, embedding model selection, and Vector_Store connection parameters, and SHALL provide a documented `.env.example` file listing all variables with default values for non-sensitive settings
3. WHEN the Docker Compose stack is started, THE Platform SHALL perform health checks on all services with a timeout of 60 seconds per service, and report readiness status to the console indicating each service's state (ready or failed)
4. THE Platform SHALL persist all data (documents, embeddings, conversation history, analytics) in named Docker volumes to survive container restarts
5. THE Platform SHALL include a README with deployment instructions, minimum system requirements (RAM, disk space, Docker version), and initial configuration steps
6. IF any service fails its health check within the timeout period, THEN THE Platform SHALL log an error message identifying the failed service and its failure reason, and the remaining healthy services SHALL continue running

### Requirement 12: Document Processing Status and Notifications

**User Story:** As a user, I want to know the status of my document processing, so that I can understand when my documents are ready for querying.

#### Acceptance Criteria

1. WHEN a document upload begins processing, THE Backend SHALL update the document status to "processing" and make this status queryable via the API, returning a response including document identifier, current status, and current pipeline stage (parsing, chunking, or embedding)
2. WHEN document processing completes successfully, THE Backend SHALL update the status to "completed" and record the processing duration in milliseconds
3. IF document processing fails at any stage, THEN THE Backend SHALL update the status to "failed" and include the pipeline stage where failure occurred, the error type, and a human-readable error message
4. THE API_Gateway SHALL provide a polling endpoint for checking document processing status by document identifier, returning the current status, pipeline stage, processing duration (if completed), and error details (if failed)
5. WHEN a document transitions between processing states, THE Backend SHALL emit a Server-Sent Event (SSE) on a dedicated status stream endpoint within 1 second of the state change, that the Frontend can consume to update the UI in real time

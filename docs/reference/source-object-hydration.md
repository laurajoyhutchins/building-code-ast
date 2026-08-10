# Verified source object hydration

Building Code AST can verify and atomically place privately stored source artifacts without learning provider credentials or publishing private storage locators.

This layer builds on the source-object locator contract. It does not make Google Drive, or any other object store, part of source identity.

## Responsibilities

`verify_local_source_object()` verifies an already-local file against:

1. the selected `SourceObjectRequirement` in the public object catalog;
2. the selected source's authoritative `SourceRegisterEntry`;
3. exact expected byte size;
4. exact SHA-256.

`hydrate_source_object()` adds private acquisition:

1. select the requirement by `source_id`;
2. validate that requirement against the supplied publication-scoped source register;
3. resolve its logical `object_key` through a private locator registry;
4. require the caller-supplied fetcher to match the locator provider;
5. fetch into a temporary file in the destination directory;
6. require a regular, nonsymlink file with exact size and SHA-256;
7. atomically replace the destination only after verification;
8. return a source-safe verified receipt.

A failed fetch, size check, or digest check does not replace an existing destination.

## Provider boundary

The package defines only a small `SourceObjectFetcher` protocol:

```python
class SourceObjectFetcher(Protocol):
    provider: ObjectProvider

    def fetch(
        self,
        locator: PrivateSourceObjectLocator,
        destination: Path,
    ) -> None: ...
```

The provider implementation owns authentication, SDK/API behavior, and network access. The Building Code AST core does not contain Google OAuth code, credentials, refresh tokens, service-account material, signed URLs, or a required Google client dependency.

A connected storage adapter, local workstation script, or trusted execution host can implement the protocol independently. The compiler sees the resulting temporary bytes only through the verification boundary.

## Publication-scoped source authority

The public object catalog can span publications, but source registers remain publication-scoped. Hydration therefore validates the **selected** object requirement against the supplied authoritative source register. It does not require constructing an artificial cross-publication union register merely to fetch one source.

This is narrower than catalog-wide validation and does not permit an unregistered source: the selected `source_id`, SHA-256, and media type must still agree exactly with its source register before any provider fetch occurs.

## Filesystem behavior

Verification accepts regular files only. Symlink source paths are rejected. Hydration also rejects a symlink destination and performs acquisition through a temporary file in the destination directory so the final placement can use `os.replace` atomically.

Size is checked before hashing. SHA-256 is streamed rather than requiring a whole publication in memory. File identity/stat metadata is compared before and after hashing so mutation during verification fails closed.

## Source-safe receipt

A successful hydration receipt contains only:

- receipt version and type;
- `verified` status;
- `source_id`;
- logical `object_key`;
- exact SHA-256;
- byte size;
- media type.

It deliberately omits:

- provider name;
- provider object ID;
- private path hint;
- local destination path;
- source expression;
- credentials or authentication material.

The receipt schema is `schemas/source-object-hydration-receipt.schema.json`.

## Example composition

```python
catalog = ...        # public, Git-safe
source_register = ...  # authoritative publication register
private_locators = ... # outside Git
fetcher = ...          # environment-owned provider adapter

receipt = hydrate_source_object(
    catalog,
    source_register,
    private_locators,
    source_id="source:...",
    destination="local-sources/source.pdf",
    fetcher=fetcher,
)
```

The example intentionally does not show a real provider object ID or credential. Provider-private configuration stays outside repository history.

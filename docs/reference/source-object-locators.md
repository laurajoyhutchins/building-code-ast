# Private source object location

Building Code AST keeps exact-source identity separate from private storage location.

The authority-bearing source register continues to identify what an artifact is through `source_id`, publication identity, SHA-256, media type, access scope, and rights status. The source-object catalog adds only a stable logical object key and expected byte size. Neither the logical key nor any storage-provider locator participates in source identity.

## Public catalog

`corpora/source-object-catalog.json` is safe to commit. Each entry contains only:

- `source_id`;
- `object_key`;
- lowercase SHA-256;
- exact byte size;
- media type.

The catalog is validated against the existing `SourceRegister`: source ID must exist and SHA-256/media type must agree exactly. A catalog entry cannot create or override source authority.

The initial catalog contains only retained artifacts that already have authoritative source-register entries and whose retained private bytes were replayed against those registered digests: IBC 2018, NDS 2018, and ASCE/SEI 7-22. Other retained publications should be added only after their own exact source registration is durable.

## Private locator registry

A private locator registry maps the public logical `object_key` to an operational provider locator. The initial provider vocabulary is deliberately small: `google_drive`.

A locator may contain:

- `object_key`;
- provider;
- opaque provider `object_id`;
- an optional private path hint.

It does not repeat `source_id`, SHA-256, or publication identity. The provider object ID is therefore a transport locator, not artifact truth.

Actual locator registries must remain outside Git. `generated-private/` is already ignored and is the recommended local location, for example:

```text
generated-private/source-object-locators.json
```

The committed JSON Schema describes the private file shape so local tooling can validate it without publishing any real provider object IDs.

## Secret boundary

Provider credentials are not fields in either contract. Strict deserialization rejects unknown fields, so values such as access tokens, OAuth client secrets, signed URLs, or service-account material cannot be added to a valid locator registry accidentally.

Authentication belongs to the environment or provider adapter. It is never source metadata.

## `source_url` is different

`SourceRegisterEntry.source_url` remains provenance about where source evidence was obtained when such a URL is appropriate. A private Google Drive object ID or private storage path is operational storage metadata and must not be placed in `source_url` merely to make hydration convenient.

## Privacy invariant

Git can know exactly which bytes are required without knowing where the owner's private copy lives:

```text
public source register + public object catalog
        |
        | source_id / logical object_key / exact digest
        v
private locator registry
        |
        | provider + opaque object ID
        v
private bytes
        |
        | verify size + SHA-256 before trust
        v
existing evidence / retrieval / parser pipeline
```

Moving or renaming a private Drive object changes no public identity. Replacing its bytes is detected by exact verification before downstream use.

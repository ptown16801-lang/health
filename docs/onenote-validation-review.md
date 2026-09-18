# Controlled OneNote extraction review

Use this checklist to review a controlled `.one` or `.onepkg` extraction. It
defines two evidence layers:

- **Private evidence packet:** the untouched input, exact identifiers and
  hashes, command, logs, manifest, recovered files, reference images, and
  inspection notes. Keep it in access-controlled storage outside Git.
- **Redacted summary:** a non-PHI attestation suitable for this repository,
  created from the template in `templates/`. It contains no source filenames,
  paths, content, screenshots, output filenames, exact timestamps, person or
  provider information, or other identifying metadata.

An exact SHA-256 may be included in a redacted summary only after an authorized
reviewer determines that it is safe to disclose. Otherwise record that the
full hash was verified privately and use only the private run identifier.

## Reviewer checklist

### 1. Privacy boundary and run isolation

- [ ] The input and all derived artifacts stayed in approved private storage.
- [ ] The run used a new, uniquely named output directory outside the repository.
- [ ] The original input was opened read-only or copied without modification.
- [ ] No real filenames, paths, clinical content, screenshots, logs, OCR text,
      manifest entries, or identifying metadata entered Git, a PR, or an issue.
- [ ] The redacted summary was checked independently for indirect identifiers.

Stop the review and remove the draft from version-control staging if any item
above fails.

### 2. Input identity and integrity

- [ ] The private packet records the input's exact filename, byte size, and
      complete SHA-256 before conversion.
- [ ] A stable, non-identifying run ID links the private packet to the redacted
      summary.
- [ ] The post-run hash of the untouched original matches the pre-run hash.
- [ ] The container type (`.one` or `.onepkg`) and fixture selection rationale
      are recorded privately.

### 3. Converter and supporting tools

- [ ] The candidate converter is explicitly identified; no silent substitute
      was used.
- [ ] Package/repository, exact version or commit, installation method, and
      executable hash or resolved path are recorded privately where available.
- [ ] The literal command and arguments, working directory, relevant environment,
      and start/end timestamps are recorded privately.
- [ ] Supporting inspection/OCR tools and versions are recorded.
- [ ] Every used capability is locally runnable without a paid subscription;
      any exception is a blocker, not an implicit recommendation.

### 4. Process result

- [ ] Standard output and standard error were captured separately in private
      storage.
- [ ] Exit status, duration, and all warnings/errors are recorded.
- [ ] A successful exit with empty, partial, or malformed output is treated as
      a possible silent failure.

### 5. Output inventory and integrity

- [ ] A recursive private manifest records each output's relative path, type,
      byte size, and SHA-256.
- [ ] Counts are summarized by type without exposing sensitive names.
- [ ] Recovered PDFs were structurally checked and directly extractable text
      was inspected without OCR first.
- [ ] Images and attachments were checked for readable structure/corruption.
- [ ] Duplicate byte hashes and suspicious near-duplicates were reviewed.
- [ ] Unexpected, zero-byte, truncated, encrypted, or unparseable outputs are
      listed as findings.

### 6. Coverage and source comparison

- [ ] Review records whether hierarchy, native text, images, embedded documents,
      general attachments, and tables were present, recovered, absent from the
      fixture, or not assessable.
- [ ] Output was compared with the authorized source application or supplied
      references only when those references were actually available.
- [ ] The comparison samples page/section relationships and every present
      content class; it does not rely only on output counts.
- [ ] Source-visible omissions, altered ordering/relationships, conversion
      artifacts, and unsupported structures are recorded.
- [ ] Distinct same-day/source observations remain distinct when values or
      context differ; date or label alone was not used to deduplicate them.
- [ ] OCR, if used, is labeled optional/derived and cannot replace the original
      or native/directly extracted text.
- [ ] The summary does not claim screenshots or reference material were
      reviewed unless they were actually supplied and inspected.

Use these coverage states consistently: `recovered`, `partial`, `missing`,
`not present`, and `not assessed`. `Not present` is not proof of converter
support. `Not assessed` cannot support a pass.

### 7. Findings and decision

- [ ] Every finding has a non-sensitive ID, severity, affected content class,
      private-evidence pointer, and disposition.
- [ ] Limitations and untested content classes are explicit.
- [ ] The decision is `PASS`, `FAIL`, or `BLOCKED`; it is not inferred from the
      process exit status.
- [ ] `PASS` is used only when all required expectations and integrity checks
      pass with no unresolved critical finding.
- [ ] `FAIL` is used for corruption, missing required/source-visible content,
      silent failure, incorrect collapsing of distinct observations, or another
      unmet required expectation.
- [ ] `BLOCKED` is used when required input, ground truth, private access, or
      evidence is unavailable; absence of evidence is never reported as pass.
- [ ] Reviewer name/role and approval time are retained privately; the redacted
      summary uses a non-identifying reviewer label if needed.

## Redaction workflow

1. Complete the checklist against the private packet in private storage.
2. Copy the redacted template into a temporary location outside the repository.
3. Replace placeholders with aggregate, non-identifying facts only. Use
   `verified privately`, `not assessed`, or a finding ID instead of sensitive
   detail.
4. Search the draft for source/output filenames, absolute paths, dates, names,
   identifiers, clinical values/content, exact commands containing paths, and
   pasted log or manifest text.
5. Have a second authorized reviewer perform a privacy check when possible.
6. Only then place the redacted summary in the repository. Before committing,
   inspect `git diff --cached` and confirm no ignored artifact was force-added.
